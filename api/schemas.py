from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class MetaResponse(BaseModel):
    mode: Literal["paper", "live"]
    total_capital: float
    max_position_pct: float
    stop_loss_pct: float
    drift_warning_pct: float
    drift_critical_pct: float
    round_trip_fee: float
    min_spread_multiplier: float
    min_24h_volume_usd: float
    top_n: int
    leverage: int


class Opportunity(BaseModel):
    base: str
    spread: float
    annual_spread: float
    annual_capital_yield: float
    short_exchange: str
    short_rate: float
    short_raw_rate: float
    short_interval: int
    short_price: float
    short_volume_24h: float
    short_next_funding: int
    long_exchange: str
    long_rate: float
    long_raw_rate: float
    long_interval: int
    long_price: float
    long_volume_24h: float
    long_next_funding: int


class ScannerResponse(BaseModel):
    opportunities: list[Opportunity]
    scanned_at: str


class PairStatus(BaseModel):
    pair_id: str
    base: str
    status: Literal["open", "closed"]
    short_exchange: str
    long_exchange: str
    size_usd: float
    leverage: int
    short_entry_price: float
    long_entry_price: float
    short_rate_at_open: float
    long_rate_at_open: float
    fees_paid: float
    funding_collected: float
    opened_at: str
    closed_at: str | None
    short_exit_price: float | None
    long_exit_price: float | None
    liq_price_short: float | None
    liq_price_long: float | None
    close_reason: str | None
    # live-computed fields (None for closed pairs without mark prices)
    price_pnl: float | None
    net_pnl: float | None


class PositionsResponse(BaseModel):
    open: list[PairStatus]
    closed: list[PairStatus]


class OpenPairRequest(BaseModel):
    base: str
    size_usd: float
    leverage: int = 1
    short_exchange: str
    short_price: float
    short_rate: float
    long_exchange: str
    long_price: float
    long_rate: float


class ClosePairRequest(BaseModel):
    short_price: float
    long_price: float


class ValidationResult(BaseModel):
    ok: bool
    message: str


class RiskResult(BaseModel):
    pair_id: str
    base: str
    level: Literal["ok", "drift_warning", "drift_critical", "stop_loss"]
    drift_pct: float
    price_pnl: float
    net_pnl: float
    stop_loss_threshold: float
    alerts: list[str]


class RiskResponse(BaseModel):
    results: list[RiskResult]


class BalanceEntry(BaseModel):
    exchange: str
    balance_usdt: float


class BalancesResponse(BaseModel):
    balances: list[BalanceEntry]


class FundingApplyResponse(BaseModel):
    payments: dict[str, float]


class PnlPoint(BaseModel):
    timestamp: str
    cumulative_pnl: float
    event_type: str
    pair_id: str
    amount_usd: float


class PnlHistoryResponse(BaseModel):
    points: list[PnlPoint]


class WsEnvelope(BaseModel):
    type: Literal["scanner", "positions", "risk", "balances"]
    data: dict
