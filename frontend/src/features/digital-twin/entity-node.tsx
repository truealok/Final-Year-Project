import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { Factory, Store, Truck, Warehouse } from "lucide-react";

import { cn } from "@/lib/utils";
import type { NetworkNode } from "@/types";

export type EntityNodeData = { entity: NetworkNode };
export type EntityFlowNode = Node<EntityNodeData, "entity">;

const TYPE_ICON = {
  supplier: Truck,
  factory: Factory,
  warehouse: Warehouse,
  retail_store: Store,
} as const;

const TYPE_LABEL = {
  supplier: "Supplier",
  factory: "Factory",
  warehouse: "Warehouse",
  retail_store: "Retail Store",
} as const;

const RISK_DOT = {
  low: "bg-success",
  medium: "bg-warning",
  high: "bg-destructive",
  critical: "bg-destructive",
} as const;

/** Custom React Flow node rendering a supply chain entity as a mini card. */
export function EntityNode({ data, selected }: NodeProps<EntityFlowNode>) {
  const { entity } = data;
  const Icon = TYPE_ICON[entity.type];

  return (
    <div
      className={cn(
        "w-44 rounded-md border bg-card px-3 py-2 shadow-card transition-shadow",
        selected && "ring-2 ring-primary",
        entity.status === "disrupted" && "border-destructive/60",
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2 !w-2 !border-border !bg-muted-foreground"
      />
      <div className="flex items-center gap-2">
        <div className="rounded bg-primary/10 p-1 text-primary">
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold leading-tight">
            {entity.name}
          </p>
          <p className="text-[10px] text-muted-foreground">
            {TYPE_LABEL[entity.type]}
          </p>
        </div>
        <span
          className={cn("h-2 w-2 shrink-0 rounded-full", RISK_DOT[entity.risk_level])}
          title={`Risk: ${entity.risk_level}`}
        />
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2 !w-2 !border-border !bg-muted-foreground"
      />
    </div>
  );
}
