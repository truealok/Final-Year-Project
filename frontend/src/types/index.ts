/**
 * API types — mirror the ResiliChain backend Pydantic schemas (snake_case).
 */

// ---------------------------------------------------------------- enums
export type UserRole = "admin" | "supply_chain_manager" | "analyst";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type EntityStatus = "active" | "inactive" | "disrupted" | "maintenance";
export type InventoryStatus = "in_stock" | "low_stock" | "out_of_stock";
export type AlertSeverity = "critical" | "warning" | "info";
export type SeverityLevel = "low" | "medium" | "high" | "critical";
export type ForecastModel = "prophet" | "xgboost" | "lstm";
export type NodeType = "supplier" | "factory" | "warehouse" | "retail_store";
export type SimulationType =
  | "supplier_failure"
  | "transport_delay"
  | "flood"
  | "demand_spike"
  | "warehouse_failure"
  | "machine_breakdown";
export type RecommendationPriority = "low" | "medium" | "high" | "critical";
export type RecommendationStatus = "pending" | "applied" | "dismissed";
export type ReportType = "forecast" | "simulation" | "inventory" | "risk";
export type ReportFormat = "json" | "csv" | "pdf";

// ---------------------------------------------------------------- shared
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface Message {
  message: string;
}

// ---------------------------------------------------------------- auth
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

// ---------------------------------------------------------------- catalog
export interface Category {
  id: string;
  name: string;
  description: string | null;
}

export interface ProductBrief {
  id: string;
  sku: string;
  name: string;
}

export interface Product extends ProductBrief {
  description: string | null;
  category: Category | null;
  unit_cost: number;
  unit_price: number;
  unit: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------- suppliers
export interface Supplier {
  id: string;
  name: string;
  country: string;
  city: string | null;
  contact_email: string | null;
  reliability_score: number;
  lead_time_days: number;
  risk_level: RiskLevel;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
}

export interface SupplierInput {
  name: string;
  country: string;
  city?: string | null;
  contact_email?: string | null;
  reliability_score?: number;
  lead_time_days?: number;
  risk_level?: RiskLevel;
  status?: EntityStatus;
}

// ---------------------------------------------------------------- warehouses
export interface WarehouseBrief {
  id: string;
  name: string;
}

export interface Warehouse extends WarehouseBrief {
  country: string;
  city: string | null;
  capacity: number;
  latitude: number | null;
  longitude: number | null;
  status: EntityStatus;
  factory_id: string | null;
  current_inventory: number;
  utilization_pct: number;
  created_at: string;
  updated_at: string;
}

export interface WarehouseInput {
  name: string;
  country: string;
  city?: string | null;
  capacity?: number;
  status?: EntityStatus;
}

// ---------------------------------------------------------------- inventory
export interface InventoryItem {
  id: string;
  product: ProductBrief;
  warehouse: WarehouseBrief;
  quantity: number;
  reorder_point: number;
  safety_stock: number;
  unit_cost: number;
  status: InventoryStatus;
  total_value: number;
  created_at: string;
  updated_at: string;
}

export interface InventoryInput {
  product_id: string;
  warehouse_id: string;
  quantity: number;
  reorder_point: number;
  safety_stock: number;
  unit_cost: number;
}

export interface InventorySummary {
  total_items: number;
  total_units: number;
  total_value: number;
  low_stock_items: number;
  out_of_stock_items: number;
}

// ---------------------------------------------------------------- forecast
export interface ForecastPoint {
  date: string;
  predicted_demand: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastPredictRequest {
  product_id: string;
  warehouse_id: string;
  start_date: string;
  end_date: string;
  model: ForecastModel;
}

export interface ForecastPredictResponse {
  forecast_id: string;
  product_id: string;
  warehouse_id: string;
  model_used: string;
  prediction_date: string;
  confidence_level: number;
  points: ForecastPoint[];
  metrics: Record<string, number | string | boolean | null>;
}

export interface ForecastHistoryItem {
  id: string;
  product: ProductBrief;
  warehouse: WarehouseBrief;
  model_used: string;
  start_date: string;
  end_date: string;
  confidence_level: number;
  forecast_data: ForecastPoint[];
  metrics: Record<string, number | string | boolean | null>;
  created_at: string;
}

export interface ForecastModelInfo {
  name: string;
  display_name: string;
  status: string;
  description: string;
  metrics: {
    mape: number;
    rmse: number;
    mae: number;
    last_trained: string | null;
  };
}

// ---------------------------------------------------------------- simulation
export interface SimulationRunRequest {
  simulation_type: SimulationType;
  severity: SeverityLevel;
  duration_days: number;
  probability: number;
  affected_node_id?: string | null;
  affected_node_type?: NodeType | null;
  monte_carlo_runs?: number;
  notes?: string | null;
}

export interface AffectedNode {
  id: string | null;
  name: string;
  type: string;
  impact_pct: number;
}

export interface AffectedRoute {
  name: string;
  transport_mode: string;
  delay_hours: number;
  status: string;
}

export interface SimulationResult {
  simulation_id: string;
  simulation_type: SimulationType;
  severity: SeverityLevel;
  duration_days: number;
  probability: number;
  resilience_score: number;
  expected_cost: number;
  recovery_time_days: number;
  stockout_probability: number;
  risk_level: RiskLevel;
  affected_nodes: AffectedNode[];
  affected_routes: AffectedRoute[];
  /** Monte Carlo engine extras (absent on legacy records) */
  service_level?: number | null;
  baseline_service_level?: number | null;
  emissions_tons_co2?: number | null;
  n_runs?: number | null;
  created_at: string;
}

export interface SimulationHistoryItem {
  id: string;
  simulation_type: SimulationType;
  severity: SeverityLevel;
  duration_days: number;
  probability: number;
  resilience_score: number;
  expected_cost: number;
  recovery_time_days: number;
  stockout_probability: number;
  risk_level: RiskLevel;
  results: {
    affected_nodes?: AffectedNode[];
    affected_routes?: AffectedRoute[];
    [key: string]: unknown;
  };
  created_at: string;
}

// ---------------------------------------------------------------- digital twin
export interface NetworkNode {
  id: string;
  name: string;
  type: NodeType;
  status: string;
  country: string | null;
  city: string | null;
  capacity: number | null;
  current_inventory: number | null;
  utilization_pct: number | null;
  risk_level: RiskLevel;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  transport_mode: string;
  distance_km: number;
  transit_time_hours: number;
  status: string;
  risk_level: RiskLevel;
}

export interface NetworkSummary {
  total_nodes: number;
  total_edges: number;
  node_counts: Record<string, number>;
  overall_risk: RiskLevel;
  resilience_score: number;
}

export interface NetworkResponse {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  summary: NetworkSummary;
}

// ---------------------------------------------------------------- dashboard
export interface DashboardResponse {
  forecast_accuracy: number;
  resilience_score: number;
  expected_cost: number;
  current_inventory: {
    total_units: number;
    total_value: number;
    low_stock_items: number;
    out_of_stock_items: number;
  };
  stockout_probability: number;
  recovery_time_days: number;
  carbon_emissions: {
    total_tons_co2: number;
    change_pct: number;
  };
  latest_alerts: Alert[];
  recent_simulations: SimulationHistoryItem[];
}

// ---------------------------------------------------------------- analytics
export interface TrendPoint {
  period: string;
  value: number;
}

export interface SupplierPerformance {
  id: string;
  name: string;
  reliability_score: number;
  on_time_delivery_rate: number;
  avg_lead_time_days: number;
  risk_level: RiskLevel;
}

export interface WarehouseUtilization {
  id: string;
  name: string;
  capacity: number;
  current_inventory: number;
  utilization_pct: number;
  status: string;
}

export interface AnalyticsResponse {
  demand_trend: TrendPoint[];
  inventory_trend: TrendPoint[];
  supplier_performance: SupplierPerformance[];
  warehouse_utilization: WarehouseUtilization[];
  disruption_frequency: TrendPoint[];
  recovery_trend: TrendPoint[];
  carbon_emissions: TrendPoint[];
}

// ---------------------------------------------------------------- recommendations
export interface Recommendation {
  id: string;
  title: string;
  suggested_action: string;
  reason: string;
  priority: RecommendationPriority;
  confidence: number;
  estimated_savings: number;
  category: string;
  status: RecommendationStatus;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------- reports
export interface Report {
  id: string;
  name: string;
  report_type: ReportType;
  format: ReportFormat;
  status: string;
  parameters: Record<string, unknown>;
  created_at: string;
}

export interface ReportDetail extends Report {
  content: {
    columns: string[];
    rows: (string | number)[][];
    summary: Record<string, unknown>;
  };
}

// ---------------------------------------------------------------- alerts
export interface Alert {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  source: string | null;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertSummary {
  total: number;
  unread: number;
  critical: number;
  warning: number;
  info: number;
}
