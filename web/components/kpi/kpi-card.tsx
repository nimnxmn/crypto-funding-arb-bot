interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}

export function KpiCard({ label, value, sub, color }: KpiCardProps) {
  return (
    <div className="bg-surface rounded p-4 flex flex-col gap-1 border border-subtle">
      <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
      <span className="text-xl font-mono font-semibold" style={{ color: color ?? "var(--foreground)" }}>
        {value}
      </span>
      {sub && <span className="text-xs text-muted">{sub}</span>}
    </div>
  );
}
