import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from exchange.base import BaseExchange, normalize_to_8h

BASE_URL = "https://www.okx.com"
MAX_WORKERS = 12  # OKX rate limit: 20 req / 2s on funding-rate endpoint


class OKX(BaseExchange):
    name = "OKX"
    per_instrument = True

    def __init__(self):
        super().__init__()
        self._ticker_cache: dict[str, dict] = {}
        self._ticker_cache_ts: float = 0.0

    def _get_tickers(self) -> dict[str, dict]:
        """Cached mark price + 24h volume for all SWAPs (refresh every 30s).
        Fetches mark-price and tickers endpoints in parallel."""
        if time.time() - self._ticker_cache_ts < 30 and self._ticker_cache:
            return self._ticker_cache

        out: dict[str, dict] = {}

        def fetch_marks():
            r = self.session.get(f"{BASE_URL}/api/v5/public/mark-price",
                                 params={"instType": "SWAP"}, timeout=10)
            r.raise_for_status()
            return r.json().get("data", [])

        def fetch_tickers():
            r = self.session.get(f"{BASE_URL}/api/v5/market/tickers",
                                 params={"instType": "SWAP"}, timeout=10)
            r.raise_for_status()
            return r.json().get("data", [])

        # Fetch both endpoints in parallel
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_marks = pool.submit(fetch_marks)
            f_ticks = pool.submit(fetch_tickers)
            try:
                for d in f_marks.result():
                    out[d["instId"]] = {"markPx": float(d["markPx"]), "vol_usd": 0.0}
            except Exception:
                pass
            try:
                for d in f_ticks.result():
                    inst_id = d["instId"]
                    if inst_id not in out:
                        continue
                    try:
                        vol_base = float(d.get("volCcy24h") or 0)
                        out[inst_id]["vol_usd"] = vol_base * out[inst_id]["markPx"]
                    except (TypeError, ValueError):
                        pass
            except Exception:
                pass

        self._ticker_cache = out
        self._ticker_cache_ts = time.time()
        return out

    def _fetch_funding(self, inst_id: str) -> dict | None:
        """Fetch one instrument's funding rate."""
        try:
            resp = self.session.get(f"{BASE_URL}/api/v5/public/funding-rate",
                                    params={"instId": inst_id}, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            if not data:
                return None
            d = data[0]
            rate_str = d.get("fundingRate", "")
            if rate_str == "":
                return None
            try:
                interval_ms = int(d["nextFundingTime"]) - int(d["fundingTime"])
                interval = max(1, round(interval_ms / 3_600_000))
            except (KeyError, ValueError):
                interval = 8
            return {
                "funding_rate": float(rate_str),
                "funding_interval": interval,
                "next_funding_time": int(d.get("nextFundingTime") or 0),
            }
        except Exception:
            return None

    def get_funding_rates(self, bases: list[str] | None = None) -> list[dict]:
        tickers = self._get_tickers()

        if bases is None:
            inst_ids = [k for k in tickers if k.endswith("-USDT-SWAP")]
        else:
            wanted = {b.upper() for b in bases}
            inst_ids = [f"{b}-USDT-SWAP" for b in wanted if f"{b}-USDT-SWAP" in tickers]

        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._fetch_funding, iid): iid for iid in inst_ids}
            for future in as_completed(futures):
                iid = futures[future]
                row = future.result()
                if row is None:
                    continue
                base = iid.split("-")[0]
                tk = tickers.get(iid, {})
                results.append({
                    "exchange": self.name,
                    "base": base,
                    "funding_rate": row["funding_rate"],
                    "funding_interval": row["funding_interval"],
                    "rate_per_8h": normalize_to_8h(row["funding_rate"], row["funding_interval"]),
                    "mark_price": tk.get("markPx", 0.0),
                    "next_funding_time": row["next_funding_time"],
                    "volume_24h_usd": tk.get("vol_usd", 0.0),
                })
        return results
