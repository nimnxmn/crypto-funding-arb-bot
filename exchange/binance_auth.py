import hashlib
import hmac
import math
import time
import requests

BASE_URL = "https://fapi.binance.com"


def _sign(params: dict, secret: str) -> str:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()


def _headers(api_key: str) -> dict:
    return {"X-MBX-APIKEY": api_key}


def _ts() -> int:
    return int(time.time() * 1000)


def get_balance(api_key: str, secret: str) -> float:
    """Return available USDT balance in futures wallet."""
    params = {"timestamp": _ts()}
    params["signature"] = _sign(params, secret)
    resp = requests.get(f"{BASE_URL}/fapi/v2/balance", params=params, headers=_headers(api_key), timeout=10)
    resp.raise_for_status()
    for asset in resp.json():
        if asset["asset"] == "USDT":
            return float(asset["availableBalance"])
    return 0.0


def get_qty_step(symbol: str) -> float:
    """Return the lot size step for a symbol (e.g. 0.001 for BTCUSDT)."""
    resp = requests.get(f"{BASE_URL}/fapi/v1/exchangeInfo", timeout=10)
    resp.raise_for_status()
    for s in resp.json()["symbols"]:
        if s["symbol"] == symbol:
            for f in s["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    return float(f["stepSize"])
    return 1.0


def round_qty(qty: float, step: float) -> float:
    precision = max(0, round(-math.log10(step)))
    return round(math.floor(qty / step) * step, precision)


def place_market_order(symbol: str, side: str, quantity: float,
                       api_key: str, secret: str) -> dict:
    """
    Place a market order on Binance futures.
    side: "BUY" (open long / close short) or "SELL" (open short / close long)
    quantity: in base asset (e.g. BTC)
    """
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": _ts(),
    }
    params["signature"] = _sign(params, secret)
    resp = requests.post(f"{BASE_URL}/fapi/v1/order", params=params,
                         headers=_headers(api_key), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_open_positions(api_key: str, secret: str) -> list[dict]:
    """Return all positions with non-zero size."""
    params = {"timestamp": _ts()}
    params["signature"] = _sign(params, secret)
    resp = requests.get(f"{BASE_URL}/fapi/v2/positionRisk", params=params,
                        headers=_headers(api_key), timeout=10)
    resp.raise_for_status()
    return [p for p in resp.json() if float(p["positionAmt"]) != 0]


def get_funding_payments(symbol: str, start_time_ms: int,
                         api_key: str, secret: str) -> list[dict]:
    """
    Fetch FUNDING_FEE entries for a symbol since start_time_ms.
    Returns list of normalized dicts: {"time": ms, "amount_usd": float}.
    """
    params = {
        "incomeType": "FUNDING_FEE",
        "symbol": symbol,
        "startTime": start_time_ms,
        "limit": 1000,
        "timestamp": _ts(),
    }
    params["signature"] = _sign(params, secret)
    resp = requests.get(f"{BASE_URL}/fapi/v1/income", params=params,
                        headers=_headers(api_key), timeout=10)
    resp.raise_for_status()
    return [{"time": int(r["time"]), "amount_usd": float(r["income"])} for r in resp.json()]
