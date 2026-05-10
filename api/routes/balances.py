from fastapi import APIRouter, HTTPException
import config
from api.schemas import BalancesResponse, BalanceEntry

router = APIRouter()


@router.get("", response_model=BalancesResponse)
def get_balances():
    if config.TRADING_MODE != "live":
        return BalancesResponse(balances=[])

    try:
        from exchange.binance_auth import BinanceAuth
        from exchange.okx_auth import OkxAuth
        from exchange.bybit_auth import BybitAuth

        balances = []
        for name, AuthClass in [("Binance", BinanceAuth), ("OKX", OkxAuth), ("Bybit", BybitAuth)]:
            try:
                client = AuthClass()
                bal = client.get_usdt_balance()
                balances.append(BalanceEntry(exchange=name, balance_usdt=bal))
            except Exception as e:
                balances.append(BalanceEntry(exchange=name, balance_usdt=0.0))

        return BalancesResponse(balances=balances)
    except ImportError:
        raise HTTPException(status_code=503, detail="Auth modules not available")
