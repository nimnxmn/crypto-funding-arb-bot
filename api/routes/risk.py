from fastapi import APIRouter, Depends
from api.schemas import RiskResponse, RiskResult
from api.deps import get_simulator
from paper_trade.simulator import PaperTradeSimulator
from risk.manager import check_all
from strategy.scanner import fetch_all

router = APIRouter()


def _build_live_data(by_base: dict) -> dict:
    live_data: dict[str, dict[str, dict]] = {}
    for base, rows in by_base.items():
        live_data[base] = {}
        for row in rows:
            live_data[base][row["exchange"]] = {
                "funding_rate": row["rate_per_8h"],
                "mark_price": row["mark_price"],
            }
    return live_data


@router.get("", response_model=RiskResponse)
def get_risk(sim: PaperTradeSimulator = Depends(get_simulator)):
    open_pairs = sim.open_pairs()
    if not open_pairs:
        return RiskResponse(results=[])

    bases = list({p.base for p in open_pairs})
    by_base = fetch_all()
    live_data = _build_live_data(by_base)
    results = check_all(sim, live_data)
    return RiskResponse(results=[RiskResult(**r) for r in results])
