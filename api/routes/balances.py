from fastapi import APIRouter
import config
from api.schemas import BalancesResponse, BalanceEntry

router = APIRouter()


@router.get("", response_model=BalancesResponse)
def get_balances():
    if config.TRADING_MODE != "live":
        return BalancesResponse(balances=[])

    from live.trader import get_balances as _get_balances
    raw = _get_balances()
    balances = [
        BalanceEntry(exchange=name, balance_usdt=bal if isinstance(bal, float) else 0.0)
        for name, bal in raw.items()
    ]
    return BalancesResponse(balances=balances)
