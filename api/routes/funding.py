from fastapi import APIRouter, Depends
from api.schemas import FundingApplyResponse
from api.deps import get_simulator
from paper_trade.simulator import PaperTradeSimulator
from strategy.scanner import fetch_all
import api.ws as ws_module

router = APIRouter()


def _build_live_data(by_base: dict) -> dict:
    """Convert scanner fetch_all output into the format simulator.apply_funding expects."""
    live_data: dict[str, dict[str, dict]] = {}
    for base, rows in by_base.items():
        live_data[base] = {}
        for row in rows:
            live_data[base][row["exchange"]] = {
                "funding_rate": row["rate_per_8h"],
                "mark_price": row["mark_price"],
            }
    return live_data


@router.post("/apply", response_model=FundingApplyResponse)
def apply_funding(sim: PaperTradeSimulator = Depends(get_simulator)):
    """Apply one 8h funding period to all open paper-trade pairs using live rates.
    Also advances the auto-apply period tracker so the next auto-apply
    doesn't double-count the same period."""
    by_base = fetch_all()
    live_data = _build_live_data(by_base)
    payments = sim.apply_funding(live_data)
    # Sync the broadcaster's period tracker so auto-apply skips this period
    ws_module._last_applied_period = ws_module._current_settlement_period()
    return FundingApplyResponse(payments=payments)
