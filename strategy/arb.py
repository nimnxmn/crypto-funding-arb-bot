from strategy.scanner import fetch_all
from paper_trade.simulator import PaperTradeSimulator, ArbPair


def get_live_data() -> dict[str, dict[str, dict]]:
    """
    Returns {base: {exchange_name: {"funding_rate": float, "mark_price": float}}}
    Uses parallel fetch across all exchanges.
    """
    by_base = fetch_all()
    result: dict[str, dict[str, dict]] = {}
    for base, rows in by_base.items():
        result[base] = {
            row["exchange"]: {
                "funding_rate": row["funding_rate"],
                "mark_price": row["mark_price"],
            }
            for row in rows
        }
    return result


def print_pairs(sim: PaperTradeSimulator, live_data: dict[str, dict[str, dict]]):
    open_pairs = sim.open_pairs()
    closed_pairs = sim.closed_pairs()

    print(f"\n{'='*82}")
    print("  OPEN ARB PAIRS")
    print(f"{'='*82}")

    if not open_pairs:
        print("  (none)")
    else:
        print(f"  {'ID':<10} {'BASE':<8} {'SHORT ON':<10} {'LONG ON':<10} "
              f"{'SIZE':>8} {'FUNDING':>10} {'PRICE PNL':>10} {'NET PNL':>10}")
        print(f"  {'-'*78}")
        total_net = 0.0
        for p in open_pairs:
            base_data = live_data.get(p.base, {})
            short_data = base_data.get(p.short_exchange, {})
            long_data = base_data.get(p.long_exchange, {})
            sp = short_data.get("mark_price", p.short_entry_price)
            lp = long_data.get("mark_price", p.long_entry_price)
            net = p.net_pnl(sp, lp)
            price_pnl = p.price_pnl(sp, lp)
            total_net += net
            print(
                f"  {p.pair_id:<10} {p.base:<8} {p.short_exchange:<10} {p.long_exchange:<10}"
                f"${p.size_usd:>7,.0f} "
                f"${p.funding_collected:>9,.4f} "
                f"${price_pnl:>+9,.4f} "
                f"${net:>+9,.4f}"
            )
        print(f"  {'-'*78}")
        print(f"  {'Total net P&L':>64} ${total_net:>+9,.4f}")

    if closed_pairs:
        print(f"\n  CLOSED PAIRS")
        print(f"  {'-'*50}")
        total_realized = 0.0
        for p in closed_pairs:
            sp = p.short_exit_price or p.short_entry_price
            lp = p.long_exit_price or p.long_entry_price
            realized = p.net_pnl(sp, lp)
            total_realized += realized
            print(f"  {p.pair_id:<10} {p.base:<8} {p.short_exchange} / {p.long_exchange}  "
                  f"realized: ${realized:>+9,.4f}")
        print(f"  {'Total realized':>48} ${total_realized:>+9,.4f}")

    print(f"{'='*82}\n")
