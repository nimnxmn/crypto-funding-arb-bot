import config
from paper_trade.simulator import PaperTradeSimulator, ArbPair

ALERT_OK       = "ok"
ALERT_DRIFT    = "drift_warning"
ALERT_CRITICAL = "drift_critical"
ALERT_STOPLOSS = "stop_loss"

_MAINTENANCE_MARGIN = 0.01  # 1% — conservative estimate across all exchanges


def drift_pct(short_price: float, long_price: float) -> float:
    """Price divergence between the two legs as a fraction."""
    mid = (short_price + long_price) / 2
    return abs(short_price - long_price) / mid if mid else 0.0


def check_pair(pair: ArbPair, short_price: float, long_price: float) -> dict:
    """
    Run all risk checks on one open pair.

    Stop-loss threshold is relative to collateral at risk (size_usd / leverage),
    so it fires proportionally sooner at higher leverage.

    Liquidation warning fires when either leg is within 20% of its estimated
    liquidation price (only relevant when leverage > 1).
    """
    d = drift_pct(short_price, long_price)
    price_pnl = pair.price_pnl(short_price, long_price)
    net = pair.net_pnl(short_price, long_price)
    collateral = pair.size_usd / pair.leverage
    threshold = -config.STOP_LOSS_PCT * collateral

    alerts = []
    level = ALERT_OK

    if price_pnl < threshold or net < threshold:
        if price_pnl < threshold:
            alerts.append(
                f"STOP-LOSS (price): price P&L ${price_pnl:+.2f} below ${threshold:.2f} — hedge broken"
            )
        if net < threshold:
            alerts.append(
                f"STOP-LOSS (net): net P&L ${net:+.2f} below ${threshold:.2f}"
            )
        level = ALERT_STOPLOSS

    elif d >= config.DRIFT_CRITICAL_PCT:
        alerts.append(
            f"CRITICAL DRIFT: {d*100:.3f}% price divergence — consider closing and reopening"
        )
        level = ALERT_CRITICAL

    elif d >= config.DRIFT_WARNING_PCT:
        alerts.append(
            f"DRIFT WARNING: {d*100:.3f}% price divergence between {pair.short_exchange} and {pair.long_exchange}"
        )
        level = ALERT_DRIFT

    # Liquidation proximity warning (leverage > 1 only)
    if pair.leverage > 1 and level not in (ALERT_STOPLOSS,):
        liq_distance = 1.0 / pair.leverage - _MAINTENANCE_MARGIN
        short_move = (short_price - pair.short_entry_price) / pair.short_entry_price
        long_move = (pair.long_entry_price - long_price) / pair.long_entry_price
        if short_move >= liq_distance * 0.8 or long_move >= liq_distance * 0.8:
            alerts.append(
                f"LIQ RISK ({pair.leverage}x): one leg within 20% of liquidation "
                f"(short liq ~${pair.liq_price_short():.2f}, long liq ~${pair.liq_price_long():.2f})"
            )
            if level == ALERT_OK:
                level = ALERT_DRIFT

    return {
        "pair_id": pair.pair_id,
        "base": pair.base,
        "level": level,
        "drift_pct": d,
        "price_pnl": price_pnl,
        "net_pnl": net,
        "stop_loss_threshold": threshold,
        "alerts": alerts,
    }


def check_all(sim: PaperTradeSimulator, live_data: dict) -> list[dict]:
    """Run risk checks on all open pairs. Returns list of check results."""
    results = []
    for pair in sim.open_pairs():
        bd = live_data.get(pair.base, {})
        sp = bd.get(pair.short_exchange, {}).get("mark_price", pair.short_entry_price)
        lp = bd.get(pair.long_exchange, {}).get("mark_price", pair.long_entry_price)
        results.append(check_pair(pair, sp, lp))
    return results


def validate_open(spread: float, size_usd: float, leverage: int = 1,
                  sim: PaperTradeSimulator | None = None) -> tuple[bool, str]:
    """
    Validate a proposed new arb pair before opening.

    size_usd is notional per leg. Capital deployed = size_usd / leverage * 2.
    MAX_POSITION_PCT applies to collateral (not notional), so higher leverage
    allows larger notional within the same capital limit.
    """
    min_spread = config.ROUND_TRIP_FEE * config.MIN_SPREAD_MULTIPLIER
    if spread < min_spread:
        return False, (
            f"Spread {spread*100:.4f}%/8h is below minimum "
            f"{min_spread*100:.4f}% ({config.MIN_SPREAD_MULTIPLIER}× round-trip fees). "
            f"Would not break even."
        )

    collateral_this = size_usd / leverage * 2
    max_collateral = config.TOTAL_CAPITAL * config.MAX_POSITION_PCT
    if collateral_this > max_collateral:
        return False, (
            f"Collateral ${collateral_this:,.0f} ({size_usd:,.0f} / {leverage}x × 2 legs) "
            f"exceeds max ${max_collateral:,.0f} "
            f"({config.MAX_POSITION_PCT*100:.0f}% of ${config.TOTAL_CAPITAL:,.0f} capital)."
        )

    if sim is not None:
        deployed_now = sum(p.size_usd / p.leverage * 2 for p in sim.open_pairs())
        new_total = deployed_now + collateral_this
        if new_total > config.TOTAL_CAPITAL:
            return False, (
                f"Would deploy ${new_total:,.0f} total collateral "
                f"(existing ${deployed_now:,.0f} + new ${collateral_this:,.0f}), "
                f"exceeds available ${config.TOTAL_CAPITAL:,.0f}."
            )

    return True, "ok"


def print_risk_report(results: list[dict]) -> None:
    if not results:
        print("  No open pairs to check.")
        return

    print(f"\n{'='*70}")
    print("  RISK REPORT")
    print(f"{'='*70}")
    for r in results:
        icon = {"ok": " OK ", "drift_warning": "WARN", "drift_critical": "CRIT", "stop_loss": "STOP"}[r["level"]]
        print(f"  [{icon}] {r['pair_id']}  {r['base']:<8}  "
              f"drift: {r['drift_pct']*100:.3f}%  net P&L: ${r['net_pnl']:>+.4f}")
        for alert in r["alerts"]:
            print(f"         -> {alert}")
    print(f"{'='*70}\n")
