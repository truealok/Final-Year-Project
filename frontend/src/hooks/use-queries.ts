/** React Query hooks for every backend resource. */

import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";

import {
  AlertApi,
  AnalyticsApi,
  DashboardApi,
  DigitalTwinApi,
  ForecastApi,
  InventoryApi,
  RecommendationApi,
  ReportApi,
  SimulationApi,
  SupplierApi,
  WarehouseApi,
  type ListParams,
} from "@/services/endpoints";
import type {
  ForecastPredictRequest,
  InventoryInput,
  RecommendationStatus,
  ReportType,
  SimulationRunRequest,
  SupplierInput,
  WarehouseInput,
} from "@/types";

// ------------------------------------------------------------- dashboards
export const useDashboard = () =>
  useQuery({ queryKey: ["dashboard"], queryFn: DashboardApi.get });

export const useAnalytics = () =>
  useQuery({ queryKey: ["analytics"], queryFn: AnalyticsApi.get });

export const useNetwork = () =>
  useQuery({ queryKey: ["digital-twin"], queryFn: DigitalTwinApi.network });

// ------------------------------------------------------------- forecast
export const useForecastModels = () =>
  useQuery({ queryKey: ["forecast-models"], queryFn: ForecastApi.models });

export const useForecastHistory = (params?: ListParams) =>
  useQuery({
    queryKey: ["forecast-history", params],
    queryFn: () => ForecastApi.history(params),
    placeholderData: keepPreviousData,
  });

export const usePredictForecast = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ForecastPredictRequest) => ForecastApi.predict(data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["forecast-history"] }),
  });
};

// ------------------------------------------------------------- simulation
export const useSimulationHistory = (params?: ListParams) =>
  useQuery({
    queryKey: ["simulation-history", params],
    queryFn: () => SimulationApi.history(params),
    placeholderData: keepPreviousData,
  });

export const useRunSimulation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SimulationRunRequest) => SimulationApi.run(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simulation-history"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

// ------------------------------------------------------------- inventory
export const useInventory = (params?: ListParams) =>
  useQuery({
    queryKey: ["inventory", params],
    queryFn: () => InventoryApi.list(params),
    placeholderData: keepPreviousData,
  });

export const useInventorySummary = () =>
  useQuery({
    queryKey: ["inventory-summary"],
    queryFn: InventoryApi.summary,
  });

export const useProducts = (params?: ListParams) =>
  useQuery({
    queryKey: ["products", params],
    queryFn: () => InventoryApi.products(params),
    placeholderData: keepPreviousData,
  });

export function useInventoryMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["inventory"] });
    queryClient.invalidateQueries({ queryKey: ["inventory-summary"] });
  };
  const create = useMutation({
    mutationFn: (data: InventoryInput) => InventoryApi.create(data),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<InventoryInput> }) =>
      InventoryApi.update(id, data),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => InventoryApi.remove(id),
    onSuccess: invalidate,
  });
  return { create, update, remove };
}

// ------------------------------------------------------------- suppliers
export const useSuppliers = (params?: ListParams) =>
  useQuery({
    queryKey: ["suppliers", params],
    queryFn: () => SupplierApi.list(params),
    placeholderData: keepPreviousData,
  });

export function useSupplierMutations() {
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["suppliers"] });
  const create = useMutation({
    mutationFn: (data: SupplierInput) => SupplierApi.create(data),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SupplierInput> }) =>
      SupplierApi.update(id, data),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => SupplierApi.remove(id),
    onSuccess: invalidate,
  });
  return { create, update, remove };
}

// ------------------------------------------------------------- warehouses
export const useWarehouses = (params?: ListParams) =>
  useQuery({
    queryKey: ["warehouses", params],
    queryFn: () => WarehouseApi.list(params),
    placeholderData: keepPreviousData,
  });

export function useWarehouseMutations() {
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["warehouses"] });
  const create = useMutation({
    mutationFn: (data: WarehouseInput) => WarehouseApi.create(data),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<WarehouseInput> }) =>
      WarehouseApi.update(id, data),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => WarehouseApi.remove(id),
    onSuccess: invalidate,
  });
  return { create, update, remove };
}

// ------------------------------------------------------------- recommendations
export const useRecommendations = (params?: ListParams) =>
  useQuery({
    queryKey: ["recommendations", params],
    queryFn: () => RecommendationApi.list(params),
    placeholderData: keepPreviousData,
  });

export function useRecommendationMutations() {
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["recommendations"] });
  const generate = useMutation({
    mutationFn: () => RecommendationApi.generate(),
    onSuccess: invalidate,
  });
  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: RecommendationStatus }) =>
      RecommendationApi.updateStatus(id, status),
    onSuccess: invalidate,
  });
  return { generate, updateStatus };
}

// ------------------------------------------------------------- reports
export const useReports = (params?: ListParams) =>
  useQuery({
    queryKey: ["reports", params],
    queryFn: () => ReportApi.list(params),
    placeholderData: keepPreviousData,
  });

export function useReportMutations() {
  const queryClient = useQueryClient();
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["reports"] });
  const generate = useMutation({
    mutationFn: (reportType: ReportType) => ReportApi.generate(reportType),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => ReportApi.remove(id),
    onSuccess: invalidate,
  });
  return { generate, remove };
}

// ------------------------------------------------------------- alerts
export const useAlerts = (params?: ListParams) =>
  useQuery({
    queryKey: ["alerts", params],
    queryFn: () => AlertApi.list(params),
    placeholderData: keepPreviousData,
  });

export const useAlertSummary = () =>
  useQuery({
    queryKey: ["alert-summary"],
    queryFn: AlertApi.summary,
    refetchInterval: 60_000,
  });

export function useAlertMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
    queryClient.invalidateQueries({ queryKey: ["alert-summary"] });
  };
  const markRead = useMutation({
    mutationFn: (id: string) => AlertApi.markRead(id),
    onSuccess: invalidate,
  });
  const markAllRead = useMutation({
    mutationFn: () => AlertApi.markAllRead(),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => AlertApi.remove(id),
    onSuccess: invalidate,
  });
  return { markRead, markAllRead, remove };
}
