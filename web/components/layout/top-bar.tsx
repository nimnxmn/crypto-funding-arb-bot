"use client";
import { useQuery } from "@tanstack/react-query";
import { Menu } from "lucide-react";
import { api } from "@/lib/api";
import { useUiStore } from "@/stores/ui-store";
import { ModeSwitch } from "@/components/mode/mode-switch";

export function TopBar() {
  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: api.getMeta });
  const { data: balances } = useQuery({ queryKey: ["balances"], queryFn: api.getBalances });
  const { wsStatus, setMobileSidebarOpen } = useUiStore();

  const isLive = meta?.mode === "live";
  const mode = (meta?.mode ?? "paper") as "paper" | "live";

  return (
    <header
      className="flex items-center justify-between px-4 h-12 border-b border-subtle shrink-0 transition-colors"
      style={{ borderBottomColor: isLive ? "#F6465D" : undefined }}
    >
      <div className="flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          className="lg:hidden text-muted hover:text-foreground mr-1"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label="Open menu"
        >
          <Menu size={18} />
        </button>

        <span className="font-bold text-yellow text-sm tracking-tight">Crypto Funding Arb Bot</span>
        <ModeSwitch currentMode={mode} />
      </div>

      <div className="flex items-center gap-4 text-xs text-muted font-mono">
        {/* Exchange balances (live mode only) */}
        {balances?.balances.map((b) => (
          <span key={b.exchange} className="hidden sm:inline">
            <span className="text-muted">{b.exchange} </span>
            <span className="text-foreground">
              ${b.balance_usdt.toLocaleString("en-US", { maximumFractionDigits: 0 })}
            </span>
          </span>
        ))}

        {/* WS status dot */}
        <span className="flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full inline-block transition-colors"
            style={{
              background:
                wsStatus === "connected" ? "#0ECB81" :
                wsStatus === "connecting" ? "#F0B90B" : "#F6465D",
            }}
          />
          <span className="text-muted hidden sm:inline">{wsStatus}</span>
        </span>
      </div>
    </header>
  );
}
