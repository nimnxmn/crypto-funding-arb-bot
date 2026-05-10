# ARB_bot — Crypto Funding Rate Arbitrage Bot

## Project Goal
Build a funding rate arbitrage bot that exploits funding rate differentials across crypto perpetual futures exchanges. The strategy is delta-neutral: hold equal and opposite perp positions to pocket the funding rate spread with minimal directional risk.

## Strategy
- **Type**: Cross-exchange funding rate arbitrage (perp-perp)
- **Mechanism**: Go short on the exchange with high positive funding, go long on the exchange with low/negative funding. Net funding = spread between exchanges, payable each settlement period.
- **Leverage**: Configurable 1–10x per position (default 1x)
- **Exchanges**: Binance, OKX, Bybit (all USDT-margined linear perps)

## Tech Stack
- **Backend**: FastAPI (`api/`) — run with `uvicorn api.main:app --reload`
- **Frontend**: Next.js 14 (`web/`) — run with `npm run dev` inside `web/`
- **Real-time**: WebSocket broadcaster pushes scanner/positions/risk every 5s
- **Notifications**: Telegram (live mode)
- **Persistence**: `data/trades_log.csv` (event-sourced: open/funding/close rows)

## How to Run
```
# Terminal 1 — from ARB_bot/
uvicorn api.main:app --reload

# Terminal 2 — from ARB_bot/web/
npm run dev
```

## Project Structure
```
ARB_bot/
├── CLAUDE.md
├── config.py                    # thresholds, fee constants, excluded bases, env loader
├── .env.example                 # API keys template (copy to .env, never commit)
├── main.py                      # interactive CLI runner (menu)
├── data/
│   └── trades_log.csv           # paper trade event log (open/funding/close rows)
├── exchange/
│   ├── base.py                  # BaseExchange ABC + helpers
│   ├── registry.py              # list of exchange instances used by scanner
│   ├── binance.py               # Binance public API wrapper
│   ├── okx.py                   # OKX public API wrapper (per-instrument)
│   ├── bybit.py                 # Bybit public API wrapper
│   ├── binance_auth.py          # Binance authenticated trading API
│   ├── okx_auth.py              # OKX authenticated trading API
│   └── bybit_auth.py            # Bybit authenticated trading API
├── strategy/
│   ├── scanner.py               # multi-exchange spread scanner; shared 10s TTL cache (_fetch_cached)
│   └── arb.py                   # terminal pretty-print for positions
├── paper_trade/
│   └── simulator.py             # ArbPair + PaperTradeSimulator (CSV-backed, event-sourced)
├── live/
│   ├── trader.py                # live order placement (parallel legs, emergency close)
│   ├── notifier.py              # Telegram notifications
│   └── positions.json           # persistent live position store (auto-created)
├── risk/
│   └── manager.py               # drift detection, stop-loss, validate_open
├── api/
│   ├── main.py                  # FastAPI app, router registration, lifespan
│   ├── deps.py                  # get_simulator (lru_cache), set_config, reset_simulator
│   ├── schemas.py               # Pydantic models for all API types
│   ├── ws.py                    # WebSocket broadcaster (5s loop, auto funding, auto stop-loss)
│   └── routes/
│       ├── meta.py              # GET /api/meta
│       ├── scanner.py           # GET /api/scanner, POST /api/scanner/refresh
│       ├── positions.py         # CRUD /api/positions, POST /close-all
│       ├── funding.py           # POST /api/funding/apply
│       ├── risk.py              # GET /api/risk
│       ├── pnl.py               # GET /api/pnl/history
│       ├── config_route.py      # POST /api/config (runtime config mutation)
│       └── reset.py             # POST /api/reset (wipe CSV + clear simulator cache)
└── web/                         # Next.js 14 frontend
    ├── app/
    │   ├── page.tsx             # main dashboard (scanner, open positions, history, risk, P&L chart)
    │   ├── history/page.tsx     # full trade history page
    │   └── settings/page.tsx    # editable config, leverage, danger zone
    ├── components/
    │   ├── positions/
    │   │   ├── positions-table.tsx        # open positions with live P&L, click-to-detail
    │   │   └── closed-position-detail.tsx # detail dialog for closed trades
    │   ├── trade/open-pair-modal.tsx      # trade entry with leverage selector
    │   ├── chart/pnl-chart.tsx            # lightweight-charts v5 P&L line + trade markers
    │   ├── scanner/scanner-table.tsx      # arb spread table, click to open trade
    │   └── ws-provider.tsx                # WS client, updates react-query cache + toasts
    └── lib/
        ├── api.ts               # all API calls
        ├── types.ts             # TypeScript interfaces
        └── ws.ts                # WebSocket hook
```

## Status — what's built

### ✅ Phase 1 — Multi-exchange scanner
- Three exchanges via parallel `ThreadPoolExecutor` (Binance & Bybit bulk; OKX per-instrument for overlapping bases only)
- Funding rates normalized to per-8h regardless of native interval
- Liquidity filter: drops pairs below `MIN_24H_VOLUME_USD` ($1M default)
- Stock-token blacklist (`EXCLUDED_BASES`) — synthetic tokens have divergent feeds
- Shared 10s TTL cache (`_fetch_cached`) used by both HTTP routes and WS broadcaster — no double fetching

### ✅ Phase 2 — Paper trade engine
- `ArbPair`: delta-neutral position, size_usd = notional per leg, collateral = size_usd / leverage
- Leverage 1–10x; liquidation price estimates included
- Funding math: `net = short_qty × short_mark × short_rate − long_qty × long_mark × long_rate`
- Event-sourced CSV log: open / funding / close events; positions reconstructed on startup
- `close_reason` field: `"manual"` or `"stop_loss"` — stored in CSV and shown in UI

### ✅ Phase 3 — Streamlit dashboard (legacy, superseded)
- Replaced by FastAPI + Next.js dashboard (Phase 6)

### ✅ Phase 4 — Risk management
- **Drift detection**: `drift_pct = |short_price − long_price| / mid` — warning at 0.3%, critical at 1.0%
- **Stop-loss**: triggers when net P&L < `−STOP_LOSS_PCT × (size_usd / leverage)`
- **Liquidation proximity warning** when leverage > 1 and either leg is within 20% of liq price
- **Validate-open**: spread ≥ 2× round-trip fee; collateral ≤ MAX_POSITION_PCT; total deployed ≤ TOTAL_CAPITAL
- All thresholds use `import config` (not `from config import`) so runtime mutation via `/api/config` takes effect immediately

### ✅ Phase 5 — Live trading skeleton
- Authenticated wrappers for all 3 exchanges (HMAC signing)
- `live.trader.open_live_pair`: parallel leg execution, auto emergency-close on partial fill failure
- Lot-size matching: equal notional on both legs, no residual directional exposure
- `live.trader.sync_funding`: pulls actual payments from exchange income endpoints
- Telegram notifier; `TRADING_MODE` env var (`paper` | `live`)

### ✅ Phase 6 — Pro dashboard (built)
FastAPI backend + Next.js 14 frontend with:
- **Real-time WebSocket**: 5s broadcast loop with live mark prices for open position P&L
- **Auto funding**: applies at 8h settlement boundaries (00:00/08:00/16:00 UTC), sends toast notification
- **Auto stop-loss**: WS loop detects and closes positions, sends toast notification
- **Scanner**: last-updated timestamp, manual Refresh button
- **Open positions**: live NET P&L and drift, click-to-detail dialog, Close All with confirmation
- **Trade history**: close reason badge (Manual / Stop-Loss), click-to-detail dialog
- **P&L chart**: lightweight-charts v5, trade open/close markers
- **Settings page**: editable capital, risk, fee config; leverage picker; Reset Account (wipes CSV)
- **Runtime config**: `POST /api/config` mutates `config` module attributes in-place

## Key Architecture Decisions
- **`size_usd` = notional per leg** — UI input is collateral; modal multiplies by leverage before sending
- **Shared fetch cache**: `strategy/scanner.py:_fetch_cached()` is the single price source for HTTP + WS
- **Runtime config mutation**: `api/deps.py:set_config()` calls `setattr(_config, key, value)` — works because all modules use `import config`, not `from config import X`
- **Simulator singleton**: `get_simulator()` uses `@lru_cache(maxsize=1)`; `reset_simulator()` calls `cache_clear()`
- **Leverage default in modal**: synced via `useEffect` on `meta?.leverage` + `openTradeModal` — needed because `useForm` defaultValues only run once at mount

## Known Limitations
- Retail taker fees (0.05%) → break-even spread is 0.20% round-trip
- Capital efficiency is poor at 1× leverage — needs 2× capital deployed per arb size
- Slippage between parallel fills is real on small-cap pairs
- Operational risks: exchange downtime, API rate limits, withdrawal freezes

## Notes
- Funding settlement: most are 8h (00:00/08:00/16:00 UTC); some Binance/OKX symbols are 4h or 1h — scanner normalizes to per-8h
- `MIN_SPREAD_MULTIPLIER = 2.0` means spread must be ≥ 2× round-trip fee to open
- `data/trades_log.csv` and `live/positions.json` contain trade data — do not commit
