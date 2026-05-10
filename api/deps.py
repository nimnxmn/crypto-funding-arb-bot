"""
Singleton instances shared across all API routes.
Instantiated once on app startup, injected via FastAPI dependency.
"""
from functools import lru_cache
import config as _config

from paper_trade.simulator import PaperTradeSimulator

# ── Runtime mode override ─────────────────────────────────────────────────────
_runtime_mode: str = _config.TRADING_MODE


def get_mode() -> str:
    return _runtime_mode


def set_mode(mode: str) -> None:
    global _runtime_mode
    _runtime_mode = mode


# ── Runtime config overrides ──────────────────────────────────────────────────
def set_config(key: str, value) -> None:
    """Update a config value at runtime. Mutates the live config module so all
    callers that reference config.X (not bound names) see the new value."""
    setattr(_config, key, value)


# ── Simulator singleton ───────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_simulator() -> PaperTradeSimulator:
    return PaperTradeSimulator()


def reset_simulator() -> None:
    get_simulator.cache_clear()


# ── Live trader (lazy) ────────────────────────────────────────────────────────
_live_trader = None


def get_live_trader():
    global _live_trader
    if _live_trader is None:
        from live.trader import LiveTrader
        _live_trader = LiveTrader()
    return _live_trader
