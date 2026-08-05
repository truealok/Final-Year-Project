import { Boxes, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { TableSkeleton } from "@/components/common/loading-skeleton";
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
import { useAuth } from "@/hooks/use-auth";
import { useDebounce } from "@/hooks/use-debounce";
import {
  useInventory,
  useInventoryMutations,
  useInventorySummary,
  useProducts,
  useWarehouses,
} from "@/hooks/use-queries";
import { ApiError } from "@/services/api";
import type { InventoryItem } from "@/types";
import { derivedIncoming, derivedReserved } from "@/utils/derived";
import { formatCurrency, formatNumber, titleCase } from "@/utils/format";

interface FormState {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  reorder_point: number;
  safety_stock: number;
  unit_cost: number;
}

const EMPTY_FORM: FormState = {
  product_id: "",
  warehouse_id: "",
  quantity: 0,
  reorder_point: 50,
  safety_stock: 25,
  unit_cost: 0,
};

export default function InventoryPage() {
  const { hasRole } = useAuth();
  const canEdit = hasRole("admin", "supply_chain_manager");

  const [page, setPage] = useState(1);
  const [warehouseFilter, setWarehouseFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search);

  const { data: summary } = useInventorySummary();
  const { data: warehouses } = useWarehouses({ page: 1, size: 100 });
  const { data: products } = useProducts({ page: 1, size: 100 });
  const { data, isLoading } = useInventory({
    page,
    size: 15,
    warehouse_id: warehouseFilter === "all" ? undefined : warehouseFilter,
    status_filter: statusFilter === "all" ? undefined : statusFilter,
  });
  const { create, update, remove } = useInventoryMutations();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<InventoryItem | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  // Client-side search within the fetched page (backend has no text search on inventory yet).
  const visibleItems = useMemo(() => {
    const items = data?.items ?? [];
    const query = debouncedSearch.trim().toLowerCase();
    if (!query) return items;
    return items.filter(
      (item) =>
        item.product.name.toLowerCase().includes(query) ||
        item.product.sku.toLowerCase().includes(query) ||
        item.warehouse.name.toLowerCase().includes(query),
    );
  }, [data, debouncedSearch]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (item: InventoryItem) => {
    setEditing(item);
    setForm({
      product_id: item.product.id,
      warehouse_id: item.warehouse.id,
      quantity: item.quantity,
      reorder_point: item.reorder_point,
      safety_stock: item.safety_stock,
      unit_cost: item.unit_cost,
    });
    setDialogOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      if (editing) {
        await update.mutateAsync({
          id: editing.id,
          data: {
            quantity: form.quantity,
            reorder_point: form.reorder_point,
            safety_stock: form.safety_stock,
            unit_cost: form.unit_cost,
          },
        });
        toast.success("Inventory record updated.");
      } else {
        if (!form.product_id || !form.warehouse_id) {
          toast.error("Select a product and warehouse.");
          return;
        }
        await create.mutateAsync(form);
        toast.success("Inventory record created.");
      }
      setDialogOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Save failed.");
    }
  };

  const onDelete = async (item: InventoryItem) => {
    if (!window.confirm(`Delete inventory of ${item.product.name} at ${item.warehouse.name}?`)) {
      return;
    }
    try {
      await remove.mutateAsync(item.id);
      toast.success("Inventory record deleted.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Delete failed.");
    }
  };

  const setNumber = (key: keyof FormState) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: Number(event.target.value) || 0 }));

  return (
    <PageTransition>
      <PageHeader
        title="Inventory"
        description="Stock positions across every warehouse in the network."
        breadcrumbs={[{ label: "Inventory" }]}
        actions={
          canEdit && (
            <Button onClick={openCreate}>
              <Plus />
              Add inventory
            </Button>
          )
        }
      />

      {/* Summary strip */}
      {summary && (
        <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
          {[
            { label: "Records", value: formatNumber(summary.total_items) },
            { label: "Total units", value: formatNumber(summary.total_units) },
            { label: "Total value", value: formatCurrency(summary.total_value, true) },
            { label: "Low stock", value: formatNumber(summary.low_stock_items) },
            { label: "Out of stock", value: formatNumber(summary.out_of_stock_items) },
          ].map((stat) => (
            <div key={stat.label} className="rounded-lg border bg-card px-4 py-3">
              <p className="text-xs text-muted-foreground">{stat.label}</p>
              <p className="mt-0.5 text-lg font-semibold">{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search product, SKU or warehouse…"
          className="w-full sm:w-72"
        />
        <Select
          value={warehouseFilter}
          onValueChange={(v) => { setWarehouseFilter(v); setPage(1); }}
        >
          <SelectTrigger className="w-full sm:w-52">
            <SelectValue placeholder="Warehouse" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All warehouses</SelectItem>
            {(warehouses?.items ?? []).map((w) => (
              <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={statusFilter}
          onValueChange={(v) => { setStatusFilter(v); setPage(1); }}
        >
          <SelectTrigger className="w-full sm:w-44">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="in_stock">In stock</SelectItem>
            <SelectItem value="low_stock">Low stock</SelectItem>
            <SelectItem value="out_of_stock">Out of stock</SelectItem>
          </SelectContent>
        </Select>
      </FilterBar>

      <Card>
        <CardContent className="p-0 sm:p-2">
          {isLoading ? (
            <div className="p-4"><TableSkeleton rows={8} /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead className="hidden md:table-cell">Warehouse</TableHead>
                  <TableHead className="text-right">Available</TableHead>
                  <TableHead className="hidden text-right sm:table-cell">Reserved</TableHead>
                  <TableHead className="hidden text-right lg:table-cell">Incoming</TableHead>
                  <TableHead className="hidden text-right lg:table-cell">Safety Stock</TableHead>
                  <TableHead>Status</TableHead>
                  {canEdit && <TableHead className="w-20 text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleItems.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <p className="font-medium">{item.product.name}</p>
                      <p className="text-xs text-muted-foreground">{item.product.sku}</p>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {item.warehouse.name}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatNumber(item.quantity)}
                    </TableCell>
                    <TableCell className="hidden text-right tabular-nums text-muted-foreground sm:table-cell">
                      {formatNumber(derivedReserved(item.id, item.quantity))}
                    </TableCell>
                    <TableCell className="hidden text-right tabular-nums text-muted-foreground lg:table-cell">
                      {formatNumber(derivedIncoming(item.id, item.reorder_point))}
                    </TableCell>
                    <TableCell className="hidden text-right tabular-nums text-muted-foreground lg:table-cell">
                      {formatNumber(item.safety_stock)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge value={item.status} showIcon={false} />
                    </TableCell>
                    {canEdit && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => openEdit(item)}
                            aria-label="Edit"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive"
                            onClick={() => onDelete(item)}
                            aria-label="Delete"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
                {visibleItems.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={canEdit ? 8 : 7}
                      className="py-10 text-center text-muted-foreground"
                    >
                      <Boxes className="mx-auto mb-2 h-6 w-6" />
                      No inventory records match your filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Pagination
        page={data?.page ?? 1}
        pages={data?.pages ?? 1}
        total={data?.total ?? 0}
        onPageChange={setPage}
      />

      {/* Create / edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit inventory record" : "Add inventory record"}
            </DialogTitle>
            <DialogDescription>
              {editing
                ? `${editing.product.name} at ${editing.warehouse.name}`
                : "Register stock of a product at a warehouse."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            {!editing && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Product</Label>
                  <Select
                    value={form.product_id}
                    onValueChange={(v) => {
                      const product = products?.items.find((p) => p.id === v);
                      setForm((f) => ({
                        ...f,
                        product_id: v,
                        unit_cost: product?.unit_cost ?? f.unit_cost,
                      }));
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select product" />
                    </SelectTrigger>
                    <SelectContent>
                      {(products?.items ?? []).map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.sku} · {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Warehouse</Label>
                  <Select
                    value={form.warehouse_id}
                    onValueChange={(v) => setForm((f) => ({ ...f, warehouse_id: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select warehouse" />
                    </SelectTrigger>
                    <SelectContent>
                      {(warehouses?.items ?? []).map((w) => (
                        <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="quantity">Quantity</Label>
                <Input id="quantity" type="number" min={0} value={form.quantity} onChange={setNumber("quantity")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="unitCost">Unit cost (USD)</Label>
                <Input id="unitCost" type="number" min={0} step="0.01" value={form.unit_cost} onChange={setNumber("unit_cost")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="reorderPoint">Reorder point</Label>
                <Input id="reorderPoint" type="number" min={0} value={form.reorder_point} onChange={setNumber("reorder_point")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="safetyStock">Safety stock</Label>
                <Input id="safetyStock" type="number" min={0} value={form.safety_stock} onChange={setNumber("safety_stock")} />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending || update.isPending}>
                {(create.isPending || update.isPending) && <Loader2 className="animate-spin" />}
                {editing ? "Save changes" : "Create record"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageTransition>
  );
}
