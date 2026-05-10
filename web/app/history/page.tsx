"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { fmtUsd, fmtDateTime, fmtPct } from "@/lib/format";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { WsProvider } from "@/components/ws-provider";
import { ExchangeChip } from "@/components/scanner/exchange-chip";
import { Skeleton } from "@/components/ui/skeleton";
import { ClosedPositionDetail } from "@/components/positions/closed-position-detail";
import type { PairStatus } from "@/lib/types";

export default function HistoryPage() {
  const { data: positions, isLoading } = useQuery({
    queryKey: ["positions"],
    queryFn: api.getPositions,
  });

  const [detail, setDetail] = useState<PairStatus | null>(null);
  const closed = positions?.closed ?? [];

  const totalRealized = closed.reduce((s, p) => s + (p.net_pnl ?? 0), 0);
  const totalFunding = closed.reduce((s, p) => s + p.funding_collected, 0);
  const wins = closed.filter((p) => (p.net_pnl ?? 0) > 0).length;
  const winRate = closed.length > 0 ? (wins / closed.length) * 100 : 0;

  return (
    <WsProvider>
      <DashboardShell>
        <div className="p-4 space-y-4">
          <h1 className="text-sm font-semibold text-foreground">Trade History</h1>

          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Total Realized P&L", value: fmtUsd(totalRealized), color: totalRealized >= 0 ? "#0ECB81" : "#F6465D" },
              { label: "Total Funding", value: fmtUsd(totalFunding), color: totalFunding >= 0 ? "#0ECB81" : "#F6465D" },
              { label: "Closed Trades", value: String(closed.length), color: undefined },
              { label: "Win Rate", value: `${winRate.toFixed(0)}%`, color: winRate >= 50 ? "#0ECB81" : "#F6465D" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-surface rounded p-4 border border-subtle">
                <div className="text-xs text-muted uppercase tracking-wider mb-1">{label}</div>
                <div className="text-xl font-mono font-semibold" style={{ color: color ?? "var(--foreground)" }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          {/* Full history table */}
          <div className="bg-surface rounded border border-subtle overflow-hidden">
            <div className="px-4 py-2 border-b border-subtle">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                Closed Positions ({closed.length})
              </span>
            </div>

            {isLoading ? (
              <div className="p-4 space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-9 w-full bg-surface-2" />
                ))}
              </div>
            ) : (
              <div className="overflow-auto">
                <table className="w-full text-xs trade-table">
                  <thead>
                    <tr className="border-b border-subtle text-muted font-medium text-left">
                      <th className="px-3 py-2">ID</th>
                      <th className="px-3 py-2">BASE</th>
                      <th className="px-3 py-2">SHORT</th>
                      <th className="px-3 py-2">LONG</th>
                      <th className="px-3 py-2">COLLATERAL</th>
                      <th className="px-3 py-2">LVRG</th>
                      <th className="px-3 py-2">ENTRY SPREAD</th>
                      <th className="px-3 py-2">FEES</th>
                      <th className="px-3 py-2">FUNDING</th>
                      <th className="px-3 py-2">PRICE P&L</th>
                      <th className="px-3 py-2">NET P&L</th>
                      <th className="px-3 py-2">OPENED</th>
                      <th className="px-3 py-2">CLOSED</th>
                      <th className="px-3 py-2">REASON</th>
                    </tr>
                  </thead>
                  <tbody>
                    {closed.length === 0 && (
                      <tr>
                        <td colSpan={14} className="px-3 py-8 text-center text-muted">
                          No closed trades yet.
                        </td>
                      </tr>
                    )}
                    {closed.map((p) => {
                      const netPnl = p.net_pnl ?? 0;
                      const pricePnl = p.price_pnl ?? 0;
                      const entrySpread = p.short_rate_at_open - p.long_rate_at_open;
                      return (
                        <tr
                          key={p.pair_id}
                          className="border-b border-subtle row-hover cursor-pointer"
                          onClick={() => setDetail(p)}
                        >
                          <td className="px-3 py-2 font-mono text-muted">{p.pair_id}</td>
                          <td className="px-3 py-2 font-semibold">{p.base}</td>
                          <td className="px-3 py-2"><ExchangeChip name={p.short_exchange} /></td>
                          <td className="px-3 py-2"><ExchangeChip name={p.long_exchange} /></td>
                          <td className="px-3 py-2 font-mono">
                            ${(p.size_usd / p.leverage * 2).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </td>
                          <td className="px-3 py-2 font-mono font-semibold">
                            <span className={p.leverage > 1 ? "text-yellow" : "text-muted"}>{p.leverage}x</span>
                          </td>
                          <td className={`px-3 py-2 font-mono ${entrySpread > 0 ? "text-green" : "text-muted"}`}>
                            {fmtPct(entrySpread)}
                          </td>
                          <td className="px-3 py-2 font-mono text-red">{fmtUsd(-p.fees_paid)}</td>
                          <td className={`px-3 py-2 font-mono ${p.funding_collected >= 0 ? "text-green" : "text-red"}`}>
                            {fmtUsd(p.funding_collected)}
                          </td>
                          <td className={`px-3 py-2 font-mono ${pricePnl >= 0 ? "text-green" : "text-red"}`}>
                            {fmtUsd(pricePnl)}
                          </td>
                          <td className={`px-3 py-2 font-mono font-semibold ${netPnl >= 0 ? "text-green" : "text-red"}`}>
                            {fmtUsd(netPnl)}
                          </td>
                          <td className="px-3 py-2 text-muted">{fmtDateTime(p.opened_at)}</td>
                          <td className="px-3 py-2 text-muted">{p.closed_at ? fmtDateTime(p.closed_at) : "—"}</td>
                          <td className="px-3 py-2">
                            {p.close_reason === "stop_loss" ? (
                              <span className="px-1.5 py-0.5 rounded text-xs font-semibold bg-red/20 text-red">Stop-Loss</span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-xs font-semibold bg-surface-2 text-muted">Manual</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </DashboardShell>

      <ClosedPositionDetail pair={detail} onClose={() => setDetail(null)} />
    </WsProvider>
  );
}
