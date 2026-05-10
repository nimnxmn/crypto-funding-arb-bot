import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env not loaded; set env vars manually or install python-dotenv

# ── Trading mode ──────────────────────────────────────────────────────────────

TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # "paper" or "live"

# ── Strategy ──────────────────────────────────────────────────────────────────

# Taker fee per side
TAKER_FEE = 0.0005  # 0.05%

# Round-trip fee cost (open + close, both sides)
ROUND_TRIP_FEE = TAKER_FEE * 4  # 0.20%

# Top N symbols to show in scanner output
TOP_N = 20

# How often to refresh funding rates (seconds)
SCAN_INTERVAL = 60

# ── Risk Management ──────────────────────────────────────────────────────────

TOTAL_CAPITAL = 10_000.0     # your total capital in USDT (adjust this)
MAX_POSITION_PCT = 0.20      # max 20% of capital per pair leg
LEVERAGE = 1                 # default leverage for new positions (1–10)
DRIFT_WARNING_PCT = 0.003    # 0.3% price drift between exchanges → warning
DRIFT_CRITICAL_PCT = 0.010   # 1.0% drift → suggest close/reopen
STOP_LOSS_PCT = 0.02         # close pair if net P&L < -2% of position size
MIN_SPREAD_MULTIPLIER = 2.0  # spread must be > 2× round-trip fees to open

# Minimum 24h notional volume on EACH leg's exchange for the symbol to be tradeable.
# Filters out illiquid pairs where slippage would eat the spread.
MIN_24H_VOLUME_USD = 1_000_000  # $1M daily minimum

# ── Stock/ETF tokens to exclude — their prices diverge between exchanges ──────
# because each exchange uses a different price feed (not true crypto arb)
EXCLUDED_BASES = {
    "NVDA", "AMD", "TSLA", "AAPL", "GOOGL", "MSFT", "AMZN", "META",
    "NFLX", "COIN", "MSTR", "QQQ", "SPY", "EWY", "MU", "INTC",
    "BABA", "PLTR", "HOOD", "RBLX", "SQ", "PYPL", "SNAP", "UBER",
    "ABNB", "LYFT", "DASH", "DKNG", "PENN", "GME", "AMC", "BB",
}
