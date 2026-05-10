import type {
  Meta, ScannerResponse, PositionsResponse, PairStatus,
  OpenPairRequest, ValidationResult, RiskResponse,
  BalancesResponse, PnlHistoryResponse, UpdateConfigRequest,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path}: ${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail ?? `${path}: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getMeta: () => get<Meta>("/api/meta"),
  setMode: (mode: "paper" | "live") => post<{ mode: string }>("/api/mode", { mode }),
  getScanner: () => get<ScannerResponse>("/api/scanner"),
  getPositions: () => get<PositionsResponse>("/api/positions"),
  validatePair: (req: OpenPairRequest) => post<ValidationResult>("/api/positions/validate", req),
  openPosition: (req: OpenPairRequest) => post<PairStatus>("/api/positions", req),
  closePosition: (id: string, short_price: number, long_price: number) =>
    post<PairStatus>(`/api/positions/${id}/close`, { short_price, long_price }),
  getRisk: () => get<RiskResponse>("/api/risk"),
  getBalances: () => get<BalancesResponse>("/api/balances"),
  applyFunding: () => post<{ payments: Record<string, number> }>("/api/funding/apply"),
  getPnlHistory: () => get<PnlHistoryResponse>("/api/pnl/history"),
  updateConfig: (body: UpdateConfigRequest) => post<{ ok: boolean }>("/api/config", body),
  resetPaperTrade: () => post<{ ok: boolean }>("/api/reset"),
  refreshScanner: () => post<ScannerResponse>("/api/scanner/refresh"),
  closeAllPositions: () => post<{ closed: number }>("/api/positions/close-all"),
};
