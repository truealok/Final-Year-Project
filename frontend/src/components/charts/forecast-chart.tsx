import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  axisProps,
  gridProps,
  legendStyle,
  tooltipContentStyle,
  tooltipLabelStyle,
} from "@/components/charts/chart-theme";
import type { ForecastPoint } from "@/types";
import { formatCompact } from "@/utils/format";

interface ForecastChartProps {
  points: ForecastPoint[];
}

/**
 * Forecast line with its confidence interval as a range band (same hue at
 * low opacity — the band is the same series' uncertainty, not a second
 * series).
 */
export function ForecastChart({ points }: ForecastChartProps) {
  const data = points.map((p) => ({
    date: p.date.slice(5), // MM-DD
    predicted: p.predicted_demand,
    band: [p.lower_bound, p.upper_bound] as [number, number],
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="date" {...axisProps} minTickGap={28} />
        <YAxis
          {...axisProps}
          width={44}
          tickFormatter={(v: number) => formatCompact(v)}
        />
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          formatter={(value: number | string | number[], name: string) => {
            if (Array.isArray(value)) {
              return [
                `${formatCompact(value[0])} – ${formatCompact(value[1])}`,
                "95% interval",
              ];
            }
            return [formatCompact(Number(value)), name];
          }}
          cursor={{ stroke: "var(--chart-axis)", strokeWidth: 1 }}
        />
        <Legend wrapperStyle={legendStyle} iconSize={10} />
        <Area
          dataKey="band"
          name="95% interval"
          stroke="none"
          fill="var(--chart-1)"
          fillOpacity={0.14}
          activeDot={false}
        />
        <Line
          dataKey="predicted"
          name="Predicted demand"
          type="monotone"
          stroke="var(--chart-1)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
