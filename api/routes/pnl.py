import csv
from pathlib import Path
from fastapi import APIRouter
from api.schemas import PnlHistoryResponse, PnlPoint

router = APIRouter()

LOG_PATH = Path(__file__).parent.parent.parent / "data" / "trades_log.csv"


@router.get("/history", response_model=PnlHistoryResponse)
def get_pnl_history():
    if not LOG_PATH.exists():
        return PnlHistoryResponse(points=[])

    with open(LOG_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    cumulative = 0.0
    points: list[PnlPoint] = []
    for row in rows:
        event_type = row.get("event_type", "")
        amount = float(row.get("amount_usd", 0) or 0)

        # Only funding and close events contribute to realized P&L
        if event_type == "funding":
            cumulative += amount
        elif event_type == "close":
            # Close event amount_usd is realized net P&L (already includes prior funding)
            # We just mark it — the delta is fees+close P&L component
            cumulative += amount
        elif event_type == "open":
            # Open deducts the reservation fee
            cumulative -= amount

        if event_type in ("open", "funding", "close"):
            points.append(PnlPoint(
                timestamp=row.get("timestamp", ""),
                cumulative_pnl=round(cumulative, 4),
                event_type=event_type,
                pair_id=row.get("pair_id", ""),
                amount_usd=amount,
            ))

    return PnlHistoryResponse(points=points)
