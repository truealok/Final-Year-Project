import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  axisProps,
  CHART_COLORS,
  gridProps,
  legendStyle,
  tooltipContentStyle,
  tooltipLabelStyle,
} from "@/components/charts/chart-theme";
import { formatCompact } from "@/utils/format";

export interface SeriesDef {
  key: string;
  label: string;
}

interface TrendChartProps {
  data: Record<string, string | number>[];
  /** X-axis key (default "period"). */
  xKey?: string;
  series: SeriesDef[];
  kind?: "line" | "area";
  valueFormatter?: (value: number) => string;
}

/**
 * Line/area chart for one or more time series. A legend renders automatically
 * for two or more series (identity never rides on color alone).
 */
export function TrendChart({
  data,
  xKey = "period",
  series,
  kind = "line",
  valueFormatter = formatCompact,
}: TrendChartProps) {
  const Chart = kind === "area" ? AreaChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <Chart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey={xKey} {...axisProps} minTickGap={24} />
        <YAxis
          {...axisProps}
          width={44}
          tickFormatter={(v: number) => valueFormatter(v)}
        />
        <Tooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          formatter={(value: number | string, name: string) => [
            valueFormatter(Number(value)),
            name,
          ]}
          cursor={{ stroke: "var(--chart-axis)", strokeWidth: 1 }}
        />
        {series.length > 1 && <Legend wrapperStyle={legendStyle} iconSize={10} />}
        {series.map((s, i) =>
          kind === "area" ? (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              fill={CHART_COLORS[i % CHART_COLORS.length]}
              fillOpacity={0.12}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ) : (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ),
        )}
      </Chart>
    </ResponsiveContainer>
  );
}
