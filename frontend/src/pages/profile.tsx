import { Loader2, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/common/page-header";
import { PageTransition } from "@/components/common/page-transition";
import { StatusBadge } from "@/components/common/status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/hooks/use-auth";
import { UserApi } from "@/services/endpoints";
import { ApiError } from "@/services/api";
import { formatDate, titleCase } from "@/utils/format";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  if (!user) return null;

  const saveName = async (event: FormEvent) => {
    event.preventDefault();
    setSavingName(true);
    try {
      await UserApi.updateMe({ full_name: fullName });
      await refreshUser();
      toast.success("Profile updated.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Update failed.");
    } finally {
      setSavingName(false);
    }
  };

  const savePassword = async (event: FormEvent) => {
    event.preventDefault();
    if (password !== confirm) {
      toast.error("Passwords do not match.");
      return;
    }
    setSavingPassword(true);
    try {
      await UserApi.updateMe({ password });
      setPassword("");
      setConfirm("");
      toast.success("Password changed.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Update failed.");
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <PageTransition>
      <PageHeader
        title="Profile"
        description="Your account details and security settings."
        breadcrumbs={[{ label: "Profile" }]}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardContent className="flex flex-col items-center p-6 text-center">
            <Avatar className="h-16 w-16">
              <AvatarFallback className="text-lg">
                {user.full_name
                  .split(/\s+/)
                  .map((p) => p[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <p className="mt-3 font-semibold">{user.full_name}</p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <div className="mt-3 flex items-center gap-2">
              <StatusBadge value={user.is_active ? "active" : "inactive"} />
              <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                <ShieldCheck className="h-3 w-3" />
                {titleCase(user.role)}
              </span>
            </div>
            <Separator className="my-4" />
            <dl className="w-full space-y-1.5 text-left text-xs text-muted-foreground">
              <div className="flex justify-between">
                <dt>Member since</dt>
                <dd className="text-foreground">{formatDate(user.created_at)}</dd>
              </div>
              <div className="flex justify-between">
                <dt>Last login</dt>
                <dd className="text-foreground">
                  {user.last_login_at ? formatDate(user.last_login_at) : "—"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Account settings</CardTitle>
            <CardDescription>
              Update your display name or change your password.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form onSubmit={saveName} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="fullName">Full name</Label>
                <Input
                  id="fullName"
                  value={fullName}
                  required
                  onChange={(event) => setFullName(event.target.value)}
                  className="max-w-sm"
                />
              </div>
              <Button type="submit" size="sm" disabled={savingName}>
                {savingName && <Loader2 className="animate-spin" />}
                Save name
              </Button>
            </form>
            <Separator />
            <form onSubmit={savePassword} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="newPassword">New password</Label>
                  <Input
                    id="newPassword"
                    type="password"
                    minLength={8}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="confirmPassword">Confirm password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    required
                    value={confirm}
                    onChange={(event) => setConfirm(event.target.value)}
                  />
                </div>
              </div>
              <Button type="submit" size="sm" disabled={savingPassword}>
                {savingPassword && <Loader2 className="animate-spin" />}
                Change password
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
