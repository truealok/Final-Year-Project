import type { ReactNode } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  loading?: boolean;
  className?: string;
  /** Height of the chart area in px (container includes the axis band). */
  height?: number;
  children: ReactNode;
}

/** Card wrapper for charts with a consistent header and loading state. */
export function ChartCard({
  title,
  description,
  actions,
  loading = false,
  className,
  height = 280,
  children,
}: ChartCardProps) {
  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="flex-row items-start justify-between space-y-0 pb-3">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
        {actions}
      </CardHeader>
      <CardContent className="flex-1">
        {loading ? (
          <Skeleton style={{ height }} className="w-full" />
        ) : (
          <div style={{ height }} className="w-full">
            {children}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
