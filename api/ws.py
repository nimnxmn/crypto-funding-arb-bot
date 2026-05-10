"""
WebSocket broadcaster — pushes scanner/positions/risk/balances every 5 seconds.

Key behaviours:
- Single fetch_all() call per cycle (shared TTL cache in strategy/scanner.py).
  No double-fetching: scanner, live position prices, and risk all use the same data.
- Auto-applies funding at 8h settlement boundaries (00:00, 08:00, 16:00 UTC).
- Auto-closes positions that trigger stop-loss.
- Sends "notification" messages to clients so toasts appear in the UI.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta, date as _date

from fastapi import WebSocket, WebSocketDisconnect

from api.deps import get_simulator
from api.routes.positions import _pair_to_status

SETTLEMENT_HOURS = (0, 8, 16)


def _current_settlement_period() -> tuple[_date, int]:
    """(date, settlement_hour) of the most recent past 8h boundary."""
    now = datetime.now(tz=timezone.utc)
    past = [h for h in SETTLEMENT_HOURS if h <= now.hour]
    if past:
        return (now.date(), max(past))
    yesterday = (now - timedelta(days=1)).date()
    return (yesterday, max(SETTLEMENT_HOURS))


_last_applied_period: tuple = _current_settlement_period()


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self._connections.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, payload: dict):
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def _build_live_data(by_base: dict) -> dict:
    return {
        base: {
            r["exchange"]: {"funding_rate": r["rate_per_8h"], "mark_price": r["mark_price"]}
            for r in rows
        }
        for base, rows in by_base.items()
    }


def _collect_all_sync() -> dict:
    """
    Single pass using the shared fetch cache:
    - Derives scanner opportunities (no extra HTTP calls if cache is warm).
    - Computes open-position P&L with live mark prices.
    - Runs risk checks and auto-closes stop-loss positions.
    Returns {"scanner", "positions", "risk", "notifications"}.
    """
    from strategy.scanner import _fetch_cached, _process_opportunities, get_scanned_at
    from risk.manager import check_all, ALERT_STOPLOSS

    # One fetch — shared across all downstream consumers this cycle.
    try:
        by_base = _fetch_cached()
    except Exception as e:
        print(f"[WS] fetch error: {e}")
        by_base = {}

    live_data = _build_live_data(by_base)

    # Scanner (uses same cached by_base — no extra exchange calls)
    try:
        scanner_opps = _process_opportunities(by_base)
    except Exception:
        scanner_opps = []

    # Open positions with live mark prices
    sim = get_simulator()
    open_list = []
    for p in sim.open_pairs():
        bd = live_data.get(p.base, {})
        sp = bd.get(p.short_exchange, {}).get("mark_price", p.short_entry_price)
        lp = bd.get(p.long_exchange, {}).get("mark_price", p.long_entry_price)
        open_list.append(_pair_to_status(p, sp, lp).model_dump())
    closed_list = [_pair_to_status(p).model_dump() for p in sim.closed_pairs()]

    # Risk checks + auto stop-loss
    notifications: list[dict] = []
    if sim.open_pairs():
        try:
            results = check_all(sim, live_data)
            for r in results:
                if r["level"] != ALERT_STOPLOSS:
                    continue
                pair = sim.pairs.get(r["pair_id"])
                if not pair or pair.status != "open":
                    continue
                bd = live_data.get(pair.base, {})
                sp = bd.get(pair.short_exchange, {}).get("mark_price", pair.short_entry_price)
                lp = bd.get(pair.long_exchange, {}).get("mark_price", pair.long_entry_price)
                sim.close_pair(r["pair_id"], sp, lp, reason="stop_loss")
                msg = f"Stop-loss triggered: {r['base']} ({r['pair_id']}) closed — net ${r['net_pnl']:+.2f}"
                notifications.append({"level": "error", "message": msg})
                print(f"[AUTO STOP-LOSS] {msg}")
            risk_data = {"results": results}
        except Exception as e:
            print(f"[RISK] error: {e}")
            risk_data = {"results": []}
    else:
        risk_data = {"results": []}

    return {
        "scanner": {
            "opportunities": scanner_opps,
            "scanned_at": get_scanned_at(),
        },
        "positions": {"open": open_list, "closed": closed_list},
        "risk": risk_data,
        "notifications": notifications,
    }


def _auto_apply_funding_sync() -> list[dict]:
    """Apply one 8h funding period using cached live data. Returns notification list."""
    from strategy.scanner import _fetch_cached
    sim = get_simulator()
    if not sim.open_pairs():
        return []

    by_base = _fetch_cached()
    live_data = _build_live_data(by_base)
    payments = sim.apply_funding(live_data)
    if not payments:
        return []

    total = sum(payments.values())
    msg = f"Funding applied to {len(payments)} pair(s) — net ${total:+.4f}"
    print(f"[AUTO FUNDING] {msg}")
    return [{"level": "success", "message": msg}]


async def broadcast_loop():
    global _last_applied_period

    while True:
        await asyncio.sleep(5)
        loop = asyncio.get_event_loop()

        # Auto-apply funding when a new 8h period starts
        funding_notifications: list[dict] = []
        current_period = _current_settlement_period()
        if current_period != _last_applied_period:
            try:
                funding_notifications = await loop.run_in_executor(None, _auto_apply_funding_sync)
            except Exception as e:
                print(f"[AUTO FUNDING] Error: {e}")
            _last_applied_period = current_period

        if not manager._connections:
            continue

        # Single-pass data collection (one fetch_all call shared across everything)
        result = await loop.run_in_executor(None, _collect_all_sync)

        # Push scanner / positions / risk
        for msg_type in ("scanner", "positions", "risk"):
            await manager.broadcast({"type": msg_type, "data": result[msg_type]})

        # Push balances (live mode only)
        import config
        if config.TRADING_MODE == "live":
            await manager.broadcast({"type": "balances", "data": {"balances": []}})

        # Push toast notifications
        for notif in funding_notifications + result["notifications"]:
            await manager.broadcast({"type": "notification", "data": notif})


async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
