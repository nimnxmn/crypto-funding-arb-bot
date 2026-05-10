from abc import ABC, abstractmethod
import requests
from requests.adapters import HTTPAdapter


class BaseExchange(ABC):
    name: str = ""

    # If True, the scanner should pass `bases=...` to limit which instruments
    # are queried. OKX is expensive (one HTTP call per instrument).
    per_instrument: bool = False

    def __init__(self):
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=20)
        self.session.mount("https://", adapter)

    @abstractmethod
    def get_funding_rates(self, bases: list[str] | None = None) -> list[dict]:
        """
        Returns list of normalized dicts:
        {
            "exchange":          str,
            "base":              str,         # e.g. "BTC"
            "funding_rate":      float,       # raw rate (per funding period)
            "funding_interval":  int,         # period length in hours (8, 4, 1)
            "rate_per_8h":       float,       # rate normalized to 8h for fair comparison
            "mark_price":        float,
            "next_funding_time": int,         # unix ms, 0 if unknown
        }

        bases: optional list of base symbols (e.g. ["BTC", "ETH"]) to restrict
               the query. Cheap exchanges may ignore this; expensive ones honor it.
        """


def strip_quote(symbol: str, quotes=("USDT", "USDC", "BUSD")) -> str | None:
    for q in quotes:
        if symbol.endswith(q) and len(symbol) > len(q):
            return symbol[: -len(q)]
    return None


def normalize_to_8h(rate: float, interval_hours: int) -> float:
    """Convert a per-period funding rate to its per-8h equivalent."""
    if interval_hours <= 0:
        return rate
    return rate * (8 / interval_hours)
