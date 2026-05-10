"use client";
import type { PairStatus } from "@/lib/types";
import { fmtUsd, fmtDateTime, fmtPct } from "@/lib/format";
import { ExchangeChip } from "@/components/scanner/exchange-chip";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface Props {
  pair: PairStatus | null;
  onClose: () => void;
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

export function ClosedPositionDetail({ pair: p, onClose }: Props) {
  if (!p) return null;

  const netPnl = p.net_pnl ?? 0;
  const pricePnl = p.price_pnl ?? 0;
  const entrySpread = p.short_rate_at_open - p.long_rate_at_open;
  const collateralPerLeg = p.size_usd / p.leverage;
  const totalCollateral = collateralPerLeg * 2;

  const duration = p.closed_at && p.opened_at
    ? (() => {
        const ms = new Date(p.closed_at).getTime() - new Date(p.opened_at).getTime();
        const h = Math.floor(ms / 3_600_000);
        const m = Math.floor((ms % 3_600_000) / 60_000);
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
      })()
    : "—";

  return (
    <Dialog open={!!p} onOpenChange={onClose}>
      <DialogContent className="bg-surface border-subtle max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-sm flex items-center gap-2">
            <span className="text-yellow font-bold">{p.base}</span>
            <span className="font-mono text-muted text-xs">{p.pair_id}</span>
            {p.leverage > 1 && (
              <span className="px-1.5 py-0.5 rounded bg-yellow/10 text-yellow text-xs font-semibold">
                {p.leverage}x
              </span>
            )}
            {p.close_reason === "stop_loss" ? (
              <span className="ml-auto px-1.5 py-0.5 rounded bg-red/20 text-red text-xs font-semibold">STOP-LOSS</span>
            ) : (
              <span className="ml-auto px-1.5 py-0.5 rounded bg-surface-2 text-muted text-xs">CLOSED</span>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 text-xs">
          <Section title="Position">
            <DetailRow label="Short on" value={<ExchangeChip name={p.short_exchange} />} />
            <DetailRow label="Long on" value={<ExchangeChip name={p.long_exchange} />} />
            <DetailRow label="Notional per leg" value={`$${p.size_usd.toLocaleString()}`} />
            <DetailRow label="Leverage" value={`${p.leverage}x`} valueClass={p.leverage > 1 ? "text-yellow" : undefined} />
            <DetailRow label="Collateral per leg" value={`$${collateralPerLeg.toLocaleString(undefined, { maximumFractionDigits: 2 })}`} />
            <DetailRow label="Total collateral" value={`$${totalCollateral.toLocaleString(undefined, { maximumFractionDigits: 2 })}`} />
            <DetailRow label="Duration" value={duration} />
            <DetailRow label="Opened" value={fmtDateTime(p.opened_at)} />
            <DetailRow label="Closed" value={p.closed_at ? fmtDateTime(p.closed_at) : "—"} />
            <DetailRow
              label="Close reason"
              value={p.close_reason === "stop_loss" ? "Stop-Loss (auto)" : "Manual"}
              valueClass={p.close_reason === "stop_loss" ? "text-red" : "text-muted"}
            />
          </Section>

          <Section title="Entry">
            <DetailRow label="Short entry price" value={`$${p.short_entry_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}`} />
            <DetailRow label="Long entry price" value={`$${p.long_entry_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}`} />
            <DetailRow label="Short rate at open" value={fmtPct(p.short_rate_at_open, 4)} valueClass="text-green" />
            <DetailRow label="Long rate at open" value={fmtPct(p.long_rate_at_open, 4)} />
            <DetailRow label="Spread at open" value={fmtPct(entrySpread, 4)} valueClass="text-green" />
          </Section>

          <Section title="Exit">
            <DetailRow
              label="Short exit price"
              value={p.short_exit_price ? `$${p.short_exit_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}` : "—"}
            />
            <DetailRow
              label="Long exit price"
              value={p.long_exit_price ? `$${p.long_exit_price.toLocaleString(undefined, { maximumFractionDigits: 4 })}` : "—"}
            />
          </Section>

          <Section title="P&L Breakdown">
            <DetailRow label="Funding collected" value={fmtUsd(p.funding_collected)} valueClass={p.funding_collected >= 0 ? "text-green" : "text-red"} />
            <DetailRow label="Fees paid" value={fmtUsd(-p.fees_paid)} valueClass="text-red" />
            <DetailRow label="Price P&L" value={fmtUsd(pricePnl)} valueClass={pricePnl >= 0 ? "text-green" : "text-red"} />
            <DetailRow
              label="Net P&L"
              value={fmtUsd(netPnl)}
              valueClass={`font-semibold ${netPnl >= 0 ? "text-green" : "text-red"}`}
            />
          </Section>
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
