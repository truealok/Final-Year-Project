import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Loader2,
  MapPin,
  Pencil,
  Plus,
  Trash2,
  Warehouse as WarehouseIcon,
} from "lucide-react";
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
import { useWarehouseMutations, useWarehouses } from "@/hooks/use-queries";
import { ApiError } from "@/services/api";
import type { EntityStatus, Warehouse } from "@/types";
import { derivedIncoming, derivedOutgoing } from "@/utils/derived";
import { formatNumber, titleCase } from "@/utils/format";

interface FormState {
  name: string;
  country: string;
  city: string;
  capacity: number;
  status: EntityStatus;
}

const EMPTY_FORM: FormState = {
  name: "",
  country: "",
  city: "",
  capacity: 100_000,
  status: "active",
};

export default function WarehousesPage() {
  const { hasRole } = useAuth();
  const canEdit = hasRole("admin", "supply_chain_manager");

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useWarehouses({
    page,
    size: 9,
    search: debouncedSearch || undefined,
  });
  const { create, update, remove } = useWarehouseMutations();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Warehouse | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (warehouse: Warehouse) => {
    setEditing(warehouse);
    setForm({
      name: warehouse.name,
      country: warehouse.country,
      city: warehouse.city ?? "",
      capacity: warehouse.capacity,
      status: warehouse.status,
    });
    setDialogOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const payload = { ...form, city: form.city || null };
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, data: payload });
        toast.success("Warehouse updated.");
      } else {
        await create.mutateAsync(payload);
        toast.success("Warehouse created.");
      }
      setDialogOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Save failed.");
    }
  };

  const onDelete = async (warehouse: Warehouse) => {
    if (!window.confirm(`Delete warehouse "${warehouse.name}"?`)) return;
    try {
      await remove.mutateAsync(warehouse.id);
      toast.success("Warehouse deleted.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Delete failed.");
    }
  };

  return (
    <PageTransition>
      <PageHeader
        title="Warehouses"
        description="Distribution centers with capacity, utilization and flows."
        breadcrumbs={[{ label: "Warehouses" }]}
        actions={
          canEdit && (
            <Button onClick={openCreate}>
              <Plus />
              Add warehouse
            </Button>
          )
        }
      />

      <FilterBar>
        <SearchInput
          value={search}
          onChange={(v) => { setSearch(v); setPage(1); }}
          placeholder="Search warehouses…"
          className="w-full sm:w-72"
        />
      </FilterBar>

      {isLoading ? (
        <CardGridSkeleton count={9} />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          icon={WarehouseIcon}
          title="No warehouses found"
          description="Adjust your search or add a new warehouse."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(data?.items ?? []).map((warehouse) => {
              const incoming = derivedIncoming(warehouse.id, Math.round(warehouse.capacity * 0.02));
              const outgoing = derivedOutgoing(warehouse.id, warehouse.current_inventory);
              const utilization = warehouse.utilization_pct;
              return (
                <Card key={warehouse.id} className="transition-shadow hover:shadow-card-hover">
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold">{warehouse.name}</h3>
                        <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3" />
                          {warehouse.city ? `${warehouse.city}, ` : ""}
                          {warehouse.country}
                        </p>
                      </div>
                      <StatusBadge value={warehouse.status} showIcon={false} />
                    </div>

                    <div className="mt-4">
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Utilization</span>
                        <span className="font-medium tabular-nums">
                          {utilization.toFixed(1)}%
                        </span>
                      </div>
                      <Progress
                        value={Math.min(100, utilization)}
                        indicatorClassName={
                          utilization >= 90
                            ? "bg-destructive"
                            : utilization >= 70
                              ? "bg-warning"
                              : "bg-primary"
                        }
                      />
                      <p className="mt-1.5 text-xs text-muted-foreground">
                        {formatNumber(warehouse.current_inventory)} of{" "}
                        {formatNumber(warehouse.capacity)} units
                      </p>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                      <div className="flex items-center gap-2">
                        <ArrowDownToLine className="h-3.5 w-3.5 text-success" />
                        <div>
                          <p className="text-xs text-muted-foreground">Incoming</p>
                          <p className="font-medium tabular-nums">
                            {formatNumber(incoming)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <ArrowUpFromLine className="h-3.5 w-3.5 text-primary" />
                        <div>
                          <p className="text-xs text-muted-foreground">Outgoing/day</p>
                          <p className="font-medium tabular-nums">
                            {formatNumber(outgoing)}
                          </p>
                        </div>
                      </div>
                    </div>

                    {canEdit && (
                      <div className="mt-4 flex justify-end gap-1 border-t pt-3">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(warehouse)}>
                          <Pencil />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => onDelete(warehouse)}
                        >
                          <Trash2 />
                          Delete
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
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
            <DialogTitle>{editing ? "Edit warehouse" : "Add warehouse"}</DialogTitle>
            <DialogDescription>
              {editing ? editing.name : "Register a new distribution center."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="whName">Name</Label>
                <Input
                  id="whName"
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="whCountry">Country</Label>
                <Input
                  id="whCountry"
                  required
                  value={form.country}
                  onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="whCity">City</Label>
                <Input
                  id="whCity"
                  value={form.city}
                  onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="whCapacity">Capacity (units)</Label>
                <Input
                  id="whCapacity"
                  type="number"
                  min={1}
                  value={form.capacity}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, capacity: Number(e.target.value) || 1 }))
                  }
                />
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
                {editing ? "Save changes" : "Create warehouse"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageTransition>
  );
}
