"use client";
import { useState, useEffect } from "react";
import { fmtCountdown } from "@/lib/format";

export function CountdownCell({ tsMs }: { tsMs: number }) {
  const [display, setDisplay] = useState(fmtCountdown(tsMs));

  useEffect(() => {
    setDisplay(fmtCountdown(tsMs));
    const id = setInterval(() => setDisplay(fmtCountdown(tsMs)), 1000);
    return () => clearInterval(id);
  }, [tsMs]);

  return <span className="font-mono text-muted text-xs">{display}</span>;
}
