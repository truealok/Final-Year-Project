import { Monitor, Moon, Save, Sun } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";
import { FORECAST_MODELS, SEVERITY_LEVELS } from "@/utils/constants";

const PREFS_KEY = "rc_preferences";

interface Preferences {
  language: string;
  notifyCritical: boolean;
  notifyWarning: boolean;
  notifyInfo: boolean;
  notifyEmail: boolean;
  defaultModel: string;
  defaultHorizonDays: number;
  defaultSeverity: string;
  defaultDurationDays: number;
}

const DEFAULT_PREFS: Preferences = {
  language: "en",
  notifyCritical: true,
  notifyWarning: true,
  notifyInfo: false,
  notifyEmail: false,
  defaultModel: "prophet",
  defaultHorizonDays: 30,
  defaultSeverity: "medium",
  defaultDurationDays: 7,
};

function loadPrefs(): Preferences {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [prefs, setPrefs] = useState<Preferences>(loadPrefs);

  const save = () => {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    toast.success("Settings saved.");
  };

  const set = <K extends keyof Preferences>(key: K, value: Preferences[K]) =>
    setPrefs((p) => ({ ...p, [key]: value }));

  const themeOptions = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ] as const;

  return (
    <PageTransition>
      <PageHeader
        title="Settings"
        description="Workspace preferences for appearance, notifications and defaults."
        breadcrumbs={[{ label: "Settings" }]}
        actions={
          <Button onClick={save}>
            <Save />
            Save settings
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-2">
        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Appearance</CardTitle>
            <CardDescription>Theme applies immediately.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
              {themeOptions.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setTheme(value)}
                  className={cn(
                    "flex flex-col items-center gap-1.5 rounded-md border p-3 text-sm transition-colors hover:bg-accent",
                    theme === value && "border-primary bg-primary/5 text-primary",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>
            <Separator />
            <div className="space-y-1.5">
              <Label>Language</Label>
              <Select
                value={prefs.language}
                onValueChange={(v) => set("language", v)}
              >
                <SelectTrigger className="max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="de">Deutsch (coming soon)</SelectItem>
                  <SelectItem value="hi">हिन्दी (coming soon)</SelectItem>
                  <SelectItem value="ja">日本語 (coming soon)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Interface copy is English-only for now; your choice is stored
                for when localization ships.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Notifications</CardTitle>
            <CardDescription>
              Which alert severities appear in your notification feed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {(
              [
                ["notifyCritical", "Critical alerts", "Stockouts, node failures, severe weather"],
                ["notifyWarning", "Warnings", "Low stock, reliability drops, route congestion"],
                ["notifyInfo", "Informational", "Completed forecasts and generated recommendations"],
                ["notifyEmail", "Email digest", "Daily summary to your account email"],
              ] as const
            ).map(([key, label, hint]) => (
              <div key={key} className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">{hint}</p>
                </div>
                <Switch
                  checked={prefs[key]}
                  onCheckedChange={(checked) => set(key, checked)}
                />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Forecast defaults */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Forecast Settings</CardTitle>
            <CardDescription>Defaults for new forecast runs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Default model</Label>
              <Select
                value={prefs.defaultModel}
                onValueChange={(v) => set("defaultModel", v)}
              >
                <SelectTrigger className="max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FORECAST_MODELS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="horizon">Default horizon (days)</Label>
              <Input
                id="horizon"
                type="number"
                min={7}
                max={365}
                className="max-w-xs"
                value={prefs.defaultHorizonDays}
                onChange={(e) =>
                  set("defaultHorizonDays", Number(e.target.value) || 30)
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Simulation defaults */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Simulation Settings</CardTitle>
            <CardDescription>Defaults for new disruption scenarios.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Default severity</Label>
              <Select
                value={prefs.defaultSeverity}
                onValueChange={(v) => set("defaultSeverity", v)}
              >
                <SelectTrigger className="max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITY_LEVELS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="simDuration">Default duration (days)</Label>
              <Input
                id="simDuration"
                type="number"
                min={1}
                max={365}
                className="max-w-xs"
                value={prefs.defaultDurationDays}
                onChange={(e) =>
                  set("defaultDurationDays", Number(e.target.value) || 7)
                }
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
