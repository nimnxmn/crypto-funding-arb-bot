import time
from exchange.base import BaseExchange, strip_quote, normalize_to_8h

BASE_URL = "https://fapi.binance.com"


class Binance(BaseExchange):
    name = "Binance"
    per_instrument = False

    def __init__(self):
        super().__init__()
        self._interval_cache: dict[str, int] = {}
        self._interval_cache_ts: float = 0.0

    def _funding_intervals(self) -> dict[str, int]:
        """Fetch funding intervals per symbol. Cached for 1 hour."""
        if time.time() - self._interval_cache_ts < 3600 and self._interval_cache:
            return self._interval_cache
        try:
            resp = self.session.get(f"{BASE_URL}/fapi/v1/fundingInfo", timeout=10)
            resp.raise_for_status()
            self._interval_cache = {item["symbol"]: int(item["fundingIntervalHours"])
                                    for item in resp.json()}
            self._interval_cache_ts = time.time()
        except Exception:
            self._interval_cache = {}
        return self._interval_cache

    def _volumes_24h(self) -> dict[str, float]:
        """24h quote volume in USDT per symbol."""
        try:
            resp = self.session.get(f"{BASE_URL}/fapi/v1/ticker/24hr", timeout=10)
            resp.raise_for_status()
            return {item["symbol"]: float(item["quoteVolume"]) for item in resp.json()}
        except Exception:
            return {}

    def get_funding_rates(self, bases: list[str] | None = None) -> list[dict]:
        intervals = self._funding_intervals()
        volumes = self._volumes_24h()
        resp = self.session.get(f"{BASE_URL}/fapi/v1/premiumIndex", timeout=10)
        resp.raise_for_status()

        out = []
        for item in resp.json():
            symbol = item["symbol"]
            base = strip_quote(symbol)
            if base is None:
                continue
            interval = intervals.get(symbol, 8)
            rate = float(item["lastFundingRate"])
            out.append({
                "exchange": self.name,
                "base": base,
                "funding_rate": rate,
                "funding_interval": interval,
                "rate_per_8h": normalize_to_8h(rate, interval),
                "mark_price": float(item["markPrice"]),
                "next_funding_time": int(item["nextFundingTime"]),
                "volume_24h_usd": volumes.get(symbol, 0.0),
            })
        return out
