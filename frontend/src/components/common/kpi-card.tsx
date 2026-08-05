import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  /** Signed percentage, e.g. -3.2 renders "3.2%" with a down arrow. */
  delta?: number;
  /** Whether a positive delta is good (default) or bad (e.g. cost). */
  positiveIsGood?: boolean;
  hint?: string;
  index?: number;
}

/** Single KPI stat tile with an optional trend delta. */
export function KpiCard({
  label,
  value,
  icon: Icon,
  delta,
  positiveIsGood = true,
  hint,
  index = 0,
}: KpiCardProps) {
  const isUp = (delta ?? 0) >= 0;
  const isGood = positiveIsGood ? isUp : !isUp;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.04, ease: "easeOut" }}
    >
      <Card className="transition-shadow hover:shadow-card-hover">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <div className="rounded-md bg-primary/10 p-1.5 text-primary">
              <Icon className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
          <div className="mt-1 flex items-center gap-1.5 text-xs">
            {delta !== undefined && (
              <span
                className={cn(
                  "inline-flex items-center gap-0.5 font-medium",
                  isGood ? "text-success" : "text-destructive",
                )}
              >
                {isUp ? (
                  <ArrowUpRight className="h-3.5 w-3.5" />
                ) : (
                  <ArrowDownRight className="h-3.5 w-3.5" />
                )}
                {Math.abs(delta).toFixed(1)}%
              </span>
            )}
            {hint && <span className="text-muted-foreground">{hint}</span>}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
