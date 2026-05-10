"use client";
import { useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useWebSocket } from "@/lib/ws";
import { useUiStore } from "@/stores/ui-store";
import type { WsMessage } from "@/lib/types";

export function WsProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const setWsStatus = useUiStore((s) => s.setWsStatus);

  const onMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "scanner") {
      qc.setQueryData(["scanner"], msg.data);
    } else if (msg.type === "positions") {
      qc.setQueryData(["positions"], msg.data);
    } else if (msg.type === "risk") {
      qc.setQueryData(["risk"], msg.data);
    } else if (msg.type === "balances") {
      qc.setQueryData(["balances"], msg.data);
    } else if (msg.type === "notification") {
      const { level, message } = msg.data;
      if (level === "error") toast.error(message);
      else if (level === "success") toast.success(message);
      else toast(message);
    }
  }, [qc]);

  const statusRef = useWebSocket(onMessage);

  useEffect(() => {
    const id = setInterval(() => {
      setWsStatus(statusRef.current);
    }, 1000);
    return () => clearInterval(id);
  }, [statusRef, setWsStatus]);

  return <>{children}</>;
}
