export interface Meta {
  mode: "paper" | "live";
  total_capital: number;
  max_position_pct: number;
  stop_loss_pct: number;
  drift_warning_pct: number;
  drift_critical_pct: number;
  round_trip_fee: number;
  min_spread_multiplier: number;
  min_24h_volume_usd: number;
  top_n: number;
  leverage: number;
}

export interface Opportunity {
  base: string;
  spread: number;
  annual_spread: number;
  annual_capital_yield: number;
  short_exchange: string;
  short_rate: number;
  short_raw_rate: number;
  short_interval: number;
  short_price: number;
  short_volume_24h: number;
  short_next_funding: number;
  long_exchange: string;
  long_rate: number;
  long_raw_rate: number;
  long_interval: number;
  long_price: number;
  long_volume_24h: number;
  long_next_funding: number;
}

export interface ScannerResponse {
  opportunities: Opportunity[];
  scanned_at: string;
}

export interface PairStatus {
  pair_id: string;
  base: string;
  status: "open" | "closed";
  short_exchange: string;
  long_exchange: string;
  size_usd: number;
  leverage: number;
  short_entry_price: number;
  long_entry_price: number;
  short_rate_at_open: number;
  long_rate_at_open: number;
  fees_paid: number;
  funding_collected: number;
  opened_at: string;
  closed_at: string | null;
  short_exit_price: number | null;
  long_exit_price: number | null;
  liq_price_short: number | null;
  liq_price_long: number | null;
  close_reason: string | null;
  price_pnl: number | null;
  net_pnl: number | null;
}

export interface PositionsResponse {
  open: PairStatus[];
  closed: PairStatus[];
}

export interface OpenPairRequest {
  base: string;
  size_usd: number;
  leverage: number;
  short_exchange: string;
  short_price: number;
  short_rate: number;
  long_exchange: string;
  long_price: number;
  long_rate: number;
}

export interface ValidationResult {
  ok: boolean;
  message: string;
}

export type RiskLevel = "ok" | "drift_warning" | "drift_critical" | "stop_loss";

export interface RiskResult {
  pair_id: string;
  base: string;
  level: RiskLevel;
  drift_pct: number;
  price_pnl: number;
  net_pnl: number;
  stop_loss_threshold: number;
  alerts: string[];
}

export interface RiskResponse {
  results: RiskResult[];
}

export interface BalanceEntry {
  exchange: string;
  balance_usdt: number;
}

export interface BalancesResponse {
  balances: BalanceEntry[];
}

export interface PnlPoint {
  timestamp: string;
  cumulative_pnl: number;
  event_type: string;
  pair_id: string;
  amount_usd: number;
}

export interface PnlHistoryResponse {
  points: PnlPoint[];
}

export interface UpdateConfigRequest {
  total_capital?: number;
  max_position_pct?: number;
  stop_loss_pct?: number;
  drift_warning_pct?: number;
  drift_critical_pct?: number;
  min_spread_multiplier?: number;
  min_24h_volume_usd?: number;
  leverage?: number;
}

export type WsMessage =
  | { type: "scanner"; data: ScannerResponse }
  | { type: "positions"; data: PositionsResponse }
  | { type: "risk"; data: RiskResponse }
  | { type: "balances"; data: BalancesResponse }
  | { type: "notification"; data: { level: string; message: string } };
