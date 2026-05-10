from fastapi import APIRouter
from pydantic import BaseModel
from api.deps import set_config

router = APIRouter()


class UpdateConfigRequest(BaseModel):
    total_capital: float | None = None
    max_position_pct: float | None = None
    stop_loss_pct: float | None = None
    drift_warning_pct: float | None = None
    drift_critical_pct: float | None = None
    min_spread_multiplier: float | None = None
    min_24h_volume_usd: float | None = None
    leverage: int | None = None


_FIELD_TO_ATTR = {
    "total_capital":       "TOTAL_CAPITAL",
    "max_position_pct":    "MAX_POSITION_PCT",
    "stop_loss_pct":       "STOP_LOSS_PCT",
    "drift_warning_pct":   "DRIFT_WARNING_PCT",
    "drift_critical_pct":  "DRIFT_CRITICAL_PCT",
    "min_spread_multiplier": "MIN_SPREAD_MULTIPLIER",
    "min_24h_volume_usd":  "MIN_24H_VOLUME_USD",
    "leverage":            "LEVERAGE",
}


@router.post("/config")
def update_config(req: UpdateConfigRequest):
    for field, attr in _FIELD_TO_ATTR.items():
        val = getattr(req, field)
        if val is not None:
            set_config(attr, val)
    return {"ok": True}
