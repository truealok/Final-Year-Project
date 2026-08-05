import { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/hooks/use-auth";
import { Sidebar } from "@/layouts/sidebar";
import { Topbar } from "@/layouts/topbar";

/** Authenticated application shell: sidebar + topbar + routed content. */
export function AppLayout() {
  const { user, initializing } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("rc_sidebar_collapsed") === "1",
  );

  const toggleSidebar = () => {
    setCollapsed((current) => {
      localStorage.setItem("rc_sidebar_collapsed", current ? "0" : "1");
      return !current;
    });
  };

  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar collapsed={collapsed} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar sidebarCollapsed={collapsed} onToggleSidebar={toggleSidebar} />
        <main className="min-w-0 flex-1 p-4 sm:p-6">
          <div className="mx-auto w-full max-w-[1400px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
