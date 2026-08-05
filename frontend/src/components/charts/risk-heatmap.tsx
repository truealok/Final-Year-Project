import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { stableFraction } from "@/utils/derived";

/**
 * Risk heatmap: entities x risk factors on a single-hue sequential ramp
 * (semantic heat, light -> dark red) with an explicit scale legend.
 * Values are also readable per-cell via tooltip and title text.
 */

const FACTORS = ["Supply", "Logistics", "Demand", "Financial", "Geo"] as const;

// Single-hue red ramp, light -> dark (sequential = magnitude).
const RAMP = ["#fee2e2", "#fca5a5", "#f87171", "#dc2626", "#7f1d1d"] as const;
const RAMP_DARK = ["#450a0a", "#7f1d1d", "#b91c1c", "#ef4444", "#fca5a5"] as const;

interface RiskHeatmapProps {
  entities: { id: string; name: string; baseRisk: number }[]; // baseRisk 0..1
}

function riskValue(id: string, factor: string, base: number): number {
  const jitter = stableFraction(id, factor) * 0.5 - 0.25;
  return Math.min(0.99, Math.max(0.02, base + jitter));
}

function bucket(value: number): number {
  return Math.min(RAMP.length - 1, Math.floor(value * RAMP.length));
}

export function RiskHeatmap({ entities }: RiskHeatmapProps) {
  return (
    <TooltipProvider delayDuration={100}>
      <div className="flex h-full flex-col">
        <div className="grid flex-1 gap-1 overflow-x-auto">
          <div
            className="grid min-w-[420px] gap-1"
            style={{
              gridTemplateColumns: `minmax(96px, 1.4fr) repeat(${FACTORS.length}, 1fr)`,
            }}
          >
            <div />
            {FACTORS.map((factor) => (
              <div
                key={factor}
                className="pb-1 text-center text-[11px] font-medium text-muted-foreground"
              >
                {factor}
              </div>
            ))}
            {entities.map((entity) => (
              <RowCells key={entity.id} entity={entity} />
            ))}
          </div>
        </div>
        {/* Scale legend (sequential ramp always ships one) */}
        <div className="mt-3 flex items-center justify-end gap-2 text-[11px] text-muted-foreground">
          <span>Low</span>
          <div className="flex overflow-hidden rounded-sm">
            {RAMP.map((color, i) => (
              <span
                key={color}
                className="h-2.5 w-6 dark:hidden"
                style={{ backgroundColor: color }}
                aria-hidden
              />
            ))}
            {RAMP_DARK.map((color) => (
              <span
                key={color}
                className="hidden h-2.5 w-6 dark:block"
                style={{ backgroundColor: color }}
                aria-hidden
              />
            ))}
          </div>
          <span>High</span>
        </div>
      </div>
    </TooltipProvider>
  );
}

function RowCells({
  entity,
}: {
  entity: { id: string; name: string; baseRisk: number };
}) {
  return (
    <>
      <div className="truncate pr-2 text-xs leading-6" title={entity.name}>
        {entity.name}
      </div>
      {FACTORS.map((factor) => {
        const value = riskValue(entity.id, factor, entity.baseRisk);
        const idx = bucket(value);
        return (
          <Tooltip key={factor}>
            <TooltipTrigger asChild>
              <div
                role="img"
                aria-label={`${entity.name} · ${factor}: ${(value * 100).toFixed(0)}%`}
                className="h-6 cursor-default rounded-sm border-2 border-card"
              >
                <div
                  className="h-full w-full rounded-[2px] dark:hidden"
                  style={{ backgroundColor: RAMP[idx] }}
                />
                <div
                  className="hidden h-full w-full rounded-[2px] dark:block"
                  style={{ backgroundColor: RAMP_DARK[idx] }}
                />
              </div>
            </TooltipTrigger>
            <TooltipContent>
              {entity.name} · {factor}: {(value * 100).toFixed(0)}% risk
            </TooltipContent>
          </Tooltip>
        );
      })}
    </>
  );
}
