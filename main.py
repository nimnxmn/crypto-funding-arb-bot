from strategy.scanner import scan, print_opportunities
from strategy.arb import get_live_data, print_pairs
from paper_trade.simulator import PaperTradeSimulator
from risk.manager import check_all, validate_open, print_risk_report

sim = PaperTradeSimulator()


def menu_scan():
    print("\nFetching funding rates from all exchanges...")
    opps = scan()
    print_opportunities(opps)


def menu_open():
    print("\nFetching live spreads...")
    opps = scan()
    print_opportunities(opps)

    base = input("\n  Enter base asset to trade (e.g. BTC): ").strip().upper()
    match = next((o for o in opps if o["base"] == base), None)
    if not match:
        print(f"  {base} not found in current opportunities.")
        return

    print(f"\n  Best spread for {base}:")
    print(f"  SHORT on {match['short_exchange']}  rate: {match['short_rate']*100:+.4f}%/8h  "
          f"price: ${match['short_price']:,.4f}")
    print(f"  LONG  on {match['long_exchange']}  rate: {match['long_rate']*100:+.4f}%/8h  "
          f"price: ${match['long_price']:,.4f}")
    print(f"  Net spread: {match['spread']*100:+.4f}%/8h  ({match['annual_spread']*100:+.2f}% annualized)")

    size_input = input("\n  Position size per leg in USDT (e.g. 1000): ").strip()
    try:
        size_usd = float(size_input)
    except ValueError:
        print("  Invalid size.")
        return

    allowed, reason = validate_open(match["spread"], size_usd, sim)
    if not allowed:
        print(f"\n  [RISK BLOCK] {reason}")
        return

    confirm = input(f"  Open {base} arb pair at ${size_usd:,.0f} per leg? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    pair = sim.open_pair(
        base=base,
        size_usd=size_usd,
        short_exchange=match["short_exchange"],
        short_price=match["short_price"],
        short_rate=match["short_rate"],
        long_exchange=match["long_exchange"],
        long_price=match["long_price"],
        long_rate=match["long_rate"],
    )
    print(f"\n  Opened arb pair {pair.pair_id}")
    print(f"  SHORT {base} on {pair.short_exchange} @ ${pair.short_entry_price:,.4f}")
    print(f"  LONG  {base} on {pair.long_exchange} @ ${pair.long_entry_price:,.4f}")
    print(f"  Total fees reserved: ${pair.fees_paid:.4f}")


def menu_positions():
    print("\nFetching live prices...")
    live_data = get_live_data()
    print_pairs(sim, live_data)


def menu_funding():
    open_pairs = sim.open_pairs()
    if not open_pairs:
        print("\n  No open pairs.")
        return

    print(f"\n  Fetching live rates for {len(open_pairs)} open pair(s)...")
    live_data = get_live_data()
    payments = sim.apply_funding(live_data)

    if not payments:
        print("  Could not fetch live rates for any open pair.")
        return

    total = sum(payments.values())
    for pid, amt in payments.items():
        p = sim.pairs[pid]
        print(f"  {pid}  {p.base:<8} {p.short_exchange} / {p.long_exchange}  "
              f"funding: ${amt:>+.4f}")
    print(f"  Total this period: ${total:>+.4f}")


def menu_risk():
    open_pairs = sim.open_pairs()
    if not open_pairs:
        print("\n  No open pairs.")
        return
    print("\n  Fetching live prices for risk check...")
    live_data = get_live_data()
    results = check_all(sim, live_data)
    print_risk_report(results)


def menu_close():
    open_pairs = sim.open_pairs()
    if not open_pairs:
        print("\n  No open pairs.")
        return

    live_data = get_live_data()
    print_pairs(sim, live_data)

    pid = input("  Enter Pair ID to close: ").strip()
    if pid not in sim.pairs or sim.pairs[pid].status != "open":
        print("  Pair not found or already closed.")
        return

    pair = sim.pairs[pid]
    base_data = live_data.get(pair.base, {})
    short_price = base_data.get(pair.short_exchange, {}).get("mark_price", pair.short_entry_price)
    long_price = base_data.get(pair.long_exchange, {}).get("mark_price", pair.long_entry_price)

    print(f"\n  Closing {pair.base}  SHORT on {pair.short_exchange} @ ${short_price:,.4f}"
          f"  LONG on {pair.long_exchange} @ ${long_price:,.4f}")
    confirm = input("  Confirm close? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    realized = sim.close_pair(pid, short_price, long_price)
    print(f"\n  Pair {pid} closed.  Realized P&L: ${realized:>+.4f}")


MENU = """
ARB_bot — Paper Trade  (Binance x OKX x Bybit)
  [1] Scan arb opportunities
  [2] Open arb pair
  [3] View positions + P&L
  [4] Apply funding payment
  [5] Risk report
  [6] Close pair
  [7] Exit
"""

ACTIONS = {
    "1": menu_scan,
    "2": menu_open,
    "3": menu_positions,
    "4": menu_funding,
    "5": menu_risk,
    "6": menu_close,
}

if __name__ == "__main__":
    print(f"ARB_bot started. {len(sim.pairs)} pair(s) loaded from log.")
    while True:
        print(MENU)
        choice = input("  > ").strip()
        if choice == "7":
            print("Bye.")
            break
        action = ACTIONS.get(choice)
        if action:
            try:
                action()
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print("  Invalid choice.")
