import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import {
  CHART_COLORS,
  legendStyle,
  tooltipContentStyle,
} from "@/components/charts/chart-theme";

interface DonutChartProps {
  data: { name: string; value: number }[];
  valueFormatter?: (value: number) => string;
}

/**
 * Part-to-whole donut (<= 6 segments, glance-level only). Segments carry a
 * 2px surface gap; the legend carries identity.
 */
export function DonutChart({
  data,
  valueFormatter = (v) => String(v),
}: DonutChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data.slice(0, 6)}
          dataKey="value"
          nameKey="name"
          innerRadius="55%"
          outerRadius="80%"
          paddingAngle={2}
          stroke="hsl(var(--card))"
          strokeWidth={2}
        >
          {data.slice(0, 6).map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={tooltipContentStyle}
          formatter={(value: number | string, name: string) => [
            valueFormatter(Number(value)),
            name,
          ]}
        />
        <Legend
          wrapperStyle={legendStyle}
          iconSize={10}
          layout="horizontal"
          verticalAlign="bottom"
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
