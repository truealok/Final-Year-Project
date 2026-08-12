import { Loader2, Play, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useNetwork,
  useRunSimulation,
  useSimulationHistory,
} from "@/hooks/use-queries";
import { ApiError } from "@/services/api";
import type {
  SeverityLevel,
  SimulationResult,
  SimulationType,
} from "@/types";
import { SEVERITY_LEVELS, SIMULATION_TYPES } from "@/utils/constants";
import {
  formatCurrency,
  formatDateTime,
  formatProbability,
  titleCase,
} from "@/utils/format";

export default function SimulationPage() {
  const { data: network } = useNetwork();
  const { data: history } = useSimulationHistory({ page: 1, size: 10 });
  const run = useRunSimulation();

  const [type, setType] = useState<SimulationType>("supplier_failure");
  const [severity, setSeverity] = useState<SeverityLevel>("medium");
  const [duration, setDuration] = useState(7);
  const [probability, setProbability] = useState(0.5);
  const [monteCarloRuns, setMonteCarloRuns] = useState(500);
  const [affectedNodeId, setAffectedNodeId] = useState<string>("any");
  const [result, setResult] = useState<SimulationResult | null>(null);

  const nodes = network?.nodes ?? [];

  const runSimulation = async () => {
    try {
      const node = nodes.find((n) => n.id === affectedNodeId);
      const response = await run.mutateAsync({
        simulation_type: type,
        severity,
        duration_days: duration,
        probability,
        affected_node_id: node ? node.id : null,
        affected_node_type: node ? node.type : null,
        monte_carlo_runs: monteCarloRuns,
      });
      setResult(response);
      toast.success("Simulation complete.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Simulation failed.",
      );
    }
  };

  const resilienceTone =
    result && result.resilience_score >= 70
      ? "bg-success"
      : result && result.resilience_score >= 45
        ? "bg-warning"
        : "bg-destructive";

  return (
    <PageTransition>
      <PageHeader
        title="Disruption Simulation"
        description="Stress-test the network against what-if disruption scenarios."
        breadcrumbs={[{ label: "Simulation" }]}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {/* Control panel */}
        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Scenario Builder</CardTitle>
            <CardDescription>
              Configure the disruption and run the simulation engine.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Disruption type</Label>
              <Select
                value={type}
                onValueChange={(value) => setType(value as SimulationType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SIMULATION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Severity</Label>
              <Select
                value={severity}
                onValueChange={(value) => setSeverity(value as SeverityLevel)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITY_LEVELS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="duration">Duration (days)</Label>
                <Input
                  id="duration"
                  type="number"
                  min={1}
                  max={365}
                  value={duration}
                  onChange={(event) =>
                    setDuration(Math.max(1, Number(event.target.value) || 1))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="probability">Probability</Label>
                <Input
                  id="probability"
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={probability}
                  onChange={(event) =>
                    setProbability(
                      Math.min(1, Math.max(0, Number(event.target.value) || 0)),
                    )
                  }
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Affected node</Label>
              <Select value={affectedNodeId} onValueChange={setAffectedNodeId}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Highest-impact node (auto)</SelectItem>
                  {nodes.slice(0, 60).map((node) => (
                    <SelectItem key={node.id} value={node.id}>
                      {node.name} · {titleCase(node.type)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="mc-runs">Monte Carlo runs</Label>
              <Select
                value={String(monteCarloRuns)}
                onValueChange={(value) => setMonteCarloRuns(Number(value))}
              >
                <SelectTrigger id="mc-runs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="100">100 · fastest, noisier</SelectItem>
                  <SelectItem value="500">500 · balanced</SelectItem>
                  <SelectItem value="1000">1000 · most stable</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              className="w-full"
              onClick={runSimulation}
              disabled={run.isPending}
            >
              {run.isPending ? <Loader2 className="animate-spin" /> : <Play />}
              Run simulation
            </Button>
            <p className="text-xs text-muted-foreground">
              Monte Carlo over the digital-twin network: demand statistics
              come from the real sales history; network parameters
              (capacities, lead times, routes) are configured values.
            </p>
          </CardContent>
        </Card>

        {/* Results */}
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Simulation Results</CardTitle>
            {result && (
              <CardDescription>
                {titleCase(result.simulation_type)} · {titleCase(result.severity)}{" "}
                severity · {result.duration_days} days
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {!result ? (
              <EmptyState
                icon={ShieldAlert}
                title="No simulation results"
                description="Configure a disruption scenario on the left and run the simulation."
              />
            ) : (
              <div className="space-y-6">
                {/* Score tiles */}
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Resilience Score
                    </p>
                    <p className="mt-0.5 text-2xl font-semibold">
                      {result.resilience_score.toFixed(1)}
                      <span className="text-sm text-muted-foreground"> /100</span>
                    </p>
                    <Progress
                      value={result.resilience_score}
                      className="mt-2"
                      indicatorClassName={resilienceTone}
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Expected Cost</p>
                    <p className="mt-0.5 text-2xl font-semibold">
                      {formatCurrency(result.expected_cost, true)}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      disruption exposure
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Stockout Probability
                    </p>
                    <p className="mt-0.5 text-2xl font-semibold">
                      {formatProbability(result.stockout_probability)}
                    </p>
                    <Progress
                      value={result.stockout_probability * 100}
                      className="mt-2"
                      indicatorClassName="bg-destructive"
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Recovery Time</p>
                    <p className="mt-0.5 text-2xl font-semibold">
                      {result.recovery_time_days.toFixed(1)}
                      <span className="text-sm text-muted-foreground"> days</span>
                    </p>
                    <div className="mt-1">
                      <StatusBadge value={result.risk_level} kind="risk" />
                    </div>
                  </div>
                </div>

                {/* Monte Carlo engine extras */}
                {typeof result.service_level === "number" && (
                  <div className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-lg border bg-muted/40 px-4 py-2.5 text-sm">
                    <span>
                      <span className="text-muted-foreground">Service level </span>
                      <span className="font-semibold tabular-nums">
                        {(result.service_level * 100).toFixed(1)}%
                      </span>
                      {typeof result.baseline_service_level === "number" && (
                        <span className="text-muted-foreground">
                          {" "}
                          vs {(result.baseline_service_level * 100).toFixed(1)}%
                          baseline
                        </span>
                      )}
                    </span>
                    {typeof result.emissions_tons_co2 === "number" && (
                      <span>
                        <span className="text-muted-foreground">Emissions </span>
                        <span className="font-semibold tabular-nums">
                          {result.emissions_tons_co2.toFixed(1)} t CO₂
                        </span>
                      </span>
                    )}
                    {typeof result.n_runs === "number" && (
                      <span className="text-xs text-muted-foreground">
                        {result.n_runs} Monte Carlo runs
                      </span>
                    )}
                  </div>
                )}

                {/* Affected nodes & routes */}
                <div className="grid gap-4 lg:grid-cols-2">
                  <div>
                    <p className="mb-2 text-sm font-semibold">Affected Nodes</p>
                    <ul className="space-y-2">
                      {result.affected_nodes.map((node, index) => (
                        <li
                          key={`${node.name}-${index}`}
                          className="flex items-center gap-3 rounded-md border p-2.5"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">
                              {node.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {titleCase(node.type)}
                            </p>
                          </div>
                          <div className="w-28">
                            <Progress
                              value={node.impact_pct}
                              indicatorClassName="bg-warning"
                            />
                          </div>
                          <span className="w-12 text-right text-xs tabular-nums text-muted-foreground">
                            {node.impact_pct.toFixed(0)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="mb-2 text-sm font-semibold">Affected Routes</p>
                    <ul className="space-y-2">
                      {result.affected_routes.map((route, index) => (
                        <li
                          key={`${route.name}-${index}`}
                          className="flex items-center justify-between gap-2 rounded-md border p-2.5"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium">
                              {route.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {titleCase(route.transport_mode)} · +
                              {route.delay_hours.toFixed(0)}h delay
                            </p>
                          </div>
                          <StatusBadge
                            value={
                              route.status === "suspended"
                                ? "disrupted"
                                : "maintenance"
                            }
                            showIcon={false}
                          />
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* History */}
      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Simulation History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scenario</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead className="text-right">Resilience</TableHead>
                <TableHead className="hidden text-right sm:table-cell">
                  Cost
                </TableHead>
                <TableHead className="hidden text-right md:table-cell">
                  Stockout
                </TableHead>
                <TableHead>Risk</TableHead>
                <TableHead className="hidden sm:table-cell">Run at</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(history?.items ?? []).map((sim) => (
                <TableRow key={sim.id}>
                  <TableCell className="font-medium">
                    {titleCase(sim.simulation_type)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      value={sim.severity}
                      kind="priority"
                      showIcon={false}
                    />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {sim.resilience_score.toFixed(1)}
                  </TableCell>
                  <TableCell className="hidden text-right tabular-nums sm:table-cell">
                    {formatCurrency(sim.expected_cost, true)}
                  </TableCell>
                  <TableCell className="hidden text-right tabular-nums md:table-cell">
                    {formatProbability(sim.stockout_probability)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge value={sim.risk_level} kind="risk" showIcon={false} />
                  </TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                    {formatDateTime(sim.created_at)}
                  </TableCell>
                </TableRow>
              ))}
              {(history?.items ?? []).length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="py-8 text-center text-muted-foreground"
                  >
                    No simulations yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </PageTransition>
  );
}
