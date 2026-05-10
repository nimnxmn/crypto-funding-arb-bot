import hashlib
import hmac
import json
import math
import time
import requests

BASE_URL = "https://api.bybit.com"
RECV_WINDOW = "5000"


def _ts() -> str:
    return str(int(time.time() * 1000))


def _sign_get(timestamp: str, api_key: str, query_string: str, secret: str) -> str:
    message = timestamp + api_key + RECV_WINDOW + query_string
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _sign_post(timestamp: str, api_key: str, body: str, secret: str) -> str:
    message = timestamp + api_key + RECV_WINDOW + body
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _get_headers(timestamp: str, api_key: str, signature: str) -> dict:
    return {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "Content-Type": "application/json",
    }


def get_balance(api_key: str, secret: str) -> float:
    """Return available USDT balance in unified trading account."""
    qs = "accountType=UNIFIED&coin=USDT"
    ts = _ts()
    sig = _sign_get(ts, api_key, qs, secret)
    resp = requests.get(f"{BASE_URL}/v5/account/wallet-balance",
                        params={"accountType": "UNIFIED", "coin": "USDT"},
                        headers=_get_headers(ts, api_key, sig), timeout=10)
    resp.raise_for_status()
    coins = resp.json()["result"]["list"][0]["coin"]
    for coin in coins:
        if coin["coin"] == "USDT":
            return float(coin["availableToWithdraw"])
    return 0.0


def get_qty_step(symbol: str) -> float:
    """Return lot size step for a linear perpetual."""
    resp = requests.get(f"{BASE_URL}/v5/market/instruments-info",
                        params={"category": "linear", "symbol": symbol}, timeout=10)
    resp.raise_for_status()
    items = resp.json()["result"]["list"]
    if items:
        return float(items[0]["lotSizeFilter"]["qtyStep"])
    return 0.001


def place_market_order(symbol: str, side: str, qty: float,
                       api_key: str, secret: str) -> dict:
    """
    Place a market order on Bybit linear futures.
    side: "Buy" or "Sell"
    qty: in base asset
    """
    ts = _ts()
    body = json.dumps({
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": str(qty),
    })
    sig = _sign_post(ts, api_key, body, secret)
    resp = requests.post(f"{BASE_URL}/v5/order/create", data=body,
                         headers=_get_headers(ts, api_key, sig), timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("retCode") != 0:
        raise RuntimeError(f"Bybit order failed: {result}")
    return result


def get_open_positions(api_key: str, secret: str) -> list[dict]:
    qs = "category=linear&settleCoin=USDT"
    ts = _ts()
    sig = _sign_get(ts, api_key, qs, secret)
    resp = requests.get(f"{BASE_URL}/v5/position/list",
                        params={"category": "linear", "settleCoin": "USDT"},
                        headers=_get_headers(ts, api_key, sig), timeout=10)
    resp.raise_for_status()
    return [p for p in resp.json()["result"]["list"] if float(p["size"]) > 0]


def get_funding_payments(symbol: str, start_time_ms: int,
                         api_key: str, secret: str) -> list[dict]:
    """
    Fetch funding settlement entries for a symbol since start_time_ms.
    Uses Bybit's transaction-log endpoint with type=SETTLEMENT.
    """
    params = {
        "accountType": "UNIFIED",
        "category": "linear",
        "symbol": symbol,
        "type": "SETTLEMENT",
        "startTime": str(start_time_ms),
        "limit": "100",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    ts = _ts()
    sig = _sign_get(ts, api_key, qs, secret)
    resp = requests.get(f"{BASE_URL}/v5/account/transaction-log",
                        params=params, headers=_get_headers(ts, api_key, sig), timeout=10)
    resp.raise_for_status()
    out = []
    for r in resp.json()["result"]["list"]:
        out.append({
            "time": int(r["transactionTime"]),
            "amount_usd": float(r["funding"]) if r.get("funding") else float(r.get("change", 0)),
        })
    return out
