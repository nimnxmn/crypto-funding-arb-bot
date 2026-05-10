"use client";
import { useEffect, useRef, useCallback } from "react";
import type { WsMessage } from "./types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export type WsStatus = "connecting" | "connected" | "disconnected";

export function useWebSocket(onMessage: (msg: WsMessage) => void) {
  const ws = useRef<WebSocket | null>(null);
  const statusRef = useRef<WsStatus>("disconnected");
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    statusRef.current = "connecting";
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      statusRef.current = "connected";
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };

    socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage;
        onMessage(msg);
      } catch {
        // ignore malformed
      }
    };

    socket.onclose = () => {
      statusRef.current = "disconnected";
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  return statusRef;
}
