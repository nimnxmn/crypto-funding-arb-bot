"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { PairStatus, RiskResult } from "@/lib/types";
import { fmtUsd, fmtDateTime, fmtPct } from "@/lib/format";
import { RiskBadge } from "./risk-badge";
import { ExchangeChip } from "@/components/scanner/exchange-chip";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface Props {
  pairs: PairStatus[];
  riskMap: Record<string, RiskResult>;
  isLoading?: boolean;
}

function DetailRow({ label, value, valueClass }: { label: string; value: React.ReactNode; valueClass?: string }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-subtle last:border-0">
      <span className="text-muted text-xs">{label}</span>
      <span className={`text-xs font-mono ${valueClass ?? "text-foreground"}`}>{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0">
      <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-1">{title}</p>
      <div className="bg-surface-2 rounded px-3">{children}</div>
    </div>
  );
}

export function PositionsTable({ pairs, riskMap, isLoading }: Props) {
  const qc = useQueryClient();
  const [detail, setDetail] = useState<PairStatus | null>(null);
  const [closing, setClosing] = useState<PairStatus | null>(null);

  const closeMutation = useMutation({
    mutationFn: (pair: PairStatus) =>
      api.closePosition(pair.pair_id, pair.short_entry_price, pair.long_entry_price),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["pnl"] });
      toast.success(`Closed ${result.base} — net P&L ${fmtUsd(result.net_pnl ?? 0)}`);
      setClosing(null);
      setDetail(null);
    },
    onError: (e: Error) => {
      toast.error(`Close failed: ${e.message}`);
    },
  });

  if (isLoading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-full bg-surface-2" />
        ))}
      </div>
    );
  }

  if (pairs.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-muted text-xs">
        No open positions — click a scanner row to open a trade.
      </div>
    );
  }

  const detailRisk = detail ? riskMap[detail.pair_id] : null;

  return (
    <>
      <div className="overflow-auto">
        <table className="w-full text-xs trade-table">
          <thead>
            <tr className="border-b border-subtle text-left text-muted font-medium">
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">BASE</th>
              <th className="px-3 py-2">SHORT</th>
              <th className="px-3 py-2">LONG</th>
              <th className="px-3 py-2">COLLATERAL</th>
              <th className="px-3 py-2">LVRG</th>
              <th className="px-3 py-2">FUNDING</th>
              <th className="px-3 py-2">NET P&L</th>
              <th className="px-3 py-2">DRIFT</th>
              <th className="px-3 py-2">RISK</th>
              <th className="px-3 py-2">OPENED</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {pairs.map((p) => {
                const risk = riskMap[p.pair_id];
                const netPnl = p.net_pnl ?? 0;
                return (
                  <motion.tr
                    key={p.pair_id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 8 }}
                    transition={{ duration: 0.18 }}
                    className="border-b border-subtle row-hover cursor-pointer"
                    onClick={() => setDetail(p)}
                  >
                    <td className="px-3 py-2 font-mono text-muted">{p.pair_id}</td>
                    <td className="px-3 py-2 font-semibold">{p.base}</td>
                    <td className="px-3 py-2"><ExchangeChip name={p.short_exchange} /></td>
                    <td className="px-3 py-2"><ExchangeChip name={p.long_exchange} /></td>
                    <td className="px-3 py-2 font-mono">${(p.size_usd / p.leverage * 2).toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td className="px-3 py-2 font-mono font-semibold">
                      <span className={p.leverage > 1 ? "text-yellow" : "text-muted"}>
                        {p.leverage}x
                      </span>
                    </td>
                    <td className={`px-3 py-2 font-mono ${p.funding_collected >= 0 ? "text-green" : "text-red"}`}>
                      {fmtUsd(p.funding_collected)}
                    </td>
                    <td className={`px-3 py-2 font-mono font-semibold ${netPnl >= 0 ? "text-green" : "text-red"}`}>
                      {fmtUsd(netPnl)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {risk ? (
                        <span className={
                          risk.drift_pct >= 0.01 ? "text-red" :
                          risk.drift_pct >= 0.003 ? "text-yellow" : "text-green"
                        }>
                          {(risk.drift_pct * 100).toFixed(3)}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {risk ? <RiskBadge level={risk.level} /> : "—"}
                    </td>
                    <td className="px-3 py-2 text-muted">{fmtDateTime(p.opened_at)}</td>
                    <td className="px-3 py-2">
                      <button
                        className="text-xs text-red hover:opacity-80 font-medium"
                        onClick={(e) => { e.stopPropagation(); setClosing(p); }}
                      >
                        Close
                      </button>
                    </td>
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      {/* Position Detail Dialog */}
      <Dialog open={!!detail} onOpenChange={() => setDetail(null)}>
        <DialogContent className="bg-surface border-subtle max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-sm flex items-center gap-2">
              <span className="text-yellow font-bold">{detail?.base}</span>
              <span className="font-mono text-muted text-xs">{detail?.pair_id}</span>
              {detail && detail.leverage > 1 && (
                <span className="px-1.5 py-0.5 rounded bg-yellow/10 text-yellow text-xs font-semibold">
                  {detail.leverage}x
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          {detail && (
            <div className="space-y-4 text-xs">

              <Section title="Position">
                <DetailRow label="Short on" value={<ExchangeChip name={detail.short_exchange} />} />
                <DetailRow label="Long on" value={<ExchangeChip name={detail.long_exchange} />} />
                <DetailRow label="Notional per leg" value={`$${detail.size_usd.toLocaleString()}`} />
                <DetailRow label="Leverage" value={`${detail.leverage}x`} valueClass={detail.leverage > 1 ? "text-yellow" : undefined} />
                <DetailRow
                  label="Collateral per leg"
                  value={`$${(detail.size_usd / detail.leverage).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
                />
                <DetailRow
                  label="Total collateral locked"
                  value={`$${(detail.size_usd / detail.leverage * 2).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
                />
                <DetailRow label="Opened" value={fmtDateTime(detail.opened_at)} />
              </Section>

              <Section title="Entry Prices & Rates">
                <DetailRow label="Short entry price" value={`$${detail.short_entry_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}`} />
                <DetailRow label="Long entry price" value={`$${detail.long_entry_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}`} />
                <DetailRow label="Short rate at open" value={fmtPct(detail.short_rate_at_open, 4)} valueClass="text-green" />
                <DetailRow label="Long rate at open" value={fmtPct(detail.long_rate_at_open, 4)} />
                <DetailRow
                  label="Spread at open"
                  value={fmtPct(detail.short_rate_at_open - detail.long_rate_at_open, 4)}
                  valueClass="text-green"
                />
              </Section>

              <Section title="P&L Breakdown">
                <DetailRow label="Funding collected" value={fmtUsd(detail.funding_collected)} valueClass={detail.funding_collected >= 0 ? "text-green" : "text-red"} />
                <DetailRow label="Fees paid" value={fmtUsd(-detail.fees_paid)} valueClass="text-red" />
                <DetailRow label="Price P&L" value={fmtUsd(detail.price_pnl ?? 0)} valueClass={(detail.price_pnl ?? 0) >= 0 ? "text-green" : "text-red"} />
                <DetailRow
                  label="Net P&L"
                  value={fmtUsd(detail.net_pnl ?? 0)}
                  valueClass={`font-semibold ${(detail.net_pnl ?? 0) >= 0 ? "text-green" : "text-red"}`}
                />
              </Section>

              {detailRisk && (
                <Section title="Risk">
                  <DetailRow label="Status" value={<RiskBadge level={detailRisk.level} />} />
                  <DetailRow
                    label="Price drift"
                    value={`${(detailRisk.drift_pct * 100).toFixed(3)}%`}
                    valueClass={detailRisk.drift_pct >= 0.01 ? "text-red" : detailRisk.drift_pct >= 0.003 ? "text-yellow" : "text-green"}
                  />
                  <DetailRow label="Stop-loss threshold" value={fmtUsd(detailRisk.stop_loss_threshold)} valueClass="text-red" />
                  {detailRisk.alerts.map((a, i) => (
                    <div key={i} className="py-1.5 text-yellow border-b border-subtle last:border-0">{a}</div>
                  ))}
                </Section>
              )}

              {detail.leverage > 1 && (
                <Section title="Liquidation Prices (approx)">
                  <DetailRow
                    label={`Short liq (${detail.short_exchange})`}
                    value={`$${detail.liq_price_short?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"}`}
                    valueClass="text-yellow"
                  />
                  <DetailRow
                    label={`Long liq (${detail.long_exchange})`}
                    value={`$${detail.liq_price_long?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"}`}
                    valueClass="text-yellow"
                  />
                </Section>
              )}
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setDetail(null)}>Close Dialog</Button>
            <Button
              variant="destructive"
              onClick={() => { setClosing(detail); setDetail(null); }}
            >
              Close Position
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Close Dialog */}
      <Dialog open={!!closing} onOpenChange={() => setClosing(null)}>
        <DialogContent className="bg-surface border-subtle">
          <DialogHeader>
            <DialogTitle>Close Position</DialogTitle>
          </DialogHeader>
          {closing && (
            <div className="text-sm space-y-2">
              <p>
                Close <strong>{closing.base}</strong> arb pair{" "}
                <span className="font-mono text-muted">{closing.pair_id}</span>?
              </p>
              <p className="text-muted text-xs">
                Short {closing.short_exchange} / Long {closing.long_exchange} —{" "}
                ${closing.size_usd.toLocaleString()} notional · {closing.leverage}x leverage
              </p>
              {closing.leverage > 1 && (
                <div className="bg-surface-2 rounded p-2 text-xs space-y-1">
                  <p className="text-muted font-medium">Approximate liquidation prices</p>
                  <div className="flex justify-between">
                    <span className="text-muted">Short liq ({closing.short_exchange})</span>
                    <span className="font-mono text-yellow">
                      ${closing.liq_price_short?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Long liq ({closing.long_exchange})</span>
                    <span className="font-mono text-yellow">
                      ${closing.liq_price_long?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setClosing(null)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={closeMutation.isPending}
              onClick={() => closing && closeMutation.mutate(closing)}
            >
              {closeMutation.isPending ? "Closing…" : "Confirm Close"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
