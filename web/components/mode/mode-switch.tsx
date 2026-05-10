"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
  currentMode: "paper" | "live";
}

export function ModeSwitch({ currentMode }: Props) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const qc = useQueryClient();

  const targetMode = currentMode === "paper" ? "live" : "paper";
  const needsConfirm = targetMode === "live";

  const mutation = useMutation({
    mutationFn: () => api.setMode(targetMode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meta"] });
      toast.success(`Switched to ${targetMode.toUpperCase()} mode`);
      setOpen(false);
      setConfirm("");
    },
    onError: (e: Error) => toast.error(`Mode switch failed: ${e.message}`),
  });

  const canConfirm = !needsConfirm || confirm === "LIVE";

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-xs font-semibold px-2 py-0.5 rounded transition-opacity hover:opacity-80"
        style={{
          background: currentMode === "live" ? "#F6465D22" : "#0ECB8122",
          color: currentMode === "live" ? "#F6465D" : "#0ECB81",
        }}
      >
        {currentMode.toUpperCase()}
      </button>

      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setConfirm(""); }}>
        <DialogContent className="bg-surface border-subtle max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm">Switch to {targetMode.toUpperCase()} mode</DialogTitle>
          </DialogHeader>

          <div className="space-y-3 text-xs text-muted">
            {targetMode === "live" ? (
              <>
                <p className="text-foreground">
                  Live mode places <strong>real orders</strong> on exchanges using your API keys.
                  Make sure your keys are configured and you understand the risks.
                </p>
                <ul className="space-y-1 list-disc list-inside">
                  <li>Real funds at risk — no simulated fills</li>
                  <li>Exchange fees apply on every open/close</li>
                  <li>Ensure API keys have trading permissions</li>
                </ul>
                <div>
                  <label className="block mb-1 text-muted">Type <strong className="text-foreground">LIVE</strong> to confirm</label>
                  <Input
                    autoFocus
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    className="bg-surface-2 border-subtle font-mono h-8 text-sm"
                    placeholder="LIVE"
                    onKeyDown={(e) => e.key === "Enter" && canConfirm && mutation.mutate()}
                  />
                </div>
              </>
            ) : (
              <p className="text-foreground">Switch back to PAPER mode? Live positions will remain open on exchanges — you&apos;ll need to close them manually.</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              disabled={!canConfirm || mutation.isPending}
              onClick={() => mutation.mutate()}
              style={canConfirm ? { background: targetMode === "live" ? "#F6465D" : "#0ECB81", color: "#000" } : {}}
            >
              {mutation.isPending ? "Switching…" : `Switch to ${targetMode.toUpperCase()}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
