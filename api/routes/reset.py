import csv
from pathlib import Path
from fastapi import APIRouter
from api.deps import reset_simulator

router = APIRouter()

LOG_PATH = Path(__file__).parent.parent.parent / "data" / "trades_log.csv"
FIELDNAMES = [
    "event_id", "event_type", "pair_id", "timestamp",
    "base", "short_exchange", "long_exchange",
    "short_price", "long_price", "size_usd",
    "short_rate", "long_rate", "amount_usd", "notes",
]


@router.post("/reset")
def reset_paper_trade():
    """Wipe all paper trade history and reset the in-memory simulator."""
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()
    reset_simulator()
    return {"ok": True}
