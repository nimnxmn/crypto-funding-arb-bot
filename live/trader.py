"""
Live trading engine — places real orders on Binance, OKX, Bybit.
All keys are read from environment variables (loaded from .env).
"""
import json
import math
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from exchange import binance_auth, okx_auth, bybit_auth
from live.notifier import TelegramNotifier
from strategy.scanner import fetch_all

POSITIONS_PATH = Path(__file__).parent / "positions.json"

notifier = TelegramNotifier()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _load_positions() -> dict:
    if POSITIONS_PATH.exists():
        with open(POSITIONS_PATH) as f:
            return json.load(f)
    return {}


def _save_positions(positions: dict):
    with open(POSITIONS_PATH, "w") as f:
        json.dump(positions, f, indent=2)


def _keys(exchange: str) -> dict:
    if exchange == "Binance":
        return {
            "api_key": os.getenv("BINANCE_API_KEY", ""),
            "secret": os.getenv("BINANCE_API_SECRET", ""),
        }
    if exchange == "OKX":
        return {
            "api_key": os.getenv("OKX_API_KEY", ""),
            "secret": os.getenv("OKX_API_SECRET", ""),
            "passphrase": os.getenv("OKX_PASSPHRASE", ""),
        }
    if exchange == "Bybit":
        return {
            "api_key": os.getenv("BYBIT_API_KEY", ""),
            "secret": os.getenv("BYBIT_API_SECRET", ""),
        }
    raise ValueError(f"Unknown exchange: {exchange}")


def _symbol(exchange: str, base: str) -> str:
    """Convert base asset to exchange-specific symbol."""
    if exchange == "Binance":
        return f"{base}USDT"
    if exchange == "OKX":
        return f"{base}-USDT-SWAP"
    if exchange == "Bybit":
        return f"{base}USDT"
    raise ValueError(f"Unknown exchange: {exchange}")


def _round_qty(qty: float, step: float) -> float:
    precision = max(0, round(-math.log10(step)))
    return round(math.floor(qty / step) * step, precision)


def _exchange_qty_for_size(exchange: str, base: str, size_usd: float, price: float) -> tuple[float, float]:
    """
    Return (rounded_qty_in_base_asset, effective_size_usd) after exchange lot-size rules.
    For OKX, qty is in contracts × ctVal converted back to base units.
    """
    symbol = _symbol(exchange, base)
    if exchange == "Binance":
        step = binance_auth.get_qty_step(symbol)
        qty = _round_qty(size_usd / price, step)
        return qty, qty * price
    if exchange == "OKX":
        ct_val = okx_auth.get_contract_size(symbol)
        contracts = math.floor((size_usd / price) / ct_val)
        qty_base = contracts * ct_val
        return qty_base, qty_base * price
    if exchange == "Bybit":
        step = bybit_auth.get_qty_step(symbol)
        qty = _round_qty(size_usd / price, step)
        return qty, qty * price
    raise ValueError(f"Unknown exchange: {exchange}")


# ── Balance check ─────────────────────────────────────────────────────────────

def get_balances() -> dict[str, float]:
    """Return USDT balances from all exchanges."""
    balances = {}
    k = _keys("Binance")
    try:
        balances["Binance"] = binance_auth.get_balance(**k)
    except Exception as e:
        balances["Binance"] = f"error: {e}"

    k = _keys("OKX")
    try:
        balances["OKX"] = okx_auth.get_balance(**k)
    except Exception as e:
        balances["OKX"] = f"error: {e}"

    k = _keys("Bybit")
    try:
        balances["Bybit"] = bybit_auth.get_balance(**k)
    except Exception as e:
        balances["Bybit"] = f"error: {e}"

    return balances


# ── Order placement ───────────────────────────────────────────────────────────

def _place_order(exchange: str, base: str, side: str, size_usd: float, price: float) -> dict:
    """
    Place a market order on any supported exchange.
    Returns order result dict.
    side for short leg: "SELL" / "sell" / "Sell"
    side for long leg:  "BUY"  / "buy"  / "Buy"
    """
    symbol = _symbol(exchange, base)

    if exchange == "Binance":
        step = binance_auth.get_qty_step(symbol)
        qty = _round_qty(size_usd / price, step)
        k = _keys("Binance")
        bn_side = "SELL" if side == "short" else "BUY"
        return binance_auth.place_market_order(symbol, bn_side, qty, **k)

    if exchange == "OKX":
        ct_val = okx_auth.get_contract_size(symbol)
        contracts = math.floor((size_usd / price) / ct_val)
        if contracts < 1:
            raise ValueError(f"OKX: position too small — minimum 1 contract = {ct_val} {base}")
        k = _keys("OKX")
        okx_side = "sell" if side == "short" else "buy"
        return okx_auth.place_market_order(symbol, okx_side, contracts, **k)

    if exchange == "Bybit":
        step = bybit_auth.get_qty_step(symbol)
        qty = _round_qty(size_usd / price, step)
        k = _keys("Bybit")
        bb_side = "Sell" if side == "short" else "Buy"
        return bybit_auth.place_market_order(symbol, bb_side, qty, **k)

    raise ValueError(f"Unknown exchange: {exchange}")


# ── Live pair management ──────────────────────────────────────────────────────

def open_live_pair(base: str, size_usd: float,
                   short_exchange: str, short_price: float, short_rate: float,
                   long_exchange: str, long_price: float, long_rate: float) -> dict:
    """
    Open a live arb pair: short on short_exchange, long on long_exchange.
    If the long leg fails after the short fills, the short is emergency-closed.
    Returns the position record.
    """
    pair_id = str(uuid.uuid4())[:8]
    spread = short_rate - long_rate

    # Compute rounded qty on each exchange and use the SMALLER effective size
    # so both legs match exactly (no residual directional exposure).
    short_qty, short_eff = _exchange_qty_for_size(short_exchange, base, size_usd, short_price)
    long_qty, long_eff = _exchange_qty_for_size(long_exchange, base, size_usd, long_price)

    if short_qty <= 0 or long_qty <= 0:
        raise ValueError(f"Position size too small: short_qty={short_qty}, long_qty={long_qty}")

    matched_size = min(short_eff, long_eff)
    if matched_size < size_usd * 0.95:
        print(f"  [{pair_id}] Lot-size rounding shrank position from "
              f"${size_usd:,.0f} to ${matched_size:,.0f}")

    # Fire both legs in PARALLEL to minimize the price-drift window between fills.
    # Sequential placement was 1-3s of slippage risk; parallel is typically <500ms.
    print(f"  [{pair_id}] Firing both legs in parallel ({matched_size:.2f} USDT/leg)...")
    print(f"  [{pair_id}]   SHORT {base} on {short_exchange}")
    print(f"  [{pair_id}]   LONG  {base} on {long_exchange}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        short_future = pool.submit(_place_order, short_exchange, base, "short", matched_size, short_price)
        long_future = pool.submit(_place_order, long_exchange, base, "long", matched_size, long_price)

        short_order, short_err = None, None
        long_order, long_err = None, None
        try:
            short_order = short_future.result(timeout=30)
        except Exception as e:
            short_err = e
        try:
            long_order = long_future.result(timeout=30)
        except Exception as e:
            long_err = e

    # Reconcile outcomes
    if short_err and long_err:
        notifier.error(f"open_live_pair/{pair_id}",
                       f"Both legs failed.\nshort: {short_err}\nlong: {long_err}")
        raise RuntimeError(f"Both legs failed. short={short_err}; long={long_err}")

    if short_err:
        # Long filled but short didn't — emergency close the long
        print(f"  [{pair_id}] Short leg failed — emergency closing long...")
        notifier.error(f"open_live_pair/{pair_id}",
                       f"Short leg failed: {short_err}\nEmergency closing long on {long_exchange}.")
        try:
            _place_order(long_exchange, base, "short", matched_size, long_price)
        except Exception as e2:
            notifier.error("EMERGENCY CLOSE FAILED", f"Long leg on {long_exchange}: {e2}")
        raise RuntimeError(f"Short leg failed ({short_err}). Long has been emergency-closed.") from short_err

    if long_err:
        # Short filled but long didn't — emergency close the short
        print(f"  [{pair_id}] Long leg failed — emergency closing short...")
        notifier.error(f"open_live_pair/{pair_id}",
                       f"Long leg failed: {long_err}\nEmergency closing short on {short_exchange}.")
        try:
            _place_order(short_exchange, base, "long", matched_size, short_price)
        except Exception as e2:
            notifier.error("EMERGENCY CLOSE FAILED", f"Short leg on {short_exchange}: {e2}")
        raise RuntimeError(f"Long leg failed ({long_err}). Short has been emergency-closed.") from long_err

    position = {
        "pair_id": pair_id,
        "base": base,
        "status": "open",
        "size_usd": matched_size,
        "requested_size_usd": size_usd,
        "short_exchange": short_exchange,
        "short_price": short_price,
        "short_rate_at_open": short_rate,
        "long_exchange": long_exchange,
        "long_price": long_price,
        "long_rate_at_open": long_rate,
        "spread_at_open": spread,
        "opened_at": _now(),
        "short_order": short_order,
        "long_order": long_order,
    }

    positions = _load_positions()
    positions[pair_id] = position
    _save_positions(positions)

    notifier.opened(pair_id, base, short_exchange, long_exchange, size_usd, spread * 100)
    print(f"  [{pair_id}] Opened successfully. Spread: {spread*100:+.4f}%/8h")
    return position


def close_live_pair(pair_id: str, short_price: float, long_price: float) -> float:
    """
    Close a live arb pair. Places closing orders on both exchanges.
    Returns approximate realized P&L.
    """
    positions = _load_positions()
    pos = positions.get(pair_id)
    if not pos or pos["status"] != "open":
        raise ValueError(f"Position {pair_id} not found or already closed.")

    base = pos["base"]
    matched_size = pos["size_usd"]

    # Close both legs in parallel to minimize price drift between fills.
    print(f"  [{pair_id}] Closing both legs in parallel...")
    with ThreadPoolExecutor(max_workers=2) as pool:
        # Closing a short = BUY back; closing a long = SELL
        short_close = pool.submit(_place_order, pos["short_exchange"], base, "long", matched_size, short_price)
        long_close = pool.submit(_place_order, pos["long_exchange"], base, "short", matched_size, long_price)

        errors = []
        try:
            short_close.result(timeout=30)
        except Exception as e:
            errors.append(f"short close on {pos['short_exchange']}: {e}")
        try:
            long_close.result(timeout=30)
        except Exception as e:
            errors.append(f"long close on {pos['long_exchange']}: {e}")

    if errors:
        # One or both close orders failed — surface but don't undo (manual recovery needed)
        msg = "; ".join(errors)
        notifier.error(f"close_live_pair/{pair_id}",
                       f"Close failed:\n{msg}\nManually verify positions on the exchange.")
        raise RuntimeError(f"Close failed for pair {pair_id}: {msg}")

    short_qty = pos["size_usd"] / pos["short_price"]
    long_qty = pos["size_usd"] / pos["long_price"]
    price_pnl = (pos["short_price"] - short_price) * short_qty + (long_price - pos["long_price"]) * long_qty
    realized = price_pnl  # funding was collected automatically by exchanges

    pos["status"] = "closed"
    pos["closed_at"] = _now()
    pos["short_exit_price"] = short_price
    pos["long_exit_price"] = long_price
    pos["approx_price_pnl"] = realized
    _save_positions(positions)

    notifier.closed(pair_id, base, realized)
    print(f"  [{pair_id}] Closed. Approx price P&L: ${realized:+.4f}")
    return realized


def get_live_positions() -> list[dict]:
    return [p for p in _load_positions().values() if p["status"] == "open"]


# ── Funding history sync ──────────────────────────────────────────────────────

def _opened_at_ms(pos: dict) -> int:
    """Convert ISO 'opened_at' string to unix ms."""
    return int(datetime.fromisoformat(pos["opened_at"]).timestamp() * 1000)


def _funding_for_leg(exchange: str, base: str, start_ms: int) -> tuple[float, list[dict]]:
    """Return (total_usd, raw_entries) of funding for a single leg since start_ms."""
    symbol = _symbol(exchange, base)
    if exchange == "Binance":
        entries = binance_auth.get_funding_payments(symbol, start_ms, **_keys("Binance"))
    elif exchange == "OKX":
        entries = okx_auth.get_funding_payments(symbol, start_ms, **_keys("OKX"))
    elif exchange == "Bybit":
        entries = bybit_auth.get_funding_payments(symbol, start_ms, **_keys("Bybit"))
    else:
        return 0.0, []
    return sum(e["amount_usd"] for e in entries), entries


def sync_funding(pair_id: str | None = None) -> dict[str, dict]:
    """
    Pull funding payment history from each exchange for live positions and
    update the local record. If pair_id is None, sync all open positions.

    Returns {pair_id: {"short_funding": float, "long_funding": float, "net": float}}.
    """
    positions = _load_positions()
    targets = [p for pid, p in positions.items()
               if p["status"] == "open" and (pair_id is None or pid == pair_id)]

    summary: dict[str, dict] = {}
    for pos in targets:
        pid = pos["pair_id"]
        start_ms = _opened_at_ms(pos)
        try:
            short_total, _ = _funding_for_leg(pos["short_exchange"], pos["base"], start_ms)
            long_total, _ = _funding_for_leg(pos["long_exchange"], pos["base"], start_ms)
        except Exception as e:
            notifier.error(f"sync_funding/{pid}", str(e))
            continue

        net = short_total + long_total  # exchanges already sign payments correctly
        pos["funding_short"] = short_total
        pos["funding_long"] = long_total
        pos["funding_net"] = net
        pos["funding_synced_at"] = _now()
        summary[pid] = {"short_funding": short_total, "long_funding": long_total, "net": net}

    _save_positions(positions)
    return summary
