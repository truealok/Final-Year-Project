import {
  Activity,
  ArrowRight,
  Bell,
  Boxes,
  Clock,
  DollarSign,
  FileText,
  Leaf,
  Lightbulb,
  Network,
  PackageX,
  ShieldAlert,
  ShieldCheck,
  Target,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";

import { ChartCard } from "@/components/common/chart-card";
import { KpiCard } from "@/components/common/kpi-card";
import { KpiSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader, SectionHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { StatusBadge } from "@/components/common/status-badge";
import { TrendChart } from "@/components/charts/trend-chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import {
  useAlertSummary,
  useAnalytics,
  useDashboard,
  useRecommendations,
} from "@/hooks/use-queries";
import {
  formatCompact,
  formatCurrency,
  formatDateTime,
  formatMonthKey,
  formatPercent,
  formatProbability,
  formatRelative,
  titleCase,
} from "@/utils/format";

const QUICK_ACTIONS = [
  { to: "/simulation", label: "Run simulation", icon: ShieldAlert },
  { to: "/forecast", label: "New forecast", icon: TrendingUp },
  { to: "/digital-twin", label: "View network", icon: Network },
  { to: "/reports", label: "Generate report", icon: FileText },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: dashboard, isLoading } = useDashboard();
  const { data: analytics, isLoading: analyticsLoading } = useAnalytics();
  const { data: alertSummary } = useAlertSummary();
  const { data: recommendations } = useRecommendations({ page: 1, size: 4 });

  const demandTrend = (analytics?.demand_trend ?? []).map((p) => ({
    period: formatMonthKey(p.period),
    demand: p.value,
  }));
  const inventoryTrend = (analytics?.inventory_trend ?? []).map((p) => ({
    period: formatMonthKey(p.period),
    units: p.value,
  }));
  const riskTrend = (analytics?.disruption_frequency ?? []).map((p) => ({
    period: formatMonthKey(p.period),
    disruptions: p.value,
  }));

  return (
    <PageTransition>
      <PageHeader
        title={`Welcome back, ${user?.full_name?.split(" ")[0] ?? "there"}`}
        description="Operational snapshot of your supply chain network."
        actions={
          <Button asChild>
            <Link to="/simulation">
              Run simulation
              <ArrowRight />
            </Link>
          </Button>
        }
      />

      {/* KPI grid */}
      {isLoading || !dashboard ? (
        <KpiSkeleton count={8} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            index={0}
            label="Forecast Accuracy"
            value={formatPercent(dashboard.forecast_accuracy)}
            icon={Target}
            delta={1.8}
            hint="vs last period"
          />
          <KpiCard
            index={1}
            label="Resilience Score"
            value={`${dashboard.resilience_score.toFixed(1)} / 100`}
            icon={ShieldCheck}
            delta={dashboard.resilience_score >= 70 ? 2.4 : -3.1}
            hint="network-wide"
          />
          <KpiCard
            index={2}
            label="Expected Cost"
            value={formatCurrency(dashboard.expected_cost, true)}
            icon={DollarSign}
            delta={-2.2}
            positiveIsGood={false}
            hint="disruption exposure"
          />
          <KpiCard
            index={3}
            label="Stockout Probability"
            value={formatProbability(dashboard.stockout_probability)}
            icon={PackageX}
            delta={-0.8}
            positiveIsGood={false}
            hint="next 30 days"
          />
          <KpiCard
            index={4}
            label="Recovery Time"
            value={`${dashboard.recovery_time_days.toFixed(1)} days`}
            icon={Clock}
            delta={-4.6}
            positiveIsGood={false}
            hint="avg. recent scenarios"
          />
          <KpiCard
            index={5}
            label="Active Disruptions"
            value={String(alertSummary?.critical ?? 0)}
            icon={Activity}
            hint={`${alertSummary?.unread ?? 0} unread alerts`}
          />
          <KpiCard
            index={6}
            label="Current Inventory"
            value={formatCompact(dashboard.current_inventory.total_units)}
            icon={Boxes}
            hint={formatCurrency(dashboard.current_inventory.total_value, true)}
          />
          <KpiCard
            index={7}
            label="Carbon Emissions"
            value={`${formatCompact(dashboard.carbon_emissions.total_tons_co2)} t`}
            icon={Leaf}
            delta={dashboard.carbon_emissions.change_pct}
            positiveIsGood={false}
            hint="CO₂ this period"
          />
        </div>
      )}

      {/* Trend charts */}
      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <ChartCard
          title="Demand Trend"
          description="Monthly demand across all products"
          loading={analyticsLoading}
          height={240}
        >
          <TrendChart
            data={demandTrend}
            series={[{ key: "demand", label: "Units" }]}
            kind="area"
          />
        </ChartCard>
        <ChartCard
          title="Inventory Trend"
          description="Total network inventory position"
          loading={analyticsLoading}
          height={240}
        >
          <TrendChart
            data={inventoryTrend}
            series={[{ key: "units", label: "Units" }]}
          />
        </ChartCard>
        <ChartCard
          title="Risk Trend"
          description="Disruption events per month"
          loading={analyticsLoading}
          height={240}
        >
          <TrendChart
            data={riskTrend}
            series={[{ key: "disruptions", label: "Disruptions" }]}
          />
        </ChartCard>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        {/* Latest recommendations */}
        <Card className="xl:col-span-1">
          <CardContent className="p-5">
            <SectionHeader
              title="Latest Recommendations"
              actions={
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/recommendations">
                    View all
                    <ArrowRight />
                  </Link>
                </Button>
              }
            />
            <ul className="space-y-3">
              {(recommendations?.items ?? []).map((rec) => (
                <li key={rec.id} className="rounded-md border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium leading-tight">
                      {rec.title}
                    </p>
                    <StatusBadge value={rec.priority} kind="priority" showIcon={false} />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Est. savings {formatCurrency(rec.estimated_savings, true)} ·{" "}
                    {(rec.confidence * 100).toFixed(0)}% confidence
                  </p>
                </li>
              ))}
              {(recommendations?.items ?? []).length === 0 && (
                <li className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted-foreground">
                  <Lightbulb className="h-5 w-5" />
                  No recommendations yet.
                </li>
              )}
            </ul>
          </CardContent>
        </Card>

        {/* Recent alerts */}
        <Card className="xl:col-span-1">
          <CardContent className="p-5">
            <SectionHeader
              title="Recent Alerts"
              actions={
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/alerts">
                    View all
                    <ArrowRight />
                  </Link>
                </Button>
              }
            />
            <ul className="space-y-3">
              {(dashboard?.latest_alerts ?? []).map((alert) => (
                <li key={alert.id} className="flex items-start gap-3">
                  <StatusBadge value={alert.severity} kind="severity" showIcon />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{alert.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatRelative(alert.created_at)}
                    </p>
                  </div>
                </li>
              ))}
              {(dashboard?.latest_alerts ?? []).length === 0 && (
                <li className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted-foreground">
                  <Bell className="h-5 w-5" />
                  No alerts.
                </li>
              )}
            </ul>
          </CardContent>
        </Card>

        {/* Quick actions + recent simulations */}
        <Card className="xl:col-span-1">
          <CardContent className="p-5">
            <SectionHeader title="Quick Actions" />
            <div className="grid grid-cols-2 gap-2">
              {QUICK_ACTIONS.map(({ to, label, icon: Icon }) => (
                <Button
                  key={to}
                  variant="outline"
                  className="h-auto flex-col gap-1.5 py-3"
                  asChild
                >
                  <Link to={to}>
                    <Icon className="h-4 w-4 text-primary" />
                    <span className="text-xs">{label}</span>
                  </Link>
                </Button>
              ))}
            </div>
            <SectionHeader title="Recent Simulations" />
            <ul className="space-y-2.5">
              {(dashboard?.recent_simulations ?? []).slice(0, 4).map((sim) => (
                <li
                  key={sim.id}
                  className="flex items-center justify-between gap-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {titleCase(sim.simulation_type)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(sim.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {sim.resilience_score.toFixed(0)}/100
                    </span>
                    <StatusBadge value={sim.risk_level} kind="risk" showIcon={false} />
                  </div>
                </li>
              ))}
              {(dashboard?.recent_simulations ?? []).length === 0 && (
                <li className="py-4 text-center text-sm text-muted-foreground">
                  No simulations run yet.
                </li>
              )}
            </ul>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
