"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, History, Settings, ChevronLeft, ChevronRight, X,
} from "lucide-react";
import { useUiStore } from "@/stores/ui-store";

const NAV = [
  { href: "/",         label: "Dashboard", Icon: LayoutDashboard },
  { href: "/history",  label: "History",   Icon: History },
  { href: "/settings", label: "Settings",  Icon: Settings },
];

function NavItem({
  href, label, Icon, collapsed,
}: { href: string; label: string; Icon: React.ElementType; collapsed: boolean }) {
  const pathname = usePathname();
  const active = pathname === href;
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-3 py-2 rounded text-xs transition-colors ${
        active
          ? "bg-accent text-foreground font-semibold"
          : "text-muted hover:text-foreground hover:bg-accent/50"
      }`}
      title={collapsed ? label : undefined}
    >
      <Icon size={16} className="shrink-0" />
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden whitespace-nowrap"
          >
            {label}
          </motion.span>
        )}
      </AnimatePresence>
    </Link>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, setSidebarCollapsed } = useUiStore();

  return (
    <motion.aside
      animate={{ width: sidebarCollapsed ? 52 : 180 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="flex flex-col shrink-0 border-r border-subtle bg-surface overflow-hidden hidden lg:flex"
    >
      <nav className="flex-1 px-2 py-3 space-y-1">
        {NAV.map(({ href, label, Icon }) => (
          <NavItem key={href} href={href} label={label} Icon={Icon} collapsed={sidebarCollapsed} />
        ))}
      </nav>

      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="flex items-center justify-center h-10 text-muted hover:text-foreground border-t border-subtle transition-colors"
        title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </motion.aside>
  );
}

export function MobileSidebarOverlay() {
  const { mobileSidebarOpen, setMobileSidebarOpen } = useUiStore();

  return (
    <AnimatePresence>
      {mobileSidebarOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-40 lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <motion.aside
            initial={{ x: -200 }}
            animate={{ x: 0 }}
            exit={{ x: -200 }}
            transition={{ duration: 0.2 }}
            className="fixed left-0 top-0 bottom-0 w-48 bg-surface border-r border-subtle z-50 flex flex-col lg:hidden"
          >
            <div className="flex items-center justify-between px-4 h-12 border-b border-subtle">
              <span className="font-bold text-yellow text-sm">Crypto Funding Arb Bot</span>
              <button onClick={() => setMobileSidebarOpen(false)} className="text-muted hover:text-foreground">
                <X size={16} />
              </button>
            </div>
            <nav className="flex-1 px-2 py-3 space-y-1">
              {NAV.map(({ href, label, Icon }) => (
                <NavItem
                  key={href} href={href} label={label} Icon={Icon} collapsed={false}
                />
              ))}
            </nav>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
