/** Shared labels and option lists. */

import type {
  ForecastModel,
  SeverityLevel,
  SimulationType,
} from "@/types";

export const SIMULATION_TYPES: { value: SimulationType; label: string }[] = [
  { value: "supplier_failure", label: "Supplier Failure" },
  { value: "transport_delay", label: "Transport Delay" },
  { value: "flood", label: "Flood" },
  { value: "demand_spike", label: "Demand Spike" },
  { value: "warehouse_failure", label: "Warehouse Shutdown" },
  { value: "machine_breakdown", label: "Machine Failure" },
];

export const SEVERITY_LEVELS: { value: SeverityLevel; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

export const FORECAST_MODELS: { value: ForecastModel; label: string }[] = [
  { value: "prophet", label: "Prophet" },
  { value: "xgboost", label: "XGBoost" },
  { value: "lstm", label: "LSTM" },
];

export const RISK_LEVELS = ["low", "medium", "high", "critical"] as const;

export const ENTITY_STATUSES = [
  "active",
  "inactive",
  "disrupted",
  "maintenance",
] as const;
