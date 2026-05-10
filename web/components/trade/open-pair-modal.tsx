"use client";
import { useEffect } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { useUiStore } from "@/stores/ui-store";
import { api } from "@/lib/api";
import { fmtPct, fmtUsd } from "@/lib/format";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ExchangeChip } from "@/components/scanner/exchange-chip";

const schema = z.object({
  size_usd: z.coerce.number().min(10, "Min size $10").max(100_000, "Max size $100K"),
  leverage: z.coerce.number().int().min(1, "Min 1x").max(10, "Max 10x"),
});

type FormData = z.infer<typeof schema>;

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 10];

export function OpenPairModal() {
  const { selectedOpp, openTradeModal, setOpenTradeModal, setSelectedOpp } = useUiStore();
  const qc = useQueryClient();

  const { data: meta } = useQuery({ queryKey: ["meta"], queryFn: api.getMeta });

  const { register, handleSubmit, watch, formState: { errors }, reset, setValue } = useForm<FormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as Resolver<FormData>,
    defaultValues: { size_usd: 1000, leverage: 1 },
  });

  // Sync default leverage from meta whenever it loads or the modal opens
  useEffect(() => {
    if (meta?.leverage !== undefined) {
      setValue("leverage", meta.leverage);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta?.leverage, openTradeModal]);

  const sizeUsd = watch("size_usd") || 0;
  const leverage = watch("leverage") || 1;

  const openMutation = useMutation({
    mutationFn: (data: FormData) => {
      if (!selectedOpp) throw new Error("No opportunity selected");
      return api.openPosition({
        base: selectedOpp.base,
        size_usd: data.size_usd * data.leverage,  // notional = collateral × leverage
        leverage: data.leverage,
        short_exchange: selectedOpp.short_exchange,
        short_price: selectedOpp.short_price,
        short_rate: selectedOpp.short_rate,
        long_exchange: selectedOpp.long_exchange,
        long_price: selectedOpp.long_price,
        long_rate: selectedOpp.long_rate,
      });
    },
    onSuccess: (pair) => {
      qc.invalidateQueries({ queryKey: ["positions"] });
      toast.success(`Opened ${pair.base} ${pair.leverage}x — short ${pair.short_exchange} / long ${pair.long_exchange}`);
      setSelectedOpp(null);
      reset();
    },
    onError: (e: Error) => {
      toast.error(`Open failed: ${e.message}`);
    },
  });

  const roundTripFee = meta?.round_trip_fee ?? 0.002;
  const metaLeverage = meta?.leverage ?? 1;
  // size_usd = collateral per leg; notional = collateral × leverage
  const notional = sizeUsd * leverage;
  const estimatedFees = notional * roundTripFee;
  const spreadPer8h = (selectedOpp?.spread ?? 0) * notional;
  const totalCollateral = sizeUsd * 2;
  // Rescale cap APR from the scanner's default leverage to the user's chosen leverage
  const capApr = (selectedOpp?.annual_capital_yield ?? 0) * leverage / metaLeverage;

  // Liquidation prices (approx, 1% maintenance margin)
  const liqShort = selectedOpp ? selectedOpp.short_price * (1 + 1 / leverage - 0.01) : null;
  const liqLong = selectedOpp ? selectedOpp.long_price * (1 - 1 / leverage + 0.01) : null;

  return (
    <Dialog open={openTradeModal} onOpenChange={(v) => { setOpenTradeModal(v); if (!v) setSelectedOpp(null); }}>
      <DialogContent className="bg-surface border-subtle max-w-md">
        <DialogHeader>
          <DialogTitle className="text-sm">
            Open Arb Pair — <span className="text-yellow">{selectedOpp?.base}</span>
          </DialogTitle>
        </DialogHeader>

        {selectedOpp && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-2 bg-surface-2 rounded p-3">
              <div>
                <div className="text-muted mb-1">SHORT</div>
                <div className="flex items-center gap-1.5">
                  <ExchangeChip name={selectedOpp.short_exchange} />
                  <span className="font-mono text-green">{fmtPct(selectedOpp.short_rate)}/8h</span>
                </div>
              </div>
              <div>
                <div className="text-muted mb-1">LONG</div>
                <div className="flex items-center gap-1.5">
                  <ExchangeChip name={selectedOpp.long_exchange} />
                  <span className="font-mono">{fmtPct(selectedOpp.long_rate)}/8h</span>
                </div>
              </div>
              <div className="col-span-2 border-t border-subtle pt-2 mt-1">
                <div className="flex justify-between">
                  <span className="text-muted">Spread/8h</span>
                  <span className="font-mono text-green font-semibold">{fmtPct(selectedOpp.spread)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Cap APR ({leverage}x)</span>
                  <span className="font-mono text-green">{fmtPct(capApr, 1)}</span>
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit((d) => openMutation.mutate(d))} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-muted block mb-1">Collateral per leg (USDT)</label>
                  <Input
                    type="number"
                    className="bg-surface-2 border-subtle font-mono h-8 text-sm"
                    {...register("size_usd")}
                  />
                  {errors.size_usd && <p className="text-red mt-1">{errors.size_usd.message}</p>}
                </div>
                <div>
                  <label className="text-muted block mb-1">Leverage</label>
                  <div className="flex gap-1 flex-wrap">
                    {LEVERAGE_OPTIONS.map((lv) => (
                      <button
                        key={lv}
                        type="button"
                        onClick={() => setValue("leverage", lv)}
                        className={`px-2 py-1 rounded text-xs font-mono font-semibold border transition-colors ${
                          leverage === lv
                            ? "bg-yellow text-black border-yellow"
                            : "bg-surface-2 border-subtle text-muted hover:border-yellow"
                        }`}
                      >
                        {lv}x
                      </button>
                    ))}
                  </div>
                  {errors.leverage && <p className="text-red mt-1">{errors.leverage.message}</p>}
                </div>
              </div>

              <div className="bg-surface-2 rounded p-3 space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted">Round-trip fees</span>
                  <span className="font-mono text-red">{fmtUsd(-estimatedFees)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Expected/8h</span>
                  <span className="font-mono text-green">+${spreadPer8h.toFixed(2)}</span>
                </div>
                <div className="flex justify-between border-t border-subtle pt-1 mt-1">
                  <span className="text-muted">Notional per leg</span>
                  <span className="font-mono">${notional.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Total collateral locked</span>
                  <span className="font-mono font-semibold">${totalCollateral.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                </div>
                {leverage > 1 && liqShort !== null && liqLong !== null && (
                  <div className="border-t border-subtle pt-1 mt-1 space-y-0.5">
                    <div className="flex justify-between text-yellow">
                      <span>Short liq price (~)</span>
                      <span className="font-mono">${liqShort.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-yellow">
                      <span>Long liq price (~)</span>
                      <span className="font-mono">${liqLong.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setSelectedOpp(null)}>Cancel</Button>
                <Button
                  type="submit"
                  disabled={openMutation.isPending}
                  className="bg-yellow text-black hover:bg-yellow/90"
                >
                  {openMutation.isPending ? "Opening…" : `Open ${leverage}x Position`}
                </Button>
              </DialogFooter>
            </form>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
