import { Download, Loader2, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ChartCard } from "@/components/common/chart-card";
import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { FilterBar } from "@/components/common/search-input";
import { ForecastChart } from "@/components/charts/forecast-chart";
import { TrendChart } from "@/components/charts/trend-chart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  useAnalytics,
  useForecastHistory,
  useForecastModels,
  usePredictForecast,
  useProducts,
  useWarehouses,
} from "@/hooks/use-queries";
import { ApiError } from "@/services/api";
import type { ForecastModel, ForecastPredictResponse } from "@/types";
import { FORECAST_MODELS } from "@/utils/constants";
import { downloadCsv } from "@/utils/download";
import { formatDate, formatMonthKey, titleCase } from "@/utils/format";

function isoDatePlus(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export default function ForecastPage() {
  const { data: products } = useProducts({ page: 1, size: 100 });
  const { data: warehouses } = useWarehouses({ page: 1, size: 100 });
  const { data: models } = useForecastModels();
  const { data: analytics, isLoading: analyticsLoading } = useAnalytics();
  const { data: history } = useForecastHistory({ page: 1, size: 8 });
  const predict = usePredictForecast();

  const [productId, setProductId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [model, setModel] = useState<ForecastModel>("prophet");
  const [startDate, setStartDate] = useState(isoDatePlus(1));
  const [endDate, setEndDate] = useState(isoDatePlus(30));
  const [result, setResult] = useState<ForecastPredictResponse | null>(null);

  const historicalDemand = useMemo(
    () =>
      (analytics?.demand_trend ?? []).map((p) => ({
        period: formatMonthKey(p.period),
        demand: p.value,
      })),
    [analytics],
  );

  const runForecast = async () => {
    if (!productId || !warehouseId) {
      toast.error("Select a product and a warehouse first.");
      return;
    }
    try {
      const response = await predict.mutateAsync({
        product_id: productId,
        warehouse_id: warehouseId,
        start_date: startDate,
        end_date: endDate,
        model,
      });
      setResult(response);
      toast.success(`Forecast generated with ${titleCase(response.model_used)}.`);
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Forecast failed.",
      );
    }
  };

  const downloadForecast = () => {
    if (!result) return;
    downloadCsv(
      ["date", "predicted_demand", "lower_bound", "upper_bound"],
      result.points.map((p) => [
        p.date,
        p.predicted_demand,
        p.lower_bound,
        p.upper_bound,
      ]),
      `forecast_${result.forecast_id.slice(0, 8)}.csv`,
    );
  };

  return (
    <PageTransition>
      <PageHeader
        title="Demand Forecast"
        description="Predict product demand per warehouse with confidence intervals."
        breadcrumbs={[{ label: "Forecast" }]}
        actions={
          <Button
            variant="outline"
            onClick={downloadForecast}
            disabled={!result}
          >
            <Download />
            Download forecast
          </Button>
        }
      />

      {/* Filter / parameter row */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <FilterBar className="mb-0 items-end">
            <div className="w-full space-y-1 sm:w-56">
              <Label className="text-xs">Product</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select product" />
                </SelectTrigger>
                <SelectContent>
                  {(products?.items ?? []).map((product) => (
                    <SelectItem key={product.id} value={product.id}>
                      {product.sku} · {product.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full space-y-1 sm:w-52">
              <Label className="text-xs">Warehouse</Label>
              <Select value={warehouseId} onValueChange={setWarehouseId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select warehouse" />
                </SelectTrigger>
                <SelectContent>
                  {(warehouses?.items ?? []).map((warehouse) => (
                    <SelectItem key={warehouse.id} value={warehouse.id}>
                      {warehouse.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full space-y-1 sm:w-40">
              <Label className="text-xs">From</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </div>
            <div className="w-full space-y-1 sm:w-40">
              <Label className="text-xs">To</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </div>
            <div className="w-full space-y-1 sm:w-36">
              <Label className="text-xs">Model</Label>
              <Select
                value={model}
                onValueChange={(value) => setModel(value as ForecastModel)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FORECAST_MODELS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              onClick={runForecast}
              disabled={predict.isPending}
              className="w-full sm:w-auto"
            >
              {predict.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <TrendingUp />
              )}
              Run forecast
            </Button>
          </FilterBar>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="Historical Demand"
          description="Aggregated monthly demand (sales history)"
          loading={analyticsLoading}
          height={300}
        >
          <TrendChart
            data={historicalDemand}
            series={[{ key: "demand", label: "Units" }]}
            kind="area"
          />
        </ChartCard>

        <ChartCard
          title="Forecast"
          description={
            result
              ? `${titleCase(result.model_used)} · ${formatDate(result.prediction_date)} · ${(result.confidence_level * 100).toFixed(0)}% interval`
              : "Run a forecast to see predictions"
          }
          height={300}
        >
          {result ? (
            <ForecastChart points={result.points} />
          ) : (
            <div className="flex h-full items-center justify-center">
              <EmptyState
                icon={TrendingUp}
                title="No forecast yet"
                description="Choose a product, warehouse and date range, then run a forecast."
              />
            </div>
          )}
        </ChartCard>
      </div>

      {/* Model comparison */}
      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Model Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">MAPE</TableHead>
                <TableHead className="text-right">RMSE</TableHead>
                <TableHead className="text-right">MAE</TableHead>
                <TableHead className="hidden md:table-cell">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(models ?? []).map((m) => (
                <TableRow key={m.name}>
                  <TableCell className="font-medium">{m.display_name}</TableCell>
                  <TableCell>
                    <Badge variant={m.status === "available" ? "success" : "secondary"}>
                      {titleCase(m.status)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {m.metrics.mape.toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {m.metrics.rmse.toFixed(1)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {m.metrics.mae.toFixed(1)}
                  </TableCell>
                  <TableCell className="hidden max-w-md text-xs text-muted-foreground md:table-cell">
                    {m.description}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* History */}
      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Recent Forecast Runs</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead className="hidden sm:table-cell">Warehouse</TableHead>
                <TableHead>Model</TableHead>
                <TableHead className="hidden md:table-cell">Range</TableHead>
                <TableHead className="text-right">MAPE</TableHead>
                <TableHead className="hidden sm:table-cell">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(history?.items ?? []).map((run) => (
                <TableRow key={run.id}>
                  <TableCell className="font-medium">
                    {run.product.sku}
                    <span className="hidden text-muted-foreground lg:inline">
                      {" "}
                      · {run.product.name}
                    </span>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">
                    {run.warehouse.name}
                  </TableCell>
                  <TableCell>{titleCase(run.model_used)}</TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground md:table-cell">
                    {formatDate(run.start_date)} → {formatDate(run.end_date)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {typeof run.metrics.mape === "number"
                      ? `${run.metrics.mape.toFixed(1)}%`
                      : "—"}
                  </TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                    {formatDate(run.created_at)}
                  </TableCell>
                </TableRow>
              ))}
              {(history?.items ?? []).length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-8 text-center text-muted-foreground"
                  >
                    No forecast runs yet.
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
