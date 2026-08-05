import {
  Check,
  Download,
  Eye,
  Lightbulb,
  Loader2,
  RefreshCw,
  X,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { CardGridSkeleton } from "@/components/common/loading-skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { Pagination } from "@/components/common/pagination";
import { FilterBar } from "@/components/common/search-input";
import { StatusBadge } from "@/components/common/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useRecommendationMutations,
  useRecommendations,
} from "@/hooks/use-queries";
import type { Recommendation } from "@/types";
import { downloadCsv } from "@/utils/download";
import { formatCurrency, formatDate, titleCase } from "@/utils/format";

export default function RecommendationsPage() {
  const [page, setPage] = useState(1);
  const [priority, setPriority] = useState("all");
  const [status, setStatus] = useState("all");
  const [detail, setDetail] = useState<Recommendation | null>(null);

  const { data, isLoading } = useRecommendations({
    page,
    size: 9,
    priority: priority === "all" ? undefined : priority,
    status_filter: status === "all" ? undefined : status,
  });
  const { generate, updateStatus } = useRecommendationMutations();

  const exportAll = () => {
    const items = data?.items ?? [];
    if (items.length === 0) return;
    downloadCsv(
      [
        "title", "priority", "status", "confidence", "estimated_savings",
        "category", "suggested_action", "reason",
      ],
      items.map((r) => [
        r.title, r.priority, r.status, r.confidence, r.estimated_savings,
        r.category, r.suggested_action, r.reason,
      ]),
      "recommendations.csv",
    );
    toast.success("Recommendations exported.");
  };

  const setRecStatus = async (rec: Recommendation, next: "applied" | "dismissed") => {
    try {
      await updateStatus.mutateAsync({ id: rec.id, status: next });
      toast.success(next === "applied" ? "Recommendation applied." : "Recommendation dismissed.");
      setDetail(null);
    } catch {
      toast.error("Could not update recommendation.");
    }
  };

  return (
    <PageTransition>
      <PageHeader
        title="Recommendations"
        description="AI-suggested actions to reduce cost and improve resilience."
        breadcrumbs={[{ label: "Recommendations" }]}
        actions={
          <>
            <Button variant="outline" onClick={exportAll} disabled={!data?.items?.length}>
              <Download />
              Export
            </Button>
            <Button
              onClick={() =>
                generate.mutate(undefined, {
                  onSuccess: (created) =>
                    toast.success(`${created.length} new recommendations generated.`),
                })
              }
              disabled={generate.isPending}
            >
              {generate.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              Generate
            </Button>
          </>
        }
      />

      <FilterBar>
        <Select value={priority} onValueChange={(v) => { setPriority(v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priorities</SelectItem>
            {["critical", "high", "medium", "low"].map((p) => (
              <SelectItem key={p} value={p}>{titleCase(p)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {["pending", "applied", "dismissed"].map((s) => (
              <SelectItem key={s} value={s}>{titleCase(s)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterBar>

      {isLoading ? (
        <CardGridSkeleton count={6} />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          icon={Lightbulb}
          title="No recommendations"
          description="Generate a fresh batch of AI recommendations to get started."
          action={
            <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
              <RefreshCw />
              Generate recommendations
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(data?.items ?? []).map((rec) => (
              <Card key={rec.id} className="flex flex-col transition-shadow hover:shadow-card-hover">
                <CardContent className="flex flex-1 flex-col p-5">
                  <div className="flex items-start justify-between gap-2">
                    <StatusBadge value={rec.priority} kind="priority" showIcon={false} />
                    <Badge variant="muted">{titleCase(rec.category)}</Badge>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold leading-snug">{rec.title}</h3>
                  <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">
                    {rec.reason}
                  </p>

                  <div className="mt-4 space-y-2.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Expected savings</span>
                      <span className="font-semibold text-success">
                        {formatCurrency(rec.estimated_savings, true)}
                      </span>
                    </div>
                    <div>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Confidence</span>
                        <span className="font-medium tabular-nums">
                          {(rec.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Progress value={rec.confidence * 100} />
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Status</span>
                      <StatusBadge value={rec.status} showIcon={false} />
                    </div>
                  </div>

                  <div className="mt-4 flex gap-2 border-t pt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => setDetail(rec)}
                    >
                      <Eye />
                      View details
                    </Button>
                    {rec.status === "pending" && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-success hover:text-success"
                          onClick={() => setRecStatus(rec, "applied")}
                          aria-label="Apply"
                        >
                          <Check />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-muted-foreground"
                          onClick={() => setRecStatus(rec, "dismissed")}
                          aria-label="Dismiss"
                        >
                          <X />
                        </Button>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <Pagination
            page={data?.page ?? 1}
            pages={data?.pages ?? 1}
            total={data?.total ?? 0}
            onPageChange={setPage}
          />
        </>
      )}

      {/* Detail dialog */}
      <Dialog open={detail !== null} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent>
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle>{detail.title}</DialogTitle>
                <DialogDescription>
                  {titleCase(detail.category)} · created {formatDate(detail.created_at)}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge value={detail.priority} kind="priority" />
                  <StatusBadge value={detail.status} />
                  <Badge variant="muted">
                    {(detail.confidence * 100).toFixed(0)}% confidence
                  </Badge>
                  <Badge variant="success">
                    {formatCurrency(detail.estimated_savings, true)} est. savings
                  </Badge>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Suggested action
                  </p>
                  <p className="mt-1">{detail.suggested_action}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Reason
                  </p>
                  <p className="mt-1">{detail.reason}</p>
                </div>
              </div>
              {detail.status === "pending" && (
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setRecStatus(detail, "dismissed")}
                  >
                    <X />
                    Dismiss
                  </Button>
                  <Button onClick={() => setRecStatus(detail, "applied")}>
                    <Check />
                    Apply recommendation
                  </Button>
                </DialogFooter>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </PageTransition>
  );
}
