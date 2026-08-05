import { Copy, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

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
import { AuthApi } from "@/services/endpoints";
import { ApiError } from "@/services/api";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await AuthApi.forgotPassword(email);
      setDone(true);
      setResetToken(response.reset_token);
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "Something went wrong.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Forgot password</CardTitle>
        <CardDescription>
          Enter your email and we&apos;ll start a password reset.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!done ? (
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" />}
              Send reset instructions
            </Button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              If the email exists, a password reset has been initiated.
            </p>
            {resetToken && (
              <div className="rounded-md border bg-muted/50 p-3">
                <p className="text-xs font-medium">
                  Development mode — your reset token:
                </p>
                <div className="mt-1.5 flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate rounded bg-background px-2 py-1 text-xs">
                    {resetToken}
                  </code>
                  <Button
                    type="button"
                    size="icon"
                    variant="outline"
                    className="h-7 w-7 shrink-0"
                    onClick={() => {
                      navigator.clipboard.writeText(resetToken);
                      toast.success("Token copied.");
                    }}
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <Button
                  type="button"
                  className="mt-3 w-full"
                  size="sm"
                  onClick={() =>
                    navigate(
                      `/reset-password?token=${encodeURIComponent(resetToken)}`,
                    )
                  }
                >
                  Continue to reset
                </Button>
              </div>
            )}
          </div>
        )}
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Remembered it?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
