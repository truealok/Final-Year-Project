import { Bell, Check, CheckCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { TableSkeleton } from "@/components/common/loading-skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { Pagination } from "@/components/common/pagination";
import { StatusBadge } from "@/components/common/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/hooks/use-auth";
import { useAlertMutations, useAlerts, useAlertSummary } from "@/hooks/use-queries";
import { cn } from "@/lib/utils";
import { formatRelative, titleCase } from "@/utils/format";

export default function AlertsPage() {
  const { hasRole } = useAuth();
  const canDelete = hasRole("admin", "supply_chain_manager");
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState("all");
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data: summary } = useAlertSummary();
  const { data, isLoading } = useAlerts({
    page,
    size: 12,
    severity: severity === "all" ? undefined : severity,
    unread_only: unreadOnly || undefined,
  });
  const { markRead, markAllRead, remove } = useAlertMutations();

  const tabCounts: Record<string, number | undefined> = {
    all: summary?.total,
    critical: summary?.critical,
    warning: summary?.warning,
    info: summary?.info,
  };

  return (
    <PageTransition>
      <PageHeader
        title="Alerts"
        description="Operational alerts from monitoring across the network."
        breadcrumbs={[{ label: "Alerts" }]}
        actions={
          <Button
            variant="outline"
            onClick={() =>
              markAllRead.mutate(undefined, {
                onSuccess: (res) => toast.success(res.message),
              })
            }
            disabled={(summary?.unread ?? 0) === 0 || markAllRead.isPending}
          >
            <CheckCheck />
            Mark all read
          </Button>
        }
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs
          value={severity}
          onValueChange={(value) => {
            setSeverity(value);
            setPage(1);
          }}
        >
          <TabsList>
            {(["all", "critical", "warning", "info"] as const).map((tab) => (
              <TabsTrigger key={tab} value={tab}>
                {titleCase(tab)}
                {tabCounts[tab] !== undefined && (
                  <Badge variant="muted" className="px-1.5 text-[10px]">
                    {tabCounts[tab]}
                  </Badge>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div className="flex items-center gap-2">
          <Switch
            id="unreadOnly"
            checked={unreadOnly}
            onCheckedChange={(checked) => {
              setUnreadOnly(checked);
              setPage(1);
            }}
          />
          <Label htmlFor="unreadOnly" className="text-sm text-muted-foreground">
            Unread only
          </Label>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4">
              <TableSkeleton rows={8} />
            </div>
          ) : (data?.items ?? []).length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={Bell}
                title="No alerts"
                description="Nothing matches the current filters."
              />
            </div>
          ) : (
            <ul>
              {(data?.items ?? []).map((alert) => (
                <li
                  key={alert.id}
                  className={cn(
                    "flex items-start gap-3 border-b px-4 py-3.5 last:border-0",
                    !alert.is_read && "bg-primary/[0.03]",
                  )}
                >
                  <StatusBadge value={alert.severity} kind="severity" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium">{alert.title}</p>
                      {!alert.is_read && (
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      )}
                    </div>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {alert.message}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {alert.source ? `${alert.source} · ` : ""}
                      {formatRelative(alert.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {!alert.is_read && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => markRead.mutate(alert.id)}
                        aria-label="Mark as read"
                        title="Mark as read"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {canDelete && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive"
                        onClick={() => {
                          if (window.confirm("Delete this alert?")) {
                            remove.mutate(alert.id);
                          }
                        }}
                        aria-label="Delete alert"
                        title="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Pagination
        page={data?.page ?? 1}
        pages={data?.pages ?? 1}
        total={data?.total ?? 0}
        onPageChange={setPage}
      />
    </PageTransition>
  );
}
