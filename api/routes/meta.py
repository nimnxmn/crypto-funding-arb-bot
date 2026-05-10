from fastapi import APIRouter
import config
from api.schemas import MetaResponse
from api.deps import get_mode

router = APIRouter()


@router.get("/meta", response_model=MetaResponse)
def get_meta():
    return MetaResponse(
        mode=get_mode(),
        total_capital=config.TOTAL_CAPITAL,
        max_position_pct=config.MAX_POSITION_PCT,
        stop_loss_pct=config.STOP_LOSS_PCT,
        drift_warning_pct=config.DRIFT_WARNING_PCT,
        drift_critical_pct=config.DRIFT_CRITICAL_PCT,
        round_trip_fee=config.ROUND_TRIP_FEE,
        min_spread_multiplier=config.MIN_SPREAD_MULTIPLIER,
        min_24h_volume_usd=config.MIN_24H_VOLUME_USD,
        top_n=config.TOP_N,
        leverage=config.LEVERAGE,
    )
