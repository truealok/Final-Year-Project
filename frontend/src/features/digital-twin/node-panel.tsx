import { StatusBadge } from "@/components/common/status-badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { NetworkNode } from "@/types";
import { derivedHealth, derivedLeadTime } from "@/utils/derived";
import { formatNumber, titleCase } from "@/utils/format";

interface NodePanelProps {
  node: NetworkNode | null;
  onClose: () => void;
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

/** Slide-over showing full details for the clicked network node. */
export function NodePanel({ node, onClose }: NodePanelProps) {
  const health = node ? derivedHealth(node.id) : 0;

  return (
    <Sheet open={node !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-md">
        {node && (
          <>
            <SheetHeader>
              <SheetTitle>{node.name}</SheetTitle>
              <SheetDescription>
                {titleCase(node.type)}
                {node.city ? ` · ${node.city}` : ""}
                {node.country ? `, ${node.country}` : ""}
              </SheetDescription>
            </SheetHeader>

            <div className="mt-4 flex items-center gap-2">
              <StatusBadge value={node.status} />
              <StatusBadge value={node.risk_level} kind="risk" />
            </div>

            <Separator className="my-4" />

            <div className="space-y-0.5">
              {node.capacity !== null && (
                <DetailRow
                  label="Capacity"
                  value={`${formatNumber(node.capacity)} units${node.type === "factory" ? "/day" : ""}`}
                />
              )}
              {node.current_inventory !== null && (
                <DetailRow
                  label="Current inventory"
                  value={`${formatNumber(node.current_inventory)} units`}
                />
              )}
              {node.utilization_pct !== null && (
                <DetailRow
                  label="Utilization"
                  value={`${node.utilization_pct.toFixed(1)}%`}
                />
              )}
              <DetailRow
                label="Lead time"
                value={`${derivedLeadTime(node.id)} days`}
              />
              <DetailRow
                label="Current risk"
                value={<StatusBadge value={node.risk_level} kind="risk" showIcon={false} />}
              />
              <DetailRow
                label="Status"
                value={<StatusBadge value={node.status} showIcon={false} />}
              />
            </div>

            <Separator className="my-4" />

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Node health</span>
                <span className="text-sm font-medium tabular-nums">{health}%</span>
              </div>
              <Progress
                value={health}
                indicatorClassName={
                  health >= 80
                    ? "bg-success"
                    : health >= 60
                      ? "bg-warning"
                      : "bg-destructive"
                }
              />
              <p className="mt-2 text-xs text-muted-foreground">
                Composite of uptime, throughput and incident history
                (simulated until telemetry integration).
              </p>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
