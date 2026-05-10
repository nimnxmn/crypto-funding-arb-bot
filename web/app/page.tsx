"use client";
import { useCallback, useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { fmtUsd } from "@/lib/format";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { KpiCard } from "@/components/kpi/kpi-card";
import { ScannerTable } from "@/components/scanner/scanner-table";
import { PositionsTable } from "@/components/positions/positions-table";
import { ClosedPositionDetail } from "@/components/positions/closed-position-detail";
import { OpenPairModal } from "@/components/trade/open-pair-modal";
import { PnlChart } from "@/components/chart/pnl-chart";
import { WsProvider } from "@/components/ws-provider";
import { ShortcutHelp } from "@/components/mode/shortcut-help";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useKeyboardShortcuts } from "@/lib/use-keyboard-shortcuts";
import { useUiStore } from "@/stores/ui-store";
import type { Opportunity, RiskResult, PairStatus } from "@/lib/types";

function useScannedAgo(scannedAt: string | undefined): string {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 10_000);
    return () => clearInterval(id);
  }, []);
  if (!scannedAt) return "";
  const secs = Math.floor((Date.now() - new Date(scannedAt).getTime()) / 1000);
  if (secs < 60) return `${secs}s ago`;
  return `${Math.floor(secs / 60)}m ago`;
}

export default function DashboardPage() {
  const qc = useQueryClient();
  const { setSelectedOpp, setShortcutHelpOpen, shortcutHelpOpen } = useUiStore();
  const [historyDetail, setHistoryDetail] = useState<PairStatus | null>(null);
  const [confirmCloseAll, setConfirmCloseAll] = useState(false);

  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: api.getMeta });
  const { data: scanner, isLoading: scanLoading } = useQuery({ queryKey: ["scanner"], queryFn: api.getScanner, refetchInterval: 60_000 });
  const { data: positions, isLoading: posLoading } = useQuery({ queryKey: ["positions"], queryFn: api.getPositions });
  const { data: risk } = useQuery({ queryKey: ["risk"], queryFn: api.getRisk });
  const { data: pnl } = useQuery({ queryKey: ["pnl"], queryFn: api.getPnlHistory });

  const applyFunding = useMutation({
    mutationFn: api.applyFunding,
    onSuccess: (res) => {
      const total = Object.values(res.payments).reduce((a, b) => a + b, 0);
      toast.success(`Funding applied — net ${fmtUsd(total)}`);
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["pnl"] });
    },
    onError: (e: Error) => toast.error(`Funding failed: ${e.message}`),
  });

  const refreshScanner = useMutation({
    mutationFn: api.refreshScanner,
    onSuccess: (data) => {
      qc.setQueryData(["scanner"], data);
      toast.success("Scanner refreshed");
    },
    onError: (e: Error) => toast.error(`Refresh failed: ${e.message}`),
  });

  const closeAll = useMutation({
    mutationFn: api.closeAllPositions,
    onSuccess: (res) => {
      setConfirmCloseAll(false);
      toast.success(`Closed ${res.closed} position(s)`);
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["pnl"] });
    },
    onError: (e: Error) => {
      setConfirmCloseAll(false);
      toast.error(`Close all failed: ${e.message}`);
    },
  });

  const openPairs = positions?.open ?? [];
  const closedPairs = positions?.closed ?? [];
  const riskResults = risk?.results ?? [];
  const pnlPoints = pnl?.points ?? [];
  const opportunities = scanner?.opportunities ?? [];

  const scannedAgo = useScannedAgo(scanner?.scanned_at);
  const totalCapital = meta?.total_capital ?? 10000;
  const deployedCapital = openPairs.reduce((s, p) => s + p.size_usd / p.leverage * 2, 0);
  const totalNetPnl = openPairs.reduce((s, p) => s + (p.net_pnl ?? 0), 0);
  const totalFundingCollected = openPairs.reduce((s, p) => s + p.funding_collected, 0);
  const totalFunding24h = pnlPoints
    .filter((p) => {
      const age = Date.now() - new Date(p.timestamp).getTime();
      return p.event_type === "funding" && age < 86_400_000;
    })
    .reduce((s, p) => s + p.amount_usd, 0);

  const riskMap: Record<string, RiskResult> = {};
  riskResults.forEach((r) => { riskMap[r.pair_id] = r; });
  const alertCount = riskResults.filter((r) => r.level !== "ok").length;

  const handleOpenTrade = useCallback((opp: Opportunity) => setSelectedOpp(opp), [setSelectedOpp]);
  const handleToggleHelp = useCallback(() => setShortcutHelpOpen(!shortcutHelpOpen), [setShortcutHelpOpen, shortcutHelpOpen]);

  useKeyboardShortcuts({ opportunities, onOpenTrade: handleOpenTrade, onToggleHelp: handleToggleHelp });

  return (
    <WsProvider>
      <DashboardShell>
        <div className="p-4 space-y-4">
          {/* KPI strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard
              label="Net P&L"
              value={fmtUsd(totalNetPnl)}
              color={totalNetPnl >= 0 ? "#0ECB81" : "#F6465D"}
            />
            <KpiCard
              label="Funding (Open)"
              value={fmtUsd(totalFundingCollected)}
              sub={`cumulative · ${openPairs.length} open pos`}
              color={totalFundingCollected >= 0 ? "#0ECB81" : "#F6465D"}
            />
            <KpiCard
              label="Funding (24h)"
              value={fmtUsd(totalFunding24h)}
              sub="all settlements last 24h"
              color={totalFunding24h >= 0 ? "#0ECB81" : "#F6465D"}
            />
            <KpiCard
              label="Capital Used"
              value={`$${deployedCapital.toLocaleString()}`}
              sub={`of $${totalCapital.toLocaleString()} (${((deployedCapital / totalCapital) * 100).toFixed(0)}%)`}
              color={deployedCapital > totalCapital * 0.8 ? "#F6465D" : undefined}
            />
          </div>

          {/* Main two-panel row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {/* Scanner */}
            <div className="bg-surface rounded border border-subtle overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 border-b border-subtle">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">ARB Spreads</span>
                <div className="flex items-center gap-3">
                  {scannedAgo && (
                    <span className="text-xs text-muted">Updated {scannedAgo}</span>
                  )}
                  <button
                    className="text-xs text-blue-400 hover:opacity-80 disabled:opacity-40"
                    onClick={() => refreshScanner.mutate()}
                    disabled={refreshScanner.isPending}
                  >
                    {refreshScanner.isPending ? "Refreshing…" : "Refresh"}
                  </button>
                  <span className="text-xs text-muted">{opportunities.length} pairs · click to trade</span>
                </div>
              </div>
              {scanLoading ? (
                <div className="p-4 space-y-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-full bg-surface-2" />
                  ))}
                </div>
              ) : (
                <ScannerTable opportunities={opportunities} />
              )}
            </div>

            {/* Open Positions */}
            <div className="bg-surface rounded border border-subtle overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 border-b border-subtle">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">Open Positions</span>
                <div className="flex items-center gap-3">
                  <button
                    className="text-xs text-yellow hover:opacity-80 disabled:opacity-40"
                    onClick={() => applyFunding.mutate()}
                    disabled={applyFunding.isPending || openPairs.length === 0}
                  >
                    {applyFunding.isPending ? "Applying…" : "Apply Funding"}
                  </button>
                  {!confirmCloseAll ? (
                    <button
                      className="text-xs text-red hover:opacity-80 disabled:opacity-40"
                      onClick={() => setConfirmCloseAll(true)}
                      disabled={openPairs.length === 0}
                    >
                      Close All
                    </button>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <span className="text-xs text-muted">Confirm?</span>
                      <button
                        className="text-xs text-red hover:opacity-80 disabled:opacity-40"
                        onClick={() => closeAll.mutate()}
                        disabled={closeAll.isPending}
                      >
                        {closeAll.isPending ? "Closing…" : "Yes"}
                      </button>
                      <button
                        className="text-xs text-muted hover:opacity-80"
                        onClick={() => setConfirmCloseAll(false)}
                      >
                        No
                      </button>
                    </span>
                  )}
                </div>
              </div>
              <PositionsTable pairs={openPairs} riskMap={riskMap} isLoading={posLoading} />
            </div>
          </div>

          {/* Bottom tabs */}
          <div className="bg-surface rounded border border-subtle overflow-hidden">
            <Tabs defaultValue="pnl">
              <TabsList className="bg-surface-2 rounded-none border-b border-subtle h-9 px-4 gap-1 w-full justify-start">
                <TabsTrigger value="pnl" className="text-xs h-7 data-[state=active]:bg-accent">P&L Chart</TabsTrigger>
                <TabsTrigger value="history" className="text-xs h-7 data-[state=active]:bg-accent">Trade History</TabsTrigger>
                <TabsTrigger value="risk" className="text-xs h-7 data-[state=active]:bg-accent">
                  Risk Alerts
                  {alertCount > 0 && (
                    <span className="ml-1.5 bg-red text-white text-xs px-1.5 py-0.5 rounded-full leading-none">
                      {alertCount}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="pnl" className="p-4 mt-0">
                <PnlChart points={pnlPoints} />
              </TabsContent>

              <TabsContent value="history" className="mt-0">
                <div className="overflow-auto max-h-64">
                  <table className="w-full text-xs trade-table">
                    <thead>
                      <tr className="border-b border-subtle text-muted font-medium text-left">
                        <th className="px-3 py-2">ID</th>
                        <th className="px-3 py-2">BASE</th>
                        <th className="px-3 py-2">SHORT</th>
                        <th className="px-3 py-2">LONG</th>
                        <th className="px-3 py-2">COLLATERAL</th>
                        <th className="px-3 py-2">LVRG</th>
                        <th className="px-3 py-2">FUNDING</th>
                        <th className="px-3 py-2">NET P&L</th>
                        <th className="px-3 py-2">OPENED</th>
                        <th className="px-3 py-2">CLOSED</th>
                        <th className="px-3 py-2">REASON</th>
                      </tr>
                    </thead>
                    <tbody>
                      {closedPairs.length === 0 && (
                        <tr>
                          <td colSpan={11} className="px-3 py-6 text-center text-muted">No closed positions</td>
                        </tr>
                      )}
                      {closedPairs.map((p) => (
                        <tr key={p.pair_id} className="border-b border-subtle row-hover cursor-pointer" onClick={() => setHistoryDetail(p)}>
                          <td className="px-3 py-2 font-mono text-muted">{p.pair_id}</td>
                          <td className="px-3 py-2 font-semibold">{p.base}</td>
                          <td className="px-3 py-2 text-muted">{p.short_exchange}</td>
                          <td className="px-3 py-2 text-muted">{p.long_exchange}</td>
                          <td className="px-3 py-2 font-mono">${(p.size_usd / p.leverage * 2).toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                          <td className="px-3 py-2 font-mono font-semibold">
                            <span className={p.leverage > 1 ? "text-yellow" : "text-muted"}>{p.leverage}x</span>
                          </td>
                          <td className={`px-3 py-2 font-mono ${p.funding_collected >= 0 ? "text-green" : "text-red"}`}>
                            {fmtUsd(p.funding_collected)}
                          </td>
                          <td className={`px-3 py-2 font-mono font-semibold ${(p.net_pnl ?? 0) >= 0 ? "text-green" : "text-red"}`}>
                            {fmtUsd(p.net_pnl ?? 0)}
                          </td>
                          <td className="px-3 py-2 text-muted text-xs">{p.opened_at?.slice(0, 16)}</td>
                          <td className="px-3 py-2 text-muted text-xs">{p.closed_at?.slice(0, 16) ?? "—"}</td>
                          <td className="px-3 py-2">
                            {p.close_reason === "stop_loss" ? (
                              <span className="px-1.5 py-0.5 rounded text-xs font-semibold bg-red/20 text-red">Stop-Loss</span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-xs font-semibold bg-surface-2 text-muted">Manual</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </TabsContent>

              <TabsContent value="risk" className="p-4 mt-0">
                {riskResults.length === 0 ? (
                  <p className="text-muted text-xs text-center py-4">No open positions to monitor.</p>
                ) : (
                  <div className="space-y-2">
                    {riskResults.map((r) => (
                      <div
                        key={r.pair_id}
                        className="bg-surface-2 rounded p-3 text-xs space-y-1"
                        style={{
                          borderLeft: `3px solid ${
                            r.level === "ok" ? "#0ECB81" :
                            r.level === "drift_warning" ? "#F0B90B" : "#F6465D"
                          }`,
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{r.base}</span>
                          <span className="font-mono text-muted">{r.pair_id}</span>
                          <span className="text-muted ml-auto">drift {(r.drift_pct * 100).toFixed(3)}%</span>
                          <span className="text-muted">net {fmtUsd(r.net_pnl)}</span>
                        </div>
                        {r.alerts.map((a, i) => (
                          <p key={i} className="text-yellow">{a}</p>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </DashboardShell>

      <OpenPairModal />
      <ShortcutHelp />
      <ClosedPositionDetail pair={historyDetail} onClose={() => setHistoryDetail(null)} />
    </WsProvider>
  );
}
