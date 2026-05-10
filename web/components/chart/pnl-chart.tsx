"use client";
import { useEffect, useRef } from "react";
import type { PnlPoint } from "@/lib/types";

interface Props {
  points: PnlPoint[];
}

function toChartData(points: PnlPoint[]) {
  const map = new Map<number, number>();
  for (const p of points) {
    map.set(Math.floor(new Date(p.timestamp).getTime() / 1000), p.cumulative_pnl);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a - b)
    .map(([time, value]) => ({ time: time as any, value }));
}

function toMarkers(points: PnlPoint[]) {
  const seen = new Set<number>();
  const markers: any[] = [];
  for (const p of points) {
    if (p.event_type !== "open" && p.event_type !== "close") continue;
    const t = Math.floor(new Date(p.timestamp).getTime() / 1000);
    // deduplicate by time+type to avoid stacking markers at same second
    const key = t * 10 + (p.event_type === "open" ? 0 : 1);
    if (seen.has(key)) continue;
    seen.add(key);
    if (p.event_type === "open") {
      markers.push({ time: t as any, position: "belowBar", shape: "arrowUp", color: "#F0B90B", text: "Open" });
    } else {
      const color = p.amount_usd >= 0 ? "#0ECB81" : "#F6465D";
      markers.push({ time: t as any, position: "aboveBar", shape: "arrowDown", color, text: "Close" });
    }
  }
  markers.sort((a, b) => a.time - b.time);
  return markers;
}

export function PnlChart({ points }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<unknown>(null);
  const seriesRef = useRef<unknown>(null);
  const markersRef = useRef<unknown>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let chart: unknown;
    import("lightweight-charts").then(({ createChart, LineSeries, LineStyle, createSeriesMarkers }) => {
      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 220,
        layout: { background: { color: "#181A20" }, textColor: "#848E9C" },
        grid: { vertLines: { color: "#2B3139" }, horzLines: { color: "#2B3139" } },
        crosshair: { mode: 1 },
        rightPriceScale: { borderColor: "#2B3139" },
        timeScale: { borderColor: "#2B3139", timeVisible: true },
      });

      const series = (chart as any).addSeries(LineSeries, {
        color: "#0ECB81",
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineColor: "#0ECB81",
        priceLineStyle: LineStyle.Dashed,
      });

      chartRef.current = chart;
      seriesRef.current = series;
      markersRef.current = createSeriesMarkers(series, []);

      if (points.length > 0) {
        series.setData(toChartData(points));
        (markersRef.current as any).setMarkers(toMarkers(points));
      }
    });

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        (chartRef.current as any).applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      if (chartRef.current) (chartRef.current as any).remove();
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || points.length === 0) return;
    (seriesRef.current as any).setData(toChartData(points));
    if (markersRef.current) (markersRef.current as any).setMarkers(toMarkers(points));
  }, [points]);

  if (points.length === 0) {
    return (
      <div className="h-[220px] flex items-center justify-center text-muted text-xs">
        No P&L history yet — open a position and apply funding to see the chart.
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" />;
}
