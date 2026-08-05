import { Boxes } from "lucide-react";
import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/hooks/use-auth";

/** Centered card shell for the authentication pages. */
export function AuthLayout() {
  const { user, initializing } = useAuth();

  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (user) return <Navigate to="/" replace />;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-10">
      <div className="mb-6 flex items-center gap-2.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Boxes className="h-5 w-5" />
        </div>
        <div className="leading-tight">
          <p className="text-base font-semibold">ResiliChain AI</p>
          <p className="text-xs text-muted-foreground">
            Supply Chain Forecasting &amp; Resilience
          </p>
        </div>
      </div>
      <Outlet />
      <p className="mt-8 text-center text-xs text-muted-foreground">
        Enterprise supply chain intelligence platform
      </p>
    </div>
  );
}
