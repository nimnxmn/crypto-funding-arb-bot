# Crypto Funding Arb Bot

A paper trading dashboard for cross-exchange perpetual futures funding rate arbitrage. Exploits funding rate differentials between Binance, Bybit, and OKX with a delta-neutral strategy — short the high-rate exchange, long the low-rate exchange, pocket the spread.

![Dashboard](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Strategy

- **Delta-neutral**: Equal and opposite positions cancel price exposure — profit comes purely from the funding rate spread
- **Cross-exchange**: Binance, Bybit, OKX (USDT-margined linear perpetuals)
- **Leverage**: Configurable 1–10x per position
- **Settlement**: Funding applied automatically every 8h (00:00, 08:00, 16:00 UTC)

## Features

- **Live scanner** — ranks all cross-exchange arb opportunities by spread, shows capital APR, countdown to next funding
- **Paper trading** — open/close delta-neutral pairs, track P&L in real time
- **Auto funding** — applies 8h settlement automatically in the background
- **Auto stop-loss** — monitors open positions and closes them if loss threshold is hit
- **Risk monitoring** — drift detection, liquidation proximity warnings, per-position alerts
- **Real-time dashboard** — WebSocket push every 5s with live mark prices, P&L, and toast notifications
- **Trade history** — full event log with close reason (Manual / Stop-Loss), P&L breakdown
- **Editable settings** — capital limits, risk thresholds, leverage, fee config — all adjustable at runtime

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, FastAPI, WebSocket |
| Frontend | Next.js 14, TailwindCSS, shadcn/ui |
| Charts | TradingView Lightweight Charts v5 |
| State | TanStack Query, Zustand |
| Persistence | CSV (event-sourced paper trade log) |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+

### Installation

```bash
# Clone the repo
git clone https://github.com/nimnxmn/crypto-funding-arb-bot.git
cd crypto-funding-arb-bot

# Install Python dependencies
pip install fastapi uvicorn requests python-dotenv

# Install frontend dependencies
cd web && npm install && cd ..

# Copy env template (only needed for live trading)
cp .env.example .env
```

### Run

```bash
# Terminal 1 — API server (from project root)
uvicorn api.main:app --reload

# Terminal 2 — Frontend (from web/)
cd web && npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
├── api/                  # FastAPI backend
│   ├── routes/           # REST endpoints (scanner, positions, risk, config, reset...)
│   ├── ws.py             # WebSocket broadcaster (auto funding + auto stop-loss)
│   └── schemas.py        # Pydantic models
├── strategy/
│   └── scanner.py        # Multi-exchange spread scanner with shared TTL cache
├── paper_trade/
│   └── simulator.py      # ArbPair + PaperTradeSimulator (CSV-backed, event-sourced)
├── risk/
│   └── manager.py        # Drift detection, stop-loss, position validation
├── exchange/             # Public API wrappers (Binance, Bybit, OKX)
├── live/                 # Live trading skeleton (authenticated order placement)
├── config.py             # All thresholds and constants (mutable at runtime)
├── data/
│   └── trades_log.csv    # Paper trade event log (gitignored)
└── web/                  # Next.js frontend
    ├── app/              # Pages (dashboard, history, settings)
    ├── components/       # UI components
    └── lib/              # API client, types, WebSocket hook
```

## Key Concepts

**Notional vs Collateral**
- `size_usd` = notional per leg (what you're trading)
- Collateral per leg = `size_usd / leverage`
- Total capital locked = `size_usd / leverage × 2`

**Capital APR**
The scanner shows spread APR normalized to the actual capital deployed (both legs), not the notional. At 1x leverage, capital APR = spread APR / 2.

**Break-even spread**
Round-trip taker fees are ~0.20% (4 fills × 0.05%). Any opportunity below this threshold is filtered out by default (`MIN_SPREAD_MULTIPLIER = 2.0`).

## Configuration

All thresholds are editable from the Settings page at runtime without restarting:

| Setting | Default | Description |
|---|---|---|
| Total Capital | $10,000 | Max USDT across all exchanges |
| Max Position Size | 20% | Max % of capital per pair |
| Default Leverage | 1x | Applied to new positions |
| Stop-Loss | 2% | Close if net P&L drops below this % of collateral |
| Drift Warning | 0.3% | Alert when price divergence exceeds this |
| Drift Critical | 1.0% | Suggest close/reopen |
| Min Spread Multiplier | 2× | Spread must be ≥ this × round-trip fee |
| Min 24h Volume | $1M | Liquidity filter per leg |

## Live Trading

Live trading support is scaffolded (`live/trader.py`) but requires:
1. API keys in `.env` (see `.env.example`)
2. Setting `TRADING_MODE=live`

Use with caution — real funds at risk.

## Limitations

- Retail taker fees (0.05%) make small spreads unprofitable vs VIP-tier traders
- Slippage between parallel fills is real on low-liquidity pairs
- Stock-token synthetics (NVDA, GOOGL, etc.) are excluded — different price feeds break delta neutrality
- Capital efficiency at 1x leverage requires 2× the notional in collateral

## License

MIT
