import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import config
from exchange.registry import EXCHANGES

PERIODS_PER_YEAR = 3 * 365  # using rate_per_8h, so 3 settlements/day

# Shared TTL cache for fetch_all() — used by both HTTP routes and WS broadcaster
# so only one actual set of exchange API calls happens per cycle.
_fetch_cache: dict = {"data": None, "ts": 0.0, "scanned_at": ""}
_FETCH_TTL = 10  # seconds


def format_time_until(ts_ms: int) -> str:
    """Render '2h 14m' or '47m' or '12s' for an upcoming unix-ms timestamp."""
    if ts_ms <= 0:
        return "?"
    diff_s = max(0, (ts_ms - int(time.time() * 1000)) / 1000)
    if diff_s <= 60:
        return f"{int(diff_s)}s"
    h = int(diff_s // 3600)
    m = int((diff_s % 3600) // 60)
    return f"{h}h {m:02d}m" if h > 0 else f"{m}m"


def fetch_all() -> dict[str, list[dict]]:
    """
    Two-pass fetch:
      1. Cheap exchanges (one bulk call each) — fetched in parallel.
      2. Expensive exchanges (per-instrument) — only for bases that already
         appeared in step 1, fetched in parallel.

    Returns {base: [rows from each exchange]}.
    """
    cheap = [ex for ex in EXCHANGES if not ex.per_instrument]
    expensive = [ex for ex in EXCHANGES if ex.per_instrument]

    by_base: dict[str, list[dict]] = {}

    def _fetch(ex, bases=None):
        try:
            return ex.get_funding_rates(bases=bases)
        except Exception as e:
            print(f"  [{ex.name}] fetch error: {e}")
            return []

    # Pass 1: cheap exchanges
    with ThreadPoolExecutor(max_workers=max(1, len(cheap))) as pool:
        futures = {pool.submit(_fetch, ex): ex for ex in cheap}
        for f in as_completed(futures):
            for row in f.result():
                by_base.setdefault(row["base"], []).append(row)

    # Pass 2: expensive exchanges, only for bases we've already seen
    candidate_bases = [b for b, rows in by_base.items() if len(rows) >= 1]
    if expensive and candidate_bases:
        with ThreadPoolExecutor(max_workers=max(1, len(expensive))) as pool:
            futures = {pool.submit(_fetch, ex, candidate_bases): ex for ex in expensive}
            for f in as_completed(futures):
                for row in f.result():
                    by_base.setdefault(row["base"], []).append(row)

    return by_base


def _fetch_cached() -> dict[str, list[dict]]:
    """fetch_all() with TTL cache. Call this instead of fetch_all() directly."""
    now = time.monotonic()
    if _fetch_cache["data"] is None or now - _fetch_cache["ts"] > _FETCH_TTL:
        _fetch_cache["data"] = fetch_all()
        _fetch_cache["ts"] = now
        _fetch_cache["scanned_at"] = datetime.now(tz=timezone.utc).isoformat()
    return _fetch_cache["data"]


def force_refresh() -> None:
    """Expire the fetch cache so the next call fetches fresh data."""
    _fetch_cache["data"] = None
    _fetch_cache["ts"] = 0.0
    _fetch_cache["scanned_at"] = ""


def get_scanned_at() -> str:
    return _fetch_cache.get("scanned_at", "")


def _process_opportunities(by_base: dict) -> list[dict]:
    """Convert raw fetch_all() output into sorted opportunity list."""
    opportunities = []

    for base, rows in by_base.items():
        if len(rows) < 2:
            continue
        if base.upper() in config.EXCLUDED_BASES:
            continue

        liquid_rows = [r for r in rows if r.get("volume_24h_usd", 0) >= config.MIN_24H_VOLUME_USD]
        if len(liquid_rows) < 2:
            continue

        best_short = max(liquid_rows, key=lambda r: r["rate_per_8h"])
        best_long = min(liquid_rows, key=lambda r: r["rate_per_8h"])

        if best_short["exchange"] == best_long["exchange"]:
            continue

        spread = best_short["rate_per_8h"] - best_long["rate_per_8h"]

        opportunities.append({
            "base": base,
            "spread": spread,
            "annual_spread": spread * PERIODS_PER_YEAR,
            "annual_capital_yield": spread * PERIODS_PER_YEAR * config.LEVERAGE / 2,
            "short_exchange": best_short["exchange"],
            "short_rate": best_short["rate_per_8h"],
            "short_raw_rate": best_short["funding_rate"],
            "short_interval": best_short["funding_interval"],
            "short_price": best_short["mark_price"],
            "long_exchange": best_long["exchange"],
            "long_rate": best_long["rate_per_8h"],
            "long_raw_rate": best_long["funding_rate"],
            "long_interval": best_long["funding_interval"],
            "long_price": best_long["mark_price"],
            "short_volume_24h": best_short.get("volume_24h_usd", 0),
            "long_volume_24h": best_long.get("volume_24h_usd", 0),
            "short_next_funding": best_short.get("next_funding_time", 0),
            "long_next_funding": best_long.get("next_funding_time", 0),
        })

    opportunities.sort(key=lambda x: x["spread"], reverse=True)
    return opportunities[:config.TOP_N]


def scan() -> list[dict]:
    """Find best cross-exchange arb spread per base asset (uses shared TTL cache)."""
    return _process_opportunities(_fetch_cached())


def print_opportunities(opportunities: list[dict]) -> None:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    exchanges = " x ".join(ex.name for ex in EXCHANGES)

    print(f"\n{'-'*84}")
    print(f"  TOP ARB SPREADS (normalized per-8h)  |  {exchanges}  |  {now}")
    print(f"  Min spread to beat fees: {config.ROUND_TRIP_FEE*100:.3f}% round-trip")
    print(f"{'-'*84}")
    print(f"  {'BASE':<9} {'SHORT ON':<9} {'RATE/8H':>9} {'NEXT':>7}  "
          f"{'LONG ON':<9} {'RATE/8H':>9} {'NEXT':>7}  {'SPREAD':>8} {'CAP APR':>8}")
    print(f"  {'-'*94}")

    for o in opportunities:
        flag = "*" if o["spread"] > config.ROUND_TRIP_FEE else " "
        short_in = format_time_until(o["short_next_funding"])
        long_in = format_time_until(o["long_next_funding"])
        print(
            f"{flag} {o['base']:<9}"
            f"{o['short_exchange']:<9} "
            f"{o['short_rate']*100:>+8.4f}% "
            f"{short_in:>7}  "
            f"{o['long_exchange']:<9} "
            f"{o['long_rate']*100:>+8.4f}% "
            f"{long_in:>7}  "
            f"{o['spread']*100:>+7.4f}% "
            f"{o['annual_capital_yield']*100:>+7.2f}%"
        )

    print(f"  {'-'*94}")
    print(f"  * = spread exceeds round-trip fee cost ({config.ROUND_TRIP_FEE*100:.3f}%)")
    print(f"  NEXT = time until that exchange's next funding settlement")
    print(f"  CAP APR = realistic return on total deployed capital (both legs)")
