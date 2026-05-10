import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import TAKER_FEE

LOG_PATH = Path(__file__).parent.parent / "data" / "trades_log.csv"

FIELDNAMES = [
    "event_id", "event_type", "pair_id", "timestamp",
    "base", "short_exchange", "long_exchange",
    "short_price", "long_price", "size_usd",
    "short_rate", "long_rate", "amount_usd", "leverage", "close_reason", "notes",
]


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _ensure_log():
    LOG_PATH.parent.mkdir(exist_ok=True)
    if not LOG_PATH.exists():
        with open(LOG_PATH, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


def _append_row(row: dict):
    _ensure_log()
    with open(LOG_PATH, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(row)


def _load_rows() -> list[dict]:
    _ensure_log()
    with open(LOG_PATH, newline="") as f:
        return list(csv.DictReader(f))


class ArbPair:
    """
    One delta-neutral arb position: short on high-rate exchange, long on low-rate exchange.

    size_usd = notional per leg (not collateral).
    collateral per leg = size_usd / leverage.
    Profit comes from the funding rate spread; price P&L cancels across legs.
    """
    def __init__(self, pair_id, base, size_usd,
                 short_exchange, short_price, short_rate,
                 long_exchange, long_price, long_rate,
                 opened_at, leverage=1):
        self.pair_id = pair_id
        self.base = base
        self.size_usd = float(size_usd)
        self.leverage = int(leverage)
        self.short_exchange = short_exchange
        self.short_entry_price = float(short_price)
        self.long_exchange = long_exchange
        self.long_entry_price = float(long_price)
        self.short_rate_at_open = float(short_rate)
        self.long_rate_at_open = float(long_rate)
        self.opened_at = opened_at
        self.status = "open"

        # 4 fills: open short, open long, close short, close long (on notional)
        self.fees_paid = self.size_usd * TAKER_FEE * 4
        self.funding_collected = 0.0

        self.short_exit_price = None
        self.long_exit_price = None
        self.closed_at = None
        self.close_reason: str | None = None

    @property
    def collateral_usd(self) -> float:
        """Total capital deployed across both legs."""
        return self.size_usd / self.leverage * 2

    def price_pnl(self, short_price: float, long_price: float) -> float:
        short_qty = self.size_usd / self.short_entry_price
        long_qty = self.size_usd / self.long_entry_price
        short_pnl = (self.short_entry_price - short_price) * short_qty
        long_pnl = (long_price - self.long_entry_price) * long_qty
        return short_pnl + long_pnl

    def net_pnl(self, short_price: float, long_price: float) -> float:
        return self.price_pnl(short_price, long_price) + self.funding_collected - self.fees_paid

    def apply_funding(self, short_price: float, short_rate: float,
                      long_price: float, long_rate: float) -> float:
        short_qty = self.size_usd / self.short_entry_price
        long_qty = self.size_usd / self.long_entry_price
        short_payment = short_qty * short_price * short_rate
        long_payment = long_qty * long_price * long_rate
        payment = short_payment - long_payment
        self.funding_collected += payment
        return payment

    def close(self, short_price: float, long_price: float, reason: str = "manual") -> float:
        self.short_exit_price = short_price
        self.long_exit_price = long_price
        self.closed_at = _now_iso()
        self.status = "closed"
        self.close_reason = reason
        return self.net_pnl(short_price, long_price)

    def liq_price_short(self) -> float:
        """Approximate liquidation price for the short leg (1% maintenance margin)."""
        return self.short_entry_price * (1 + 1.0 / self.leverage - 0.01)

    def liq_price_long(self) -> float:
        """Approximate liquidation price for the long leg (1% maintenance margin)."""
        return self.long_entry_price * (1 - 1.0 / self.leverage + 0.01)


class PaperTradeSimulator:
    def __init__(self):
        self.pairs: dict[str, ArbPair] = {}
        self._load()

    def _load(self):
        for row in _load_rows():
            pid = row["pair_id"]
            etype = row["event_type"]

            if etype == "open":
                pair = ArbPair(
                    pair_id=pid,
                    base=row["base"],
                    size_usd=row["size_usd"],
                    short_exchange=row["short_exchange"],
                    short_price=row["short_price"],
                    short_rate=row["short_rate"],
                    long_exchange=row["long_exchange"],
                    long_price=row["long_price"],
                    long_rate=row["long_rate"],
                    opened_at=row["timestamp"],
                    leverage=int(row.get("leverage") or 1),
                )
                pair.fees_paid = float(row["amount_usd"])
                self.pairs[pid] = pair

            elif etype == "funding" and pid in self.pairs:
                self.pairs[pid].funding_collected += float(row["amount_usd"])

            elif etype == "close" and pid in self.pairs:
                p = self.pairs[pid]
                p.status = "closed"
                p.short_exit_price = float(row["short_price"])
                p.long_exit_price = float(row["long_price"])
                p.closed_at = row["timestamp"]
                p.close_reason = row.get("close_reason") or "manual"

    def open_pair(self, base: str, size_usd: float,
                  short_exchange: str, short_price: float, short_rate: float,
                  long_exchange: str, long_price: float, long_rate: float,
                  leverage: int = 1) -> ArbPair:
        pid = str(uuid.uuid4())[:8]
        pair = ArbPair(pid, base, size_usd,
                       short_exchange, short_price, short_rate,
                       long_exchange, long_price, long_rate,
                       _now_iso(), leverage=leverage)
        self.pairs[pid] = pair

        _append_row({
            "event_id": str(uuid.uuid4())[:8],
            "event_type": "open",
            "pair_id": pid,
            "timestamp": _now_iso(),
            "base": base,
            "short_exchange": short_exchange,
            "long_exchange": long_exchange,
            "short_price": short_price,
            "long_price": long_price,
            "size_usd": size_usd,
            "short_rate": short_rate,
            "long_rate": long_rate,
            "amount_usd": round(pair.fees_paid, 6),
            "leverage": leverage,
            "notes": f"open fees ({TAKER_FEE*100:.3f}% x4 legs) {leverage}x",
        })
        return pair

    def apply_funding(self, live_data: dict[str, dict[str, dict]]) -> dict[str, float]:
        payments = {}
        for pid, pair in self.pairs.items():
            if pair.status != "open":
                continue
            base_data = live_data.get(pair.base, {})
            short_data = base_data.get(pair.short_exchange)
            long_data = base_data.get(pair.long_exchange)
            if not short_data or not long_data:
                continue

            short_rate = short_data["funding_rate"]
            long_rate = long_data["funding_rate"]
            short_price = short_data["mark_price"]
            long_price = long_data["mark_price"]

            payment = pair.apply_funding(short_price, short_rate, long_price, long_rate)
            payments[pid] = payment

            _append_row({
                "event_id": str(uuid.uuid4())[:8],
                "event_type": "funding",
                "pair_id": pid,
                "timestamp": _now_iso(),
                "base": pair.base,
                "short_exchange": pair.short_exchange,
                "long_exchange": pair.long_exchange,
                "short_price": short_price,
                "long_price": long_price,
                "size_usd": pair.size_usd,
                "short_rate": short_rate,
                "long_rate": long_rate,
                "amount_usd": round(payment, 6),
                "leverage": pair.leverage,
                "notes": f"spread={( short_rate - long_rate)*100:+.4f}%",
            })
        return payments

    def close_pair(self, pair_id: str, short_price: float, long_price: float,
                   reason: str = "manual") -> float:
        pair = self.pairs[pair_id]
        realized = pair.close(short_price, long_price, reason=reason)

        _append_row({
            "event_id": str(uuid.uuid4())[:8],
            "event_type": "close",
            "pair_id": pair_id,
            "timestamp": pair.closed_at,
            "base": pair.base,
            "short_exchange": pair.short_exchange,
            "long_exchange": pair.long_exchange,
            "short_price": short_price,
            "long_price": long_price,
            "size_usd": pair.size_usd,
            "short_rate": "",
            "long_rate": "",
            "amount_usd": round(realized, 6),
            "leverage": pair.leverage,
            "close_reason": reason,
            "notes": "realized pnl",
        })
        return realized

    def open_pairs(self) -> list[ArbPair]:
        return [p for p in self.pairs.values() if p.status == "open"]

    def closed_pairs(self) -> list[ArbPair]:
        return [p for p in self.pairs.values() if p.status == "closed"]
