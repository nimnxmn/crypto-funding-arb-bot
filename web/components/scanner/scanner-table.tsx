"use client";
import { useState, useMemo, useRef } from "react";
import {
  useReactTable, getCoreRowModel, getSortedRowModel, getFilteredRowModel,
  type ColumnDef, type SortingState, flexRender,
} from "@tanstack/react-table";
import { motion, AnimatePresence } from "framer-motion";
import type { Opportunity } from "@/lib/types";
import { fmtPct, fmtVolume } from "@/lib/format";
import { ExchangeChip } from "./exchange-chip";
import { CountdownCell } from "./countdown-cell";
import { useUiStore } from "@/stores/ui-store";

const ROUND_TRIP_FEE = 0.002;

export function ScannerTable({ opportunities }: { opportunities: Opportunity[] }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "spread", desc: true }]);
  const [globalFilter, setGlobalFilter] = useState("");
  const setSelectedOpp = useUiStore((s) => s.setSelectedOpp);

  const columns = useMemo<ColumnDef<Opportunity>[]>(() => [
    {
      accessorKey: "base",
      header: "BASE",
      filterFn: "includesString",
      cell: ({ getValue }) => (
        <span className="font-semibold text-foreground">{getValue() as string}</span>
      ),
    },
    {
      id: "short",
      header: "SHORT",
      cell: ({ row }) => <ExchangeChip name={row.original.short_exchange} />,
      enableSorting: false,
    },
    {
      accessorKey: "short_rate",
      header: "S RATE/8H",
      cell: ({ getValue }) => (
        <span className={`font-mono ${(getValue() as number) > 0 ? "text-green" : "text-red"}`}>
          {fmtPct(getValue() as number)}
        </span>
      ),
    },
    {
      id: "short_next",
      header: "NEXT",
      cell: ({ row }) => <CountdownCell tsMs={row.original.short_next_funding} />,
      enableSorting: false,
    },
    {
      id: "long",
      header: "LONG",
      cell: ({ row }) => <ExchangeChip name={row.original.long_exchange} />,
      enableSorting: false,
    },
    {
      accessorKey: "long_rate",
      header: "L RATE/8H",
      cell: ({ getValue }) => (
        <span className={`font-mono ${(getValue() as number) > 0 ? "text-green" : "text-red"}`}>
          {fmtPct(getValue() as number)}
        </span>
      ),
    },
    {
      id: "long_next",
      header: "NEXT",
      cell: ({ row }) => <CountdownCell tsMs={row.original.long_next_funding} />,
      enableSorting: false,
    },
    {
      accessorKey: "spread",
      header: "SPREAD",
      cell: ({ getValue }) => {
        const v = getValue() as number;
        const beats = v > ROUND_TRIP_FEE;
        return (
          <span className={`font-mono font-semibold ${beats ? "text-green" : "text-muted"}`}>
            {fmtPct(v)} {beats && "✓"}
          </span>
        );
      },
    },
    {
      accessorKey: "annual_capital_yield",
      header: "CAP APR",
      cell: ({ getValue }) => {
        const v = getValue() as number;
        return (
          <span className={`font-mono ${v > 0 ? "text-green" : "text-muted"}`}>
            {fmtPct(v, 1)}
          </span>
        );
      },
    },
    {
      id: "vol",
      header: "MIN VOL",
      cell: ({ row }) => (
        <span className="font-mono text-muted text-xs">
          {fmtVolume(Math.min(row.original.short_volume_24h, row.original.long_volume_24h))}
        </span>
      ),
      enableSorting: false,
    },
  ], []);

  const table = useReactTable({
    data: opportunities,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: (row, _colId, filterValue: string) =>
      row.original.base.toLowerCase().includes(filterValue.toLowerCase()),
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const rows = table.getRowModel().rows;

  return (
    <div>
      {/* Filter input */}
      <div className="px-3 py-2 border-b border-subtle">
        <input
          id="scanner-filter"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Filter by base… (press /)"
          className="w-full bg-transparent text-xs text-foreground placeholder-muted outline-none"
        />
      </div>

      <div className="overflow-auto">
        <table className="w-full text-xs trade-table">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-subtle">
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    className="text-left text-muted font-medium whitespace-nowrap select-none px-3 py-2"
                    style={{ cursor: h.column.getCanSort() ? "pointer" : "default" }}
                    onClick={h.column.getToggleSortingHandler()}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {h.column.getIsSorted() === "asc" ? " ↑" : h.column.getIsSorted() === "desc" ? " ↓" : ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {rows.map((row) => (
                <motion.tr
                  key={row.original.base}
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.15 }}
                  className="border-b border-subtle row-hover"
                  onClick={() => setSelectedOpp(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2 whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </motion.tr>
              ))}
            </AnimatePresence>
            {rows.length === 0 && (
              <tr>
                <td colSpan={10} className="px-3 py-8 text-center text-muted">
                  {globalFilter ? `No results for "${globalFilter}"` : "Scanner running…"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
