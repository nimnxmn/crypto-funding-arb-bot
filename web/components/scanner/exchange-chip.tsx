import { exchangeColor } from "@/lib/format";

export function ExchangeChip({ name }: { name: string }) {
  return (
    <span
      className="text-xs font-semibold px-1.5 py-0.5 rounded"
      style={{ color: exchangeColor(name), background: `${exchangeColor(name)}18` }}
    >
      {name}
    </span>
  );
}
