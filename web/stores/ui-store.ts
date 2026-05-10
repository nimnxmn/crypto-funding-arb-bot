import { create } from "zustand";
import type { Opportunity } from "@/lib/types";

interface UiStore {
  selectedOpp: Opportunity | null;
  setSelectedOpp: (opp: Opportunity | null) => void;
  openTradeModal: boolean;
  setOpenTradeModal: (v: boolean) => void;
  wsStatus: "connecting" | "connected" | "disconnected";
  setWsStatus: (s: "connecting" | "connected" | "disconnected") => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  mobileSidebarOpen: boolean;
  setMobileSidebarOpen: (v: boolean) => void;
  shortcutHelpOpen: boolean;
  setShortcutHelpOpen: (v: boolean) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  selectedOpp: null,
  setSelectedOpp: (opp) => set({ selectedOpp: opp, openTradeModal: !!opp }),
  openTradeModal: false,
  setOpenTradeModal: (v) => set({ openTradeModal: v }),
  wsStatus: "connecting",
  setWsStatus: (s) => set({ wsStatus: s }),
  sidebarCollapsed: false,
  setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
  mobileSidebarOpen: false,
  setMobileSidebarOpen: (v) => set({ mobileSidebarOpen: v }),
  shortcutHelpOpen: false,
  setShortcutHelpOpen: (v) => set({ shortcutHelpOpen: v }),
}));
