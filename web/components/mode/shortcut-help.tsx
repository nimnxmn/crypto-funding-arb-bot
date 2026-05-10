"use client";
import { useUiStore } from "@/stores/ui-store";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

const SHORTCUTS = [
  { key: "/",   description: "Focus scanner filter" },
  { key: "O",   description: "Open trade modal (top opportunity)" },
  { key: "?",   description: "Show this help" },
  { key: "Esc", description: "Close any open modal" },
];

export function ShortcutHelp() {
  const { shortcutHelpOpen, setShortcutHelpOpen } = useUiStore();

  return (
    <Dialog open={shortcutHelpOpen} onOpenChange={setShortcutHelpOpen}>
      <DialogContent className="bg-surface border-subtle max-w-xs">
        <DialogHeader>
          <DialogTitle className="text-sm">Keyboard Shortcuts</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          {SHORTCUTS.map(({ key, description }) => (
            <div key={key} className="flex items-center justify-between text-xs">
              <span className="text-muted">{description}</span>
              <kbd className="px-2 py-0.5 rounded bg-surface-2 border border-subtle font-mono text-foreground">
                {key}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
