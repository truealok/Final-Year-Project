/** Typed endpoint groups for every backend module. */

import { api } from "@/services/api";
import type {
  Alert,
  AlertSummary,
  AnalyticsResponse,
  AuthResponse,
  Category,
  DashboardResponse,
  ForecastHistoryItem,
  ForecastModelInfo,
  ForecastPredictRequest,
  ForecastPredictResponse,
  InventoryInput,
  InventoryItem,
  InventorySummary,
  Message,
  NetworkResponse,
  Page,
  Product,
  Recommendation,
  RecommendationStatus,
  Report,
  ReportDetail,
  ReportType,
  SimulationHistoryItem,
  SimulationResult,
  SimulationRunRequest,
  Supplier,
  SupplierInput,
  TokenPair,
  User,
  Warehouse,
  WarehouseInput,
} from "@/types";

export interface ListParams {
  page?: number;
  size?: number;
  [key: string]: string | number | boolean | undefined | null;
}

export const AuthApi = {
  login: (email: string, password: string) =>
    api<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      skipRefresh: true,
    }),
  signup: (email: string, password: string, full_name: string) =>
    api<AuthResponse>("/auth/signup", {
      method: "POST",
      body: { email, password, full_name },
      skipRefresh: true,
    }),
  me: () => api<User>("/auth/me"),
  logout: () => api<Message>("/auth/logout", { method: "POST" }),
  refresh: (refresh_token: string) =>
    api<TokenPair>("/auth/refresh", {
      method: "POST",
      body: { refresh_token },
      skipRefresh: true,
    }),
  forgotPassword: (email: string) =>
    api<{ message: string; reset_token: string | null }>(
      "/auth/forgot-password",
      { method: "POST", body: { email }, skipRefresh: true },
    ),
  resetPassword: (token: string, new_password: string) =>
    api<Message>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
      skipRefresh: true,
    }),
};

export const UserApi = {
  updateMe: (data: { full_name?: string; password?: string }) =>
    api<User>("/users/me", { method: "PATCH", body: data }),
};

export const DashboardApi = {
  get: () => api<DashboardResponse>("/dashboard"),
};

export const AnalyticsApi = {
  get: () => api<AnalyticsResponse>("/analytics"),
};

export const ForecastApi = {
  predict: (data: ForecastPredictRequest) =>
    api<ForecastPredictResponse>("/forecast/predict", {
      method: "POST",
      body: data,
    }),
  history: (params?: ListParams) =>
    api<Page<ForecastHistoryItem>>("/forecast/history", { params }),
  models: () => api<ForecastModelInfo[]>("/forecast/models"),
};

export const SimulationApi = {
  run: (data: SimulationRunRequest) =>
    api<SimulationResult>("/simulation/run", { method: "POST", body: data }),
  history: (params?: ListParams) =>
    api<Page<SimulationHistoryItem>>("/simulation/history", { params }),
  types: () => api<string[]>("/simulation/types"),
};

export const DigitalTwinApi = {
  network: () => api<NetworkResponse>("/digital-twin/network"),
};

export const InventoryApi = {
  list: (params?: ListParams) =>
    api<Page<InventoryItem>>("/inventory", { params }),
  create: (data: InventoryInput) =>
    api<InventoryItem>("/inventory", { method: "POST", body: data }),
  update: (id: string, data: Partial<InventoryInput>) =>
    api<InventoryItem>(`/inventory/${id}`, { method: "PUT", body: data }),
  remove: (id: string) =>
    api<void>(`/inventory/${id}`, { method: "DELETE" }),
  summary: () => api<InventorySummary>("/inventory/summary"),
  products: (params?: ListParams) =>
    api<Page<Product>>("/inventory/products", { params }),
  categories: () => api<Category[]>("/inventory/categories"),
};

export const SupplierApi = {
  list: (params?: ListParams) =>
    api<Page<Supplier>>("/suppliers", { params }),
  create: (data: SupplierInput) =>
    api<Supplier>("/suppliers", { method: "POST", body: data }),
  update: (id: string, data: Partial<SupplierInput>) =>
    api<Supplier>(`/suppliers/${id}`, { method: "PUT", body: data }),
  remove: (id: string) => api<void>(`/suppliers/${id}`, { method: "DELETE" }),
};

export const WarehouseApi = {
  list: (params?: ListParams) =>
    api<Page<Warehouse>>("/warehouses", { params }),
  create: (data: WarehouseInput) =>
    api<Warehouse>("/warehouses", { method: "POST", body: data }),
  update: (id: string, data: Partial<WarehouseInput>) =>
    api<Warehouse>(`/warehouses/${id}`, { method: "PUT", body: data }),
  remove: (id: string) => api<void>(`/warehouses/${id}`, { method: "DELETE" }),
};

export const RecommendationApi = {
  list: (params?: ListParams) =>
    api<Page<Recommendation>>("/recommendations", { params }),
  generate: () =>
    api<Recommendation[]>("/recommendations/generate", { method: "POST" }),
  updateStatus: (id: string, status: RecommendationStatus) =>
    api<Recommendation>(`/recommendations/${id}`, {
      method: "PATCH",
      body: { status },
    }),
};

export const ReportApi = {
  list: (params?: ListParams) => api<Page<Report>>("/reports", { params }),
  generate: (report_type: ReportType) =>
    api<ReportDetail>("/reports/generate", {
      method: "POST",
      body: { report_type },
    }),
  get: (id: string) => api<ReportDetail>(`/reports/${id}`),
  exportFile: (id: string, format: "csv" | "pdf") =>
    api<Response>(`/reports/${id}/export`, {
      params: { export_format: format },
      raw: true,
    }),
  remove: (id: string) => api<void>(`/reports/${id}`, { method: "DELETE" }),
};

export const AlertApi = {
  list: (params?: ListParams) => api<Page<Alert>>("/alerts", { params }),
  summary: () => api<AlertSummary>("/alerts/summary"),
  markRead: (id: string) =>
    api<Alert>(`/alerts/${id}/read`, { method: "PATCH" }),
  markAllRead: () => api<Message>("/alerts/read-all", { method: "PATCH" }),
  remove: (id: string) => api<void>(`/alerts/${id}`, { method: "DELETE" }),
};
