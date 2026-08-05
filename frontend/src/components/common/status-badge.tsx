import {
  AlertTriangle,
  CheckCircle2,
  Info,
  MinusCircle,
  OctagonAlert,
  Wrench,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { titleCase } from "@/utils/format";

type BadgeVariant =
  | "success"
  | "warning"
  | "destructive"
  | "muted"
  | "secondary"
  | "default";

/**
 * Color-coded badge for domain states. Status colors always ship with an
 * icon + label so meaning never rides on color alone.
 */
const RISK_MAP: Record<string, BadgeVariant> = {
  low: "success",
  medium: "warning",
  high: "destructive",
  critical: "destructive",
};

const STATUS_MAP: Record<string, BadgeVariant> = {
  active: "success",
  inactive: "muted",
  disrupted: "destructive",
  maintenance: "warning",
  in_stock: "success",
  low_stock: "warning",
  out_of_stock: "destructive",
  pending: "secondary",
  applied: "success",
  dismissed: "muted",
  completed: "success",
};

const SEVERITY_MAP: Record<string, BadgeVariant> = {
  critical: "destructive",
  warning: "warning",
  info: "secondary",
};

const ICONS: Record<BadgeVariant, typeof Info> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  destructive: OctagonAlert,
  muted: MinusCircle,
  secondary: Info,
  default: Info,
};

interface StatusBadgeProps {
  value: string;
  kind?: "risk" | "status" | "severity" | "priority";
  showIcon?: boolean;
}

export function StatusBadge({
  value,
  kind = "status",
  showIcon = true,
}: StatusBadgeProps) {
  const map =
    kind === "risk" || kind === "priority"
      ? RISK_MAP
      : kind === "severity"
        ? SEVERITY_MAP
        : STATUS_MAP;
  const variant = map[value] ?? "secondary";
  const Icon = value === "maintenance" ? Wrench : ICONS[variant];

  return (
    <Badge variant={variant}>
      {showIcon && <Icon className="h-3 w-3" />}
      {titleCase(value)}
    </Badge>
  );
}
