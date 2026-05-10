import base64
import hashlib
import hmac
import json
import math
import time
import requests
from datetime import datetime, timezone

BASE_URL = "https://www.okx.com"


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _sign(timestamp: str, method: str, path: str, body: str, secret: str) -> str:
    message = timestamp + method.upper() + path + body
    mac = hmac.new(secret.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def _headers(api_key: str, secret: str, passphrase: str,
             method: str, path: str, body: str = "") -> dict:
    ts = _timestamp()
    return {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": _sign(ts, method, path, body, secret),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }


def get_balance(api_key: str, secret: str, passphrase: str) -> float:
    """Return available USDT balance."""
    path = "/api/v5/account/balance?ccy=USDT"
    resp = requests.get(BASE_URL + path,
                        headers=_headers(api_key, secret, passphrase, "GET", path),
                        timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if data:
        for detail in data[0].get("details", []):
            if detail["ccy"] == "USDT":
                return float(detail["availEq"])
    return 0.0


def get_contract_size(inst_id: str) -> float:
    """Return contract multiplier (ctVal) for a SWAP instrument."""
    resp = requests.get(f"{BASE_URL}/api/v5/public/instruments",
                        params={"instType": "SWAP", "instId": inst_id}, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return float(data[0]["ctVal"]) if data else 1.0


def place_market_order(inst_id: str, side: str, sz: float,
                       api_key: str, secret: str, passphrase: str) -> dict:
    """
    Place a market order on OKX futures.
    inst_id: e.g. "BTC-USDT-SWAP"
    side: "buy" or "sell"
    sz: number of contracts
    """
    path = "/api/v5/trade/order"
    body = json.dumps({
        "instId": inst_id,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(math.floor(sz)),
    })
    resp = requests.post(BASE_URL + path, data=body,
                         headers=_headers(api_key, secret, passphrase, "POST", path, body),
                         timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != "0":
        raise RuntimeError(f"OKX order failed: {result}")
    return result


def get_open_positions(api_key: str, secret: str, passphrase: str) -> list[dict]:
    path = "/api/v5/account/positions?instType=SWAP"
    resp = requests.get(BASE_URL + path,
                        headers=_headers(api_key, secret, passphrase, "GET", path),
                        timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_funding_payments(inst_id: str, start_time_ms: int,
                         api_key: str, secret: str, passphrase: str) -> list[dict]:
    """
    Fetch funding fee bills for an instrument since start_time_ms.
    OKX bill type 8 = funding fee. Returns normalized dicts.
    """
    # type=8 (funding), subType=173 (funding fee expense), 174 (funding fee income).
    # Use only type=8 to get all funding events.
    path = f"/api/v5/account/bills-archive?instType=SWAP&type=8&begin={start_time_ms}"
    resp = requests.get(BASE_URL + path,
                        headers=_headers(api_key, secret, passphrase, "GET", path),
                        timeout=10)
    resp.raise_for_status()
    out = []
    for r in resp.json().get("data", []):
        if r.get("instId") != inst_id:
            continue
        out.append({"time": int(r["ts"]), "amount_usd": float(r["balChg"])})
    return out
