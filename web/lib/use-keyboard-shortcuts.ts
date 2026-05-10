"use client";
import { useEffect } from "react";
import type { Opportunity } from "@/lib/types";

interface Options {
  opportunities: Opportunity[];
  onOpenTrade: (opp: Opportunity) => void;
  onToggleHelp: () => void;
}

export function useKeyboardShortcuts({ opportunities, onOpenTrade, onToggleHelp }: Options) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const inInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      if (e.key === "?" && !inInput) {
        e.preventDefault();
        onToggleHelp();
        return;
      }

      if (inInput) return;

      if (e.key === "/") {
        e.preventDefault();
        document.getElementById("scanner-filter")?.focus();
        return;
      }

      if (e.key === "o" || e.key === "O") {
        e.preventDefault();
        if (opportunities.length > 0) onOpenTrade(opportunities[0]);
        return;
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [opportunities, onOpenTrade, onToggleHelp]);
}
