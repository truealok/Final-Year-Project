import { useMemo } from "react";

import { ChartCard } from "@/components/common/chart-card";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { SimpleBarChart } from "@/components/charts/bar-chart";
import { DonutChart } from "@/components/charts/donut-chart";
import { RiskHeatmap } from "@/components/charts/risk-heatmap";
import { TrendChart } from "@/components/charts/trend-chart";
import { useAnalytics } from "@/hooks/use-queries";
import { formatCurrency, formatMonthKey, formatPercent } from "@/utils/format";

/**
 * Cost breakdown shares (static mock until a cost service exists in the
 * backend) applied to a total derived from live warehouse/inventory data.
 */
const COST_SHARES = [
  { name: "Procurement", share: 0.38 },
  { name: "Transportation", share: 0.24 },
  { name: "Warehousing", share: 0.18 },
  { name: "Inventory holding", share: 0.12 },
  { name: "Expedited freight", share: 0.08 },
];

const RISK_BASE: Record<string, number> = {
  low: 0.2,
  medium: 0.45,
  high: 0.68,
  critical: 0.85,
};

export default function AnalyticsPage() {
  const { data, isLoading } = useAnalytics();

  const monthly = (points: { period: string; value: number }[] | undefined, key: string) =>
    (points ?? []).map((p) => ({ period: formatMonthKey(p.period), [key]: p.value }));

  const demand = useMemo(() => monthly(data?.demand_trend, "demand"), [data]);
  const inventory = useMemo(() => monthly(data?.inventory_trend, "units"), [data]);
  const disruptions = useMemo(
    () => monthly(data?.disruption_frequency, "events"),
    [data],
  );
  const recovery = useMemo(() => monthly(data?.recovery_trend, "days"), [data]);
  const carbon = useMemo(() => monthly(data?.carbon_emissions, "tons"), [data]);

  const supplierBars = useMemo(
    () =>
      (data?.supplier_performance ?? []).slice(0, 8).map((s) => ({
        name: s.name.length > 18 ? `${s.name.slice(0, 17)}…` : s.name,
        reliability: s.reliability_score,
      })),
    [data],
  );

  const utilizationBars = useMemo(
    () =>
      (data?.warehouse_utilization ?? []).map((w) => ({
        name: w.name.replace(" Distribution Center", ""),
        utilization: w.utilization_pct,
      })),
    [data],
  );

  const costTotal = useMemo(() => {
    const units = data?.inventory_trend?.at(-1)?.value ?? 500_000;
    return units * 14; // blended cost per unit (mock)
  }, [data]);

  const costBreakdown = COST_SHARES.map((c) => ({
    name: c.name,
    value: Math.round(costTotal * c.share),
  }));

  const heatmapEntities = (data?.supplier_performance ?? [])
    .slice(0, 8)
    .map((s) => ({
      id: s.id,
      name: s.name,
      baseRisk: RISK_BASE[s.risk_level] ?? 0.4,
    }));

  return (
    <PageTransition>
      <PageHeader
        title="Analytics"
        description="Cross-network performance, risk and sustainability trends."
        breadcrumbs={[{ label: "Analytics" }]}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="Demand Trend"
          description="Monthly demand across all products (last 12 months)"
          loading={isLoading}
        >
          <TrendChart data={demand} series={[{ key: "demand", label: "Units" }]} kind="area" />
        </ChartCard>

        <ChartCard
          title="Inventory Trend"
          description="Network-wide inventory position"
          loading={isLoading}
        >
          <TrendChart data={inventory} series={[{ key: "units", label: "Units" }]} />
        </ChartCard>

        <ChartCard
          title="Supplier Performance"
          description="Reliability score of top suppliers (values labeled per bar)"
          loading={isLoading}
          height={300}
        >
          <SimpleBarChart
            data={supplierBars}
            xKey="name"
            yKey="reliability"
            yLabel="Reliability"
            layout="vertical"
            valueFormatter={(v) => formatPercent(v, 0)}
          />
        </ChartCard>

        <ChartCard
          title="Warehouse Utilization"
          description="Capacity used per distribution center"
          loading={isLoading}
          height={300}
        >
          <SimpleBarChart
            data={utilizationBars}
            xKey="name"
            yKey="utilization"
            yLabel="Utilization"
            layout="vertical"
            valueFormatter={(v) => formatPercent(v, 0)}
          />
        </ChartCard>

        <ChartCard
          title="Risk Heatmap"
          description="Supplier risk exposure by factor (hover a cell for the value)"
          loading={isLoading}
          height={320}
        >
          <RiskHeatmap entities={heatmapEntities} />
        </ChartCard>

        <ChartCard
          title="Cost Breakdown"
          description={`Estimated supply chain cost base · ${formatCurrency(costTotal, true)}`}
          loading={isLoading}
          height={320}
        >
          <DonutChart
            data={costBreakdown}
            valueFormatter={(v) => formatCurrency(v, true)}
          />
        </ChartCard>

        <ChartCard
          title="Disruption Frequency"
          description="Disruption events per month"
          loading={isLoading}
        >
          <SimpleBarChart
            data={disruptions}
            xKey="period"
            yKey="events"
            yLabel="Events"
            valueFormatter={(v) => String(Math.round(v))}
          />
        </ChartCard>

        <ChartCard
          title="Recovery Trend"
          description="Average recovery time after disruption (days)"
          loading={isLoading}
        >
          <TrendChart
            data={recovery}
            series={[{ key: "days", label: "Days" }]}
            valueFormatter={(v) => `${v.toFixed(1)}d`}
          />
        </ChartCard>

        <ChartCard
          title="Carbon Emissions"
          description="Logistics CO₂ footprint (tons per month)"
          loading={isLoading}
          className="xl:col-span-2"
        >
          <TrendChart
            data={carbon}
            series={[{ key: "tons", label: "Tons CO₂" }]}
            kind="area"
          />
        </ChartCard>
      </div>
    </PageTransition>
  );
}
