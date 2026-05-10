from exchange.base import BaseExchange, strip_quote, normalize_to_8h

BASE_URL = "https://api.bybit.com"


class Bybit(BaseExchange):
    name = "Bybit"
    per_instrument = False

    def get_funding_rates(self, bases: list[str] | None = None) -> list[dict]:
        resp = self.session.get(
            f"{BASE_URL}/v5/market/tickers",
            params={"category": "linear"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("result", {}).get("list", [])

        out = []
        for item in items:
            base = strip_quote(item.get("symbol", ""))
            if base is None:
                continue
            rate = item.get("fundingRate")
            if rate is None or rate == "":
                continue
            interval = int(item.get("fundingIntervalHour") or 8)
            rate = float(rate)
            out.append({
                "exchange": self.name,
                "base": base,
                "funding_rate": rate,
                "funding_interval": interval,
                "rate_per_8h": normalize_to_8h(rate, interval),
                "mark_price": float(item.get("markPrice") or 0),
                "next_funding_time": int(item.get("nextFundingTime") or 0),
                # Bybit's `turnover24h` is already in USDT for linear pairs
                "volume_24h_usd": float(item.get("turnover24h") or 0),
            })
        return out
