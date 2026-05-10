"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { WsProvider } from "@/components/ws-provider";
import { ModeSwitch } from "@/components/mode/mode-switch";
import { ShortcutHelp } from "@/components/mode/shortcut-help";
import type { UpdateConfigRequest } from "@/lib/types";

type CapitalForm = { total_capital: number; max_position_pct: number; leverage: number };
type RiskForm = { stop_loss_pct: number; drift_warning_pct: number; drift_critical_pct: number };
type FeeForm = { min_spread_multiplier: number; min_24h_volume_usd_m: number };

function NumInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type="number"
      className="w-28 px-2 py-1 text-xs font-mono text-right rounded bg-surface-2 border border-subtle text-foreground focus:outline-none focus:border-yellow"
      {...props}
    />
  );
}

function FieldRow({ label, note, children }: { label: string; note?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-subtle last:border-0 gap-4">
      <div className="min-w-0">
        <div className="text-xs font-medium text-foreground">{label}</div>
        {note && <div className="text-xs text-muted mt-0.5">{note}</div>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Section({
  title, children, onSave, saving,
}: {
  title: string; children: React.ReactNode; onSave?: () => void; saving?: boolean;
}) {
  return (
    <div className="bg-surface rounded border border-subtle overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-subtle">
        <span className="text-xs font-semibold text-muted uppercase tracking-wider">{title}</span>
        {onSave && (
          <button
            onClick={onSave}
            disabled={saving}
            className="text-xs px-3 py-1 rounded bg-yellow text-black font-semibold hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        )}
      </div>
      <div className="px-4">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: api.getMeta });
  const mode = (meta?.mode ?? "paper") as "paper" | "live";
  const [confirmReset, setConfirmReset] = useState(false);

  const configMut = useMutation({
    mutationFn: (body: UpdateConfigRequest) => api.updateConfig(body),
    onSuccess: () => {
      toast.success("Settings saved");
      qc.invalidateQueries({ queryKey: ["meta"] });
    },
    onError: (e: Error) => toast.error(`Save failed: ${e.message}`),
  });

  const resetMut = useMutation({
    mutationFn: api.resetPaperTrade,
    onSuccess: () => {
      toast.success("Paper trade reset — starting fresh");
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["pnl"] });
      setConfirmReset(false);
    },
    onError: (e: Error) => toast.error(`Reset failed: ${e.message}`),
  });

  const capitalForm = useForm<CapitalForm>({ defaultValues: { total_capital: 10000, max_position_pct: 20, leverage: 1 } });
  const riskForm = useForm<RiskForm>({ defaultValues: { stop_loss_pct: 2, drift_warning_pct: 0.3, drift_critical_pct: 1.0 } });
  const feeForm = useForm<FeeForm>({ defaultValues: { min_spread_multiplier: 2, min_24h_volume_usd_m: 1 } });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!meta) return;
    capitalForm.reset({ total_capital: meta.total_capital, max_position_pct: meta.max_position_pct * 100, leverage: meta.leverage });
    riskForm.reset({ stop_loss_pct: meta.stop_loss_pct * 100, drift_warning_pct: meta.drift_warning_pct * 100, drift_critical_pct: meta.drift_critical_pct * 100 });
    feeForm.reset({ min_spread_multiplier: meta.min_spread_multiplier, min_24h_volume_usd_m: meta.min_24h_volume_usd / 1_000_000 });
  }, [meta]);

  const handleCapitalSave = capitalForm.handleSubmit((v) =>
    configMut.mutate({ total_capital: v.total_capital, max_position_pct: v.max_position_pct / 100, leverage: v.leverage })
  );
  const handleRiskSave = riskForm.handleSubmit((v) =>
    configMut.mutate({ stop_loss_pct: v.stop_loss_pct / 100, drift_warning_pct: v.drift_warning_pct / 100, drift_critical_pct: v.drift_critical_pct / 100 })
  );
  const handleFeeSave = feeForm.handleSubmit((v) =>
    configMut.mutate({ min_spread_multiplier: v.min_spread_multiplier, min_24h_volume_usd: v.min_24h_volume_usd_m * 1_000_000 })
  );

  return (
    <WsProvider>
      <DashboardShell>
        <div className="p-4 space-y-4 max-w-2xl">
          <h1 className="text-sm font-semibold text-foreground">Settings</h1>

          <Section title="Trading Mode">
            <div className="flex items-center justify-between py-3">
              <div>
                <div className="text-xs font-medium text-foreground">Current mode</div>
                <div className="text-xs text-muted mt-0.5">
                  {mode === "paper"
                    ? "Paper mode — no real orders placed, safe to experiment"
                    : "Live mode — real orders on exchanges, real funds at risk"}
                </div>
              </div>
              {meta && <ModeSwitch currentMode={mode} />}
            </div>
          </Section>

          <Section title="Capital & Position Limits" onSave={handleCapitalSave} saving={configMut.isPending}>
            <FieldRow label="Total Capital" note="Total USDT available across all exchanges">
              <div className="flex items-center gap-1">
                <span className="text-xs text-muted">$</span>
                <NumInput step="100" min="0" {...capitalForm.register("total_capital", { valueAsNumber: true })} />
              </div>
            </FieldRow>
            <FieldRow label="Max Position Size" note="Max % of capital per pair leg">
              <div className="flex items-center gap-1">
                <NumInput step="1" min="1" max="100" {...capitalForm.register("max_position_pct", { valueAsNumber: true })} />
                <span className="text-xs text-muted">%</span>
              </div>
            </FieldRow>
            <FieldRow label="Default Leverage" note="Applied to new positions (1x = no leverage, max 10x)">
              <div className="flex gap-1 flex-wrap justify-end">
                {[1, 2, 3, 5, 10].map((lv) => {
                  const current = capitalForm.watch("leverage");
                  return (
                    <button
                      key={lv}
                      type="button"
                      onClick={() => capitalForm.setValue("leverage", lv)}
                      className={`px-2 py-1 rounded text-xs font-mono font-semibold border transition-colors ${
                        current === lv
                          ? "bg-yellow text-black border-yellow"
                          : "bg-surface-2 border-subtle text-muted hover:border-yellow"
                      }`}
                    >
                      {lv}x
                    </button>
                  );
                })}
              </div>
            </FieldRow>
          </Section>

          <Section title="Risk Thresholds" onSave={handleRiskSave} saving={configMut.isPending}>
            <FieldRow label="Stop-Loss" note="Close pair if P&L drops below this % of position size">
              <div className="flex items-center gap-1">
                <NumInput step="0.1" min="0" {...riskForm.register("stop_loss_pct", { valueAsNumber: true })} />
                <span className="text-xs text-muted">%</span>
              </div>
            </FieldRow>
            <FieldRow label="Drift Warning" note="Alert when price divergence between exchanges exceeds this level">
              <div className="flex items-center gap-1">
                <NumInput step="0.01" min="0" {...riskForm.register("drift_warning_pct", { valueAsNumber: true })} />
                <span className="text-xs text-muted">%</span>
              </div>
            </FieldRow>
            <FieldRow label="Drift Critical" note="Suggest close/reopen when divergence exceeds this level">
              <div className="flex items-center gap-1">
                <NumInput step="0.01" min="0" {...riskForm.register("drift_critical_pct", { valueAsNumber: true })} />
                <span className="text-xs text-muted">%</span>
              </div>
            </FieldRow>
          </Section>

          <Section title="Fee & Spread Configuration" onSave={handleFeeSave} saving={configMut.isPending}>
            <FieldRow label="Min Spread Multiplier" note="Spread must be ≥ this × round-trip fee to open a pair">
              <div className="flex items-center gap-1">
                <NumInput step="0.1" min="1" {...feeForm.register("min_spread_multiplier", { valueAsNumber: true })} />
                <span className="text-xs text-muted">×</span>
              </div>
            </FieldRow>
            <FieldRow label="Min 24h Volume" note="Per-leg liquidity filter — drops illiquid pairs from scanner">
              <div className="flex items-center gap-1">
                <span className="text-xs text-muted">$</span>
                <NumInput step="0.1" min="0" {...feeForm.register("min_24h_volume_usd_m", { valueAsNumber: true })} />
                <span className="text-xs text-muted">M</span>
              </div>
            </FieldRow>
          </Section>

          <Section title="Keyboard Shortcuts">
            <div className="py-3 space-y-2">
              {[
                { key: "/",   description: "Focus scanner filter" },
                { key: "O",   description: "Open trade modal (top opportunity)" },
                { key: "?",   description: "Show shortcut help overlay" },
                { key: "Esc", description: "Close any open modal" },
              ].map(({ key, description }) => (
                <div key={key} className="flex items-center justify-between text-xs">
                  <span className="text-muted">{description}</span>
                  <kbd className="px-2 py-0.5 rounded bg-surface-2 border border-subtle font-mono text-foreground">
                    {key}
                  </kbd>
                </div>
              ))}
            </div>
          </Section>

          <div className="bg-surface rounded border border-subtle overflow-hidden">
            <div className="px-4 py-2 border-b border-subtle">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">Danger Zone</span>
            </div>
            <div className="px-4 py-4 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="text-xs font-medium text-foreground">Reset Paper Trade Account</div>
                <div className="text-xs text-muted mt-0.5">
                  Wipes all trade history and resets the simulator to zero. Cannot be undone.
                </div>
              </div>
              {!confirmReset ? (
                <button
                  className="text-xs px-3 py-1 rounded border border-red text-red hover:bg-red hover:text-white transition-colors shrink-0"
                  onClick={() => setConfirmReset(true)}
                >
                  Reset Account
                </button>
              ) : (
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-red">Sure?</span>
                  <button
                    className="text-xs px-2 py-1 rounded bg-red text-white hover:opacity-90 disabled:opacity-50"
                    onClick={() => resetMut.mutate()}
                    disabled={resetMut.isPending}
                  >
                    {resetMut.isPending ? "Resetting…" : "Yes, reset"}
                  </button>
                  <button
                    className="text-xs px-2 py-1 rounded bg-surface-2 border border-subtle text-muted hover:opacity-80"
                    onClick={() => setConfirmReset(false)}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardShell>
      <ShortcutHelp />
    </WsProvider>
  );
}
