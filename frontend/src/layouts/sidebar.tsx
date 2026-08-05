import { Boxes } from "lucide-react";
import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "@/layouts/nav-items";
import { cn } from "@/lib/utils";
import { useAlertSummary } from "@/hooks/use-queries";

interface SidebarNavProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

/** Brand block shown at the top of the sidebar. */
export function BrandMark({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex h-14 items-center gap-2.5 border-b px-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Boxes className="h-5 w-5" />
      </div>
      {!collapsed && (
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-semibold">ResiliChain AI</p>
          <p className="truncate text-[11px] text-muted-foreground">
            Supply Chain Intelligence
          </p>
        </div>
      )}
    </div>
  );
}

/** Navigation list used by both the desktop sidebar and the mobile drawer. */
export function SidebarNav({ collapsed = false, onNavigate }: SidebarNavProps) {
  const { data: alertSummary } = useAlertSummary();
  const unread = alertSummary?.unread ?? 0;

  return (
    <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          title={collapsed ? label : undefined}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
              isActive && "bg-primary/10 text-primary hover:bg-primary/10 hover:text-primary",
              collapsed && "justify-center px-2",
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" />
          {!collapsed && <span className="flex-1 truncate">{label}</span>}
          {!collapsed && label === "Alerts" && unread > 0 && (
            <span className="rounded-full bg-destructive px-1.5 py-0.5 text-[10px] font-semibold leading-none text-destructive-foreground">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

interface SidebarProps {
  collapsed: boolean;
}

/** Desktop sidebar (hidden below lg; the topbar opens a drawer instead). */
export function Sidebar({ collapsed }: SidebarProps) {
  return (
    <aside
      className={cn(
        "hidden shrink-0 flex-col border-r bg-card transition-[width] duration-200 lg:flex",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <BrandMark collapsed={collapsed} />
      <SidebarNav collapsed={collapsed} />
      {!collapsed && (
        <div className="border-t p-3 text-[11px] leading-relaxed text-muted-foreground">
          <p className="font-medium text-foreground">ResiliChain AI v1.0</p>
          <p>Forecasting &amp; resilience platform</p>
        </div>
      )}
    </aside>
  );
}
