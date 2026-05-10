from fastapi import APIRouter
from api.schemas import ScannerResponse, Opportunity
from strategy.scanner import scan, force_refresh, get_scanned_at

router = APIRouter()


@router.get("/scanner", response_model=ScannerResponse)
def get_scanner():
    """Return current scanner opportunities (uses shared 30s TTL cache)."""
    opps = scan()
    return ScannerResponse(
        opportunities=[Opportunity(**o) for o in opps],
        scanned_at=get_scanned_at(),
    )


@router.post("/scanner/refresh")
def refresh_scanner():
    """Expire the cache and immediately fetch fresh data."""
    force_refresh()
    opps = scan()
    return ScannerResponse(
        opportunities=[Opportunity(**o) for o in opps],
        scanned_at=get_scanned_at(),
    )
