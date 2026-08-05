import { Loader2, MapPin, Pencil, Plus, Trash2, Truck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { CardGridSkeleton } from "@/components/common/loading-skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { Pagination } from "@/components/common/pagination";
import { FilterBar, SearchInput } from "@/components/common/search-input";
import { StatusBadge } from "@/components/common/status-badge";
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
import { useAuth } from "@/hooks/use-auth";
import { useDebounce } from "@/hooks/use-debounce";
import { useSupplierMutations, useSuppliers } from "@/hooks/use-queries";
import { ApiError } from "@/services/api";
import type { EntityStatus, RiskLevel, Supplier } from "@/types";
import { RISK_LEVELS } from "@/utils/constants";
import { titleCase } from "@/utils/format";

interface FormState {
  name: string;
  country: string;
  city: string;
  contact_email: string;
  reliability_score: number;
  lead_time_days: number;
  risk_level: RiskLevel;
  status: EntityStatus;
}

const EMPTY_FORM: FormState = {
  name: "",
  country: "",
  city: "",
  contact_email: "",
  reliability_score: 85,
  lead_time_days: 7,
  risk_level: "medium",
  status: "active",
};

export default function SuppliersPage() {
  const { hasRole } = useAuth();
  const canEdit = hasRole("admin", "supply_chain_manager");

  const [page, setPage] = useState(1);
  const [riskFilter, setRiskFilter] = useState("all");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useSuppliers({
    page,
    size: 9,
    risk_level: riskFilter === "all" ? undefined : riskFilter,
    search: debouncedSearch || undefined,
  });
  const { create, update, remove } = useSupplierMutations();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (supplier: Supplier) => {
    setEditing(supplier);
    setForm({
      name: supplier.name,
      country: supplier.country,
      city: supplier.city ?? "",
      contact_email: supplier.contact_email ?? "",
      reliability_score: supplier.reliability_score,
      lead_time_days: supplier.lead_time_days,
      risk_level: supplier.risk_level,
      status: supplier.status,
    });
    setDialogOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const payload = {
      ...form,
      city: form.city || null,
      contact_email: form.contact_email || null,
    };
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, data: payload });
        toast.success("Supplier updated.");
      } else {
        await create.mutateAsync(payload);
        toast.success("Supplier created.");
      }
      setDialogOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Save failed.");
    }
  };

  const onDelete = async (supplier: Supplier) => {
    if (!window.confirm(`Delete supplier "${supplier.name}"?`)) return;
    try {
      await remove.mutateAsync(supplier.id);
      toast.success("Supplier deleted.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Delete failed.");
    }
  };

  return (
    <PageTransition>
      <PageHeader
        title="Suppliers"
        description="Supplier network with reliability, lead time and risk profile."
        breadcrumbs={[{ label: "Suppliers" }]}
        actions={
          canEdit && (
            <Button onClick={openCreate}>
              <Plus />
              Add supplier
            </Button>
          )
        }
      />

      <FilterBar>
        <SearchInput
          value={search}
          onChange={(v) => { setSearch(v); setPage(1); }}
          placeholder="Search suppliers…"
          className="w-full sm:w-72"
        />
        <Select value={riskFilter} onValueChange={(v) => { setRiskFilter(v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="Risk level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All risk levels</SelectItem>
            {RISK_LEVELS.map((risk) => (
              <SelectItem key={risk} value={risk}>{titleCase(risk)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterBar>

      {isLoading ? (
        <CardGridSkeleton count={9} />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          icon={Truck}
          title="No suppliers found"
          description="Adjust your filters or add a new supplier."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(data?.items ?? []).map((supplier) => (
              <Card key={supplier.id} className="transition-shadow hover:shadow-card-hover">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold">{supplier.name}</h3>
                      <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                        <MapPin className="h-3 w-3" />
                        {supplier.city ? `${supplier.city}, ` : ""}
                        {supplier.country}
                      </p>
                    </div>
                    <StatusBadge value={supplier.status} showIcon={false} />
                  </div>

                  <div className="mt-4">
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Reliability</span>
                      <span className="font-medium tabular-nums">
                        {supplier.reliability_score.toFixed(1)}%
                      </span>
                    </div>
                    <Progress
                      value={supplier.reliability_score}
                      indicatorClassName={
                        supplier.reliability_score >= 90
                          ? "bg-success"
                          : supplier.reliability_score >= 75
                            ? "bg-primary"
                            : "bg-warning"
                      }
                    />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground">Lead time</p>
                      <p className="font-medium">{supplier.lead_time_days} days</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Risk</p>
                      <StatusBadge value={supplier.risk_level} kind="risk" showIcon={false} />
                    </div>
                  </div>

                  {canEdit && (
                    <div className="mt-4 flex justify-end gap-1 border-t pt-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEdit(supplier)}
                      >
                        <Pencil />
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => onDelete(supplier)}
                      >
                        <Trash2 />
                        Delete
                      </Button>
                    </div>
                  )}
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

      {/* Create / edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Edit supplier" : "Add supplier"}</DialogTitle>
            <DialogDescription>
              {editing ? editing.name : "Register a new supplier in the network."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="country">Country</Label>
                <Input
                  id="country"
                  required
                  value={form.country}
                  onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  value={form.city}
                  onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="email">Contact email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.contact_email}
                  onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="reliability">Reliability (0–100)</Label>
                <Input
                  id="reliability"
                  type="number"
                  min={0}
                  max={100}
                  step="0.1"
                  value={form.reliability_score}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, reliability_score: Number(e.target.value) || 0 }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="leadTime">Lead time (days)</Label>
                <Input
                  id="leadTime"
                  type="number"
                  min={0}
                  max={365}
                  value={form.lead_time_days}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, lead_time_days: Number(e.target.value) || 0 }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label>Risk level</Label>
                <Select
                  value={form.risk_level}
                  onValueChange={(v) => setForm((f) => ({ ...f, risk_level: v as RiskLevel }))}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {RISK_LEVELS.map((risk) => (
                      <SelectItem key={risk} value={risk}>{titleCase(risk)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Status</Label>
                <Select
                  value={form.status}
                  onValueChange={(v) => setForm((f) => ({ ...f, status: v as EntityStatus }))}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {(["active", "inactive", "disrupted", "maintenance"] as const).map((s) => (
                      <SelectItem key={s} value={s}>{titleCase(s)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending || update.isPending}>
                {(create.isPending || update.isPending) && <Loader2 className="animate-spin" />}
                {editing ? "Save changes" : "Create supplier"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageTransition>
  );
}
