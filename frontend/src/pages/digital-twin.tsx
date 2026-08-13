import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { StatusBadge } from "@/components/common/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import {
  EntityNode,
  type EntityFlowNode,
} from "@/features/digital-twin/entity-node";
import { NodePanel } from "@/features/digital-twin/node-panel";
import { useNetwork } from "@/hooks/use-queries";
import { useTheme } from "@/hooks/use-theme";
import type { NetworkNode, NodeType } from "@/types";
import { formatNumber, titleCase } from "@/utils/format";

const nodeTypes = { entity: EntityNode };

const COLUMN_ORDER: NodeType[] = [
  "supplier",
  "factory",
  "warehouse",
  "retail_store",
];
const COLUMN_X = 280;
const ROW_Y = 92;

const EDGE_COLOR: Record<string, string> = {
  low: "#94a3b8",
  medium: "#f59e0b",
  high: "#dc2626",
  critical: "#dc2626",
};

export default function DigitalTwinPage() {
  const { data: network, isLoading } = useNetwork();
  const { resolvedTheme } = useTheme();
  const [selected, setSelected] = useState<NetworkNode | null>(null);

  const { flowNodes, flowEdges } = useMemo(() => {
    const nodes = network?.nodes ?? [];
    const byType = new Map<NodeType, NetworkNode[]>(
      COLUMN_ORDER.map((type) => [type, []]),
    );
    for (const node of nodes) byType.get(node.type)?.push(node);

    const tallest = Math.max(
      1,
      ...COLUMN_ORDER.map((type) => byType.get(type)?.length ?? 0),
    );

    const flowNodes: EntityFlowNode[] = [];
    COLUMN_ORDER.forEach((type, columnIndex) => {
      const column = byType.get(type) ?? [];
      const offsetY = ((tallest - column.length) * ROW_Y) / 2;
      column.forEach((entity, rowIndex) => {
        flowNodes.push({
          id: entity.id,
          type: "entity",
          position: {
            x: columnIndex * COLUMN_X,
            y: offsetY + rowIndex * ROW_Y,
          },
          data: { entity },
        });
      });
    });

    const flowEdges: Edge[] = (network?.edges ?? []).map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      animated: edge.status === "disrupted",
      style: {
        stroke: EDGE_COLOR[edge.risk_level] ?? "#94a3b8",
        strokeWidth: 1.5,
        opacity: edge.status === "disrupted" ? 0.9 : 0.55,
      },
    }));

    return { flowNodes, flowEdges };
  }, [network]);

  const onNodeClick: NodeMouseHandler = (_event, node) => {
    const entity = (node.data as { entity?: NetworkNode }).entity;
    if (entity) setSelected(entity);
  };

  const summary = network?.summary;

  return (
    <PageTransition>
      <PageHeader
        title="Digital Twin"
        description="Interactive live model of your end-to-end supply chain network."
        breadcrumbs={[{ label: "Digital Twin" }]}
      />

      {/* Summary strip */}
      {summary && (
        <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border bg-card px-4 py-3 text-sm">
          <span>
            <span className="font-semibold">{formatNumber(summary.total_nodes)}</span>{" "}
            <span className="text-muted-foreground">nodes</span>
          </span>
          <span>
            <span className="font-semibold">{formatNumber(summary.total_edges)}</span>{" "}
            <span className="text-muted-foreground">routes</span>
          </span>
          <span>
            <span className="font-semibold">
              {summary.resilience_score.toFixed(1)}
            </span>{" "}
            <span className="text-muted-foreground">resilience</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Overall risk</span>
            <StatusBadge value={summary.overall_risk} kind="risk" showIcon={false} />
          </span>
          <span className="ml-auto hidden text-xs text-muted-foreground lg:block">
            {COLUMN_ORDER.map(
              (type) =>
                `${summary.node_counts[type] ?? 0} ${titleCase(type)}s`,
            ).join(" · ")}
          </span>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <div className="h-[calc(100vh-320px)] min-h-[460px] w-full">
            {isLoading ? (
              <Skeleton className="h-full w-full rounded-lg" />
            ) : flowNodes.length === 0 ? (
              <div className="flex h-full items-center justify-center p-6">
                <EmptyState
                  icon={Network}
                  title="No network data"
                  description="Seed the backend database to populate the supply chain network."
                />
              </div>
            ) : (
              <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                nodeTypes={nodeTypes}
                onNodeClick={onNodeClick}
                fitView
                fitViewOptions={{ padding: 0.15 }}
                minZoom={0.2}
                maxZoom={1.6}
                nodesDraggable
                nodesConnectable={false}
                colorMode={resolvedTheme}
                proOptions={{ hideAttribution: false }}
              >
                <Background gap={20} size={1} />
                <Controls showInteractive={false} />
                <MiniMap
                  pannable
                  zoomable
                  className="!hidden md:!block"
                  nodeStrokeWidth={2}
                />
              </ReactFlow>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edge legend */}
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 rounded bg-[#94a3b8]" /> Low-risk
          route
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 rounded bg-[#f59e0b]" /> Medium
          risk
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 rounded bg-[#dc2626]" /> High /
          critical risk
        </span>
        <span>Animated edges are currently disrupted. Click a node for details.</span>
      </div>

      <NodePanel node={selected} onClose={() => setSelected(null)} />
    </PageTransition>
  );
}
