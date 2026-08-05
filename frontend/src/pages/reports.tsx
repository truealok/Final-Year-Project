import {
  FileSpreadsheet,
  FileText,
  FileType,
  Loader2,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { TableSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { Pagination } from "@/components/common/pagination";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { useReportMutations, useReports } from "@/hooks/use-queries";
import { ReportApi } from "@/services/endpoints";
import { ApiError } from "@/services/api";
import type { ReportType } from "@/types";
import { downloadBlob } from "@/utils/download";
import { formatDateTime, titleCase } from "@/utils/format";

const REPORT_TYPES: { type: ReportType; title: string; description: string }[] = [
  {
    type: "forecast",
    title: "Forecast Report",
    description: "Recent forecast runs with models, ranges and accuracy.",
  },
  {
    type: "simulation",
    title: "Simulation Report",
    description: "Disruption scenarios with resilience and cost outcomes.",
  },
  {
    type: "inventory",
    title: "Inventory Report",
    description: "Stock positions, values and status per warehouse.",
  },
  {
    type: "risk",
    title: "Risk Report",
    description: "Supplier risk profile and alert distribution.",
  },
];

export default function ReportsPage() {
  const { hasRole } = useAuth();
  const canDelete = hasRole("admin", "supply_chain_manager");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useReports({ page, size: 10 });
  const { generate, remove } = useReportMutations();
  const [generating, setGenerating] = useState<ReportType | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);

  const onGenerate = async (type: ReportType) => {
    setGenerating(type);
    try {
      await generate.mutateAsync(type);
      toast.success(`${titleCase(type)} report generated.`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Generation failed.");
    } finally {
      setGenerating(null);
    }
  };

  const onExport = async (
    reportId: string,
    reportName: string,
    format: "csv" | "pdf",
    excel = false,
  ) => {
    setExporting(`${reportId}:${format}${excel ? ":xlsx" : ""}`);
    try {
      const response = await ReportApi.exportFile(reportId, format);
      const blob = await response.blob();
      const safeName = reportName.replace(/\s+/g, "_").toLowerCase();
      downloadBlob(blob, `${safeName}.${format}`);
      toast.success(
        excel
          ? "Exported as CSV (opens directly in Excel)."
          : `Exported as ${format.toUpperCase()}.`,
      );
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Export failed.");
    } finally {
      setExporting(null);
    }
  };

  const onDelete = async (reportId: string, name: string) => {
    if (!window.confirm(`Delete report "${name}"?`)) return;
    try {
      await remove.mutateAsync(reportId);
      toast.success("Report deleted.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Delete failed.");
    }
  };

  return (
    <PageTransition>
      <PageHeader
        title="Reports"
        description="Generate and export operational reports."
        breadcrumbs={[{ label: "Reports" }]}
      />

      {/* Generators */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {REPORT_TYPES.map((report) => (
          <Card key={report.type} className="flex flex-col">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-primary" />
                {report.title}
              </CardTitle>
              <CardDescription className="text-xs">
                {report.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="mt-auto">
              <Button
                size="sm"
                className="w-full"
                onClick={() => onGenerate(report.type)}
                disabled={generating !== null}
              >
                {generating === report.type && <Loader2 className="animate-spin" />}
                Generate
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Generated reports */}
      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Generated Reports</CardTitle>
          <CardDescription className="text-xs">
            Export any report as PDF, CSV, or Excel-compatible CSV.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={5} />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="hidden sm:table-cell">Type</TableHead>
                    <TableHead className="hidden md:table-cell">Status</TableHead>
                    <TableHead className="hidden md:table-cell">Created</TableHead>
                    <TableHead className="text-right">Export</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(data?.items ?? []).map((report) => (
                    <TableRow key={report.id}>
                      <TableCell className="font-medium">{report.name}</TableCell>
                      <TableCell className="hidden sm:table-cell">
                        {titleCase(report.report_type)}
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <StatusBadge value={report.status} showIcon={false} />
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted-foreground md:table-cell">
                        {formatDateTime(report.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            disabled={exporting !== null}
                            onClick={() => onExport(report.id, report.name, "pdf")}
                            title="Export PDF"
                          >
                            {exporting === `${report.id}:pdf` ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <FileType className="h-3.5 w-3.5" />
                            )}
                            PDF
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            disabled={exporting !== null}
                            onClick={() => onExport(report.id, report.name, "csv")}
                            title="Export CSV"
                          >
                            {exporting === `${report.id}:csv` ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <FileText className="h-3.5 w-3.5" />
                            )}
                            CSV
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            disabled={exporting !== null}
                            onClick={() => onExport(report.id, report.name, "csv", true)}
                            title="Excel-compatible CSV"
                          >
                            {exporting === `${report.id}:csv:xlsx` ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <FileSpreadsheet className="h-3.5 w-3.5" />
                            )}
                            Excel
                          </Button>
                          {canDelete && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-destructive"
                              onClick={() => onDelete(report.id, report.name)}
                              aria-label="Delete report"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {(data?.items ?? []).length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="py-10 text-center text-muted-foreground"
                      >
                        No reports yet — generate one above.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              <Pagination
                page={data?.page ?? 1}
                pages={data?.pages ?? 1}
                total={data?.total ?? 0}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </PageTransition>
  );
}
