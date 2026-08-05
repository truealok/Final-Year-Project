/**
 * Shared chart styling following the dataviz method:
 * - categorical colors in fixed order (CVD-validated, never cycled)
 * - solid hairline gridlines, recessive axes, thin marks
 * - text in text tokens, never series colors
 */

export const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
] as const;

export const gridProps = {
  stroke: "var(--chart-grid)",
  strokeWidth: 1,
  vertical: false,
} as const;

export const axisProps = {
  stroke: "var(--chart-axis)",
  fontSize: 11,
  tickLine: false,
  axisLine: { stroke: "var(--chart-grid)" },
} as const;

export const tooltipContentStyle: React.CSSProperties = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
  color: "hsl(var(--foreground))",
  boxShadow: "0 2px 8px rgb(0 0 0 / 0.08)",
};

export const tooltipLabelStyle: React.CSSProperties = {
  color: "hsl(var(--muted-foreground))",
  fontSize: 11,
  marginBottom: 4,
};

export const legendStyle: React.CSSProperties = {
  fontSize: 12,
  color: "hsl(var(--muted-foreground))",
};
