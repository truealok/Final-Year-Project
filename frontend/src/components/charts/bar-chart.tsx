import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  axisProps,
  gridProps,
  tooltipContentStyle,
  tooltipLabelStyle,
} from "@/components/charts/chart-theme";
import { formatCompact } from "@/utils/format";

interface SimpleBarChartProps {
  data: Record<string, string | number>[];
  xKey: string;
  yKey: string;
  yLabel: string;
  layout?: "horizontal" | "vertical";
  valueFormatter?: (value: number) => string;
  /** Optional per-datum color override (e.g. utilization thresholds). */
  colorFor?: (row: Record<string, string | number>) => string;
}

/**
 * Single-series bar chart (one series -> one color, slot 1; a value ramp on
 * nominal categories is an anti-pattern). Rounded 4px data ends, thin bars.
 */
export function SimpleBarChart({
  data,
  xKey,
  yKey,
  yLabel,
  layout = "horizontal",
  valueFormatter = formatCompact,
  colorFor,
}: SimpleBarChartProps) {
  const isVertical = layout === "vertical";
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        layout={isVertical ? "vertical" : "horizontal"}
        margin={{ top: 8, right: 8, bottom: 0, left: isVertical ? 8 : 0 }}
        barCategoryGap="28%"
      >
        <CartesianGrid
          {...gridProps}
          horizontal={!isVertical}
          vertical={isVertical}
        />
        {isVertical ? (
          <>
            <XAxis
              type="number"
              {...axisProps}
              tickFormatter={(v: number) => valueFormatter(v)}
            />
            <YAxis
              type="category"
              dataKey={xKey}
              {...axisProps}
              width={110}
              interval={0}
            />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} {...axisProps} minTickGap={16} />
            <YAxis
              {...axisProps}
              width={44}
              tickFormatter={(v: number) => valueFormatter(v)}
            />
          </>
        )}
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          cursor={{ fill: "var(--chart-grid)", opacity: 0.35 }}
          formatter={(value: number | string) => [
            valueFormatter(Number(value)),
            yLabel,
          ]}
        />
        <Bar
          dataKey={yKey}
          name={yLabel}
          fill="var(--chart-1)"
          maxBarSize={isVertical ? 14 : 28}
          radius={isVertical ? [0, 4, 4, 0] : [4, 4, 0, 0]}
        >
          {colorFor &&
            data.map((row, i) => <Cell key={i} fill={colorFor(row)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
