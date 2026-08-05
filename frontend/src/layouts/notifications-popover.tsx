import { Bell, CheckCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { useAlertMutations, useAlerts, useAlertSummary } from "@/hooks/use-queries";
import { formatRelative } from "@/utils/format";

/** Topbar bell: unread count badge + latest alerts preview. */
export function NotificationsPopover() {
  const { data: summary } = useAlertSummary();
  const { data: alerts } = useAlerts({ page: 1, size: 5 });
  const { markAllRead } = useAlertMutations();
  const unread = summary?.unread ?? 0;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => markAllRead.mutate()}
            disabled={unread === 0 || markAllRead.isPending}
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </Button>
        </div>
        <Separator />
        <ul className="max-h-80 overflow-y-auto">
          {(alerts?.items ?? []).map((alert) => (
            <li
              key={alert.id}
              className="border-b px-4 py-3 last:border-0 hover:bg-muted/50"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium leading-tight">
                  {alert.title}
                </p>
                {!alert.is_read && (
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                )}
              </div>
              <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                {alert.message}
              </p>
              <div className="mt-1.5 flex items-center gap-2">
                <StatusBadge value={alert.severity} kind="severity" />
                <span className="text-[11px] text-muted-foreground">
                  {formatRelative(alert.created_at)}
                </span>
              </div>
            </li>
          ))}
          {(alerts?.items ?? []).length === 0 && (
            <li className="px-4 py-8 text-center text-sm text-muted-foreground">
              No notifications.
            </li>
          )}
        </ul>
        <Separator />
        <Link
          to="/alerts"
          className="block px-4 py-2.5 text-center text-xs font-medium text-primary hover:underline"
        >
          View all alerts
        </Link>
      </PopoverContent>
    </Popover>
  );
}
