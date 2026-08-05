import {
  BarChart3,
  Bell,
  Boxes,
  FileText,
  LayoutDashboard,
  Lightbulb,
  Network,
  Settings,
  ShieldAlert,
  TrendingUp,
  Truck,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/forecast", label: "Forecast", icon: TrendingUp },
  { to: "/digital-twin", label: "Digital Twin", icon: Network },
  { to: "/simulation", label: "Simulation", icon: ShieldAlert },
  { to: "/recommendations", label: "Recommendations", icon: Lightbulb },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/suppliers", label: "Suppliers", icon: Truck },
  { to: "/warehouses", label: "Warehouses", icon: Warehouse },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/settings", label: "Settings", icon: Settings },
];
