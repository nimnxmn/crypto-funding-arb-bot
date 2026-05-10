from fastapi import APIRouter, HTTPException, Depends
import config
from api.schemas import (
    PositionsResponse, PairStatus, OpenPairRequest,
    ClosePairRequest, ValidationResult,
)
from api.deps import get_simulator
from paper_trade.simulator import PaperTradeSimulator, ArbPair
from risk.manager import validate_open

router = APIRouter()


def _pair_to_status(pair: ArbPair, short_price=None, long_price=None) -> PairStatus:
    if pair.status == "open" and short_price is not None and long_price is not None:
        price_pnl = pair.price_pnl(short_price, long_price)
        net_pnl = pair.net_pnl(short_price, long_price)
    elif pair.status == "closed" and pair.short_exit_price and pair.long_exit_price:
        price_pnl = pair.price_pnl(pair.short_exit_price, pair.long_exit_price)
        net_pnl = pair.net_pnl(pair.short_exit_price, pair.long_exit_price)
    else:
        price_pnl = None
        net_pnl = None

    liq_short = pair.liq_price_short() if pair.leverage > 1 else None
    liq_long = pair.liq_price_long() if pair.leverage > 1 else None

    return PairStatus(
        pair_id=pair.pair_id,
        base=pair.base,
        status=pair.status,
        short_exchange=pair.short_exchange,
        long_exchange=pair.long_exchange,
        size_usd=pair.size_usd,
        leverage=pair.leverage,
        short_entry_price=pair.short_entry_price,
        long_entry_price=pair.long_entry_price,
        short_rate_at_open=pair.short_rate_at_open,
        long_rate_at_open=pair.long_rate_at_open,
        fees_paid=pair.fees_paid,
        funding_collected=pair.funding_collected,
        opened_at=pair.opened_at,
        closed_at=pair.closed_at,
        short_exit_price=pair.short_exit_price,
        long_exit_price=pair.long_exit_price,
        liq_price_short=liq_short,
        liq_price_long=liq_long,
        close_reason=pair.close_reason,
        price_pnl=price_pnl,
        net_pnl=net_pnl,
    )


@router.get("", response_model=PositionsResponse)
def get_positions(sim: PaperTradeSimulator = Depends(get_simulator)):
    open_pairs = [_pair_to_status(p, p.short_entry_price, p.long_entry_price) for p in sim.open_pairs()]
    closed_pairs = [_pair_to_status(p) for p in sim.closed_pairs()]
    return PositionsResponse(open=open_pairs, closed=closed_pairs)


@router.post("/validate", response_model=ValidationResult)
def validate_pair(req: OpenPairRequest, sim: PaperTradeSimulator = Depends(get_simulator)):
    spread = req.short_rate - req.long_rate
    ok, msg = validate_open(spread, req.size_usd, req.leverage, sim)
    return ValidationResult(ok=ok, message=msg)


@router.post("", response_model=PairStatus)
def open_position(req: OpenPairRequest, sim: PaperTradeSimulator = Depends(get_simulator)):
    spread = req.short_rate - req.long_rate
    ok, msg = validate_open(spread, req.size_usd, req.leverage, sim)
    if not ok:
        raise HTTPException(status_code=422, detail=msg)

    pair = sim.open_pair(
        base=req.base,
        size_usd=req.size_usd,
        short_exchange=req.short_exchange,
        short_price=req.short_price,
        short_rate=req.short_rate,
        long_exchange=req.long_exchange,
        long_price=req.long_price,
        long_rate=req.long_rate,
        leverage=req.leverage,
    )
    return _pair_to_status(pair, req.short_price, req.long_price)


@router.post("/close-all")
def close_all_positions(sim: PaperTradeSimulator = Depends(get_simulator)):
    """Close every open position at current live mark prices."""
    from strategy.scanner import _fetch_cached
    by_base = _fetch_cached()
    live_data = {
        base: {r["exchange"]: {"mark_price": r["mark_price"]} for r in rows}
        for base, rows in by_base.items()
    }
    count = 0
    for pair in list(sim.open_pairs()):
        bd = live_data.get(pair.base, {})
        sp = bd.get(pair.short_exchange, {}).get("mark_price", pair.short_entry_price)
        lp = bd.get(pair.long_exchange, {}).get("mark_price", pair.long_entry_price)
        sim.close_pair(pair.pair_id, sp, lp)
        count += 1
    return {"closed": count}


@router.post("/{pair_id}/close", response_model=PairStatus)
def close_position(
    pair_id: str,
    req: ClosePairRequest,
    sim: PaperTradeSimulator = Depends(get_simulator),
):
    pair = sim.pairs.get(pair_id)
    if not pair:
        raise HTTPException(status_code=404, detail=f"Pair {pair_id} not found")
    if pair.status != "open":
        raise HTTPException(status_code=409, detail=f"Pair {pair_id} is already closed")

    sim.close_pair(pair_id, req.short_price, req.long_price)
    return _pair_to_status(pair)
