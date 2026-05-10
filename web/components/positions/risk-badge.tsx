import type { RiskLevel } from "@/lib/types";

const styles: Record<RiskLevel, { label: string; color: string; bg: string }> = {
  ok:             { label: "OK",      color: "#0ECB81", bg: "#0ECB8118" },
  drift_warning:  { label: "DRIFT",   color: "#F0B90B", bg: "#F0B90B18" },
  drift_critical: { label: "CRIT",    color: "#F6465D", bg: "#F6465D18" },
  stop_loss:      { label: "STOP",    color: "#F6465D", bg: "#F6465D33" },
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  const s = styles[level];
  return (
    <span
      className="text-xs font-bold px-1.5 py-0.5 rounded"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}
