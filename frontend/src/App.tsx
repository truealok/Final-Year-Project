import { Route, Routes } from "react-router-dom";

import { AppLayout } from "@/layouts/app-layout";
import { AuthLayout } from "@/layouts/auth-layout";
import AlertsPage from "@/pages/alerts";
import AnalyticsPage from "@/pages/analytics";
import ForgotPasswordPage from "@/pages/auth/forgot-password";
import LoginPage from "@/pages/auth/login";
import ResetPasswordPage from "@/pages/auth/reset-password";
import SignupPage from "@/pages/auth/signup";
import DashboardPage from "@/pages/dashboard";
import DigitalTwinPage from "@/pages/digital-twin";
import ForecastPage from "@/pages/forecast";
import InventoryPage from "@/pages/inventory";
import NotFoundPage from "@/pages/not-found";
import ProfilePage from "@/pages/profile";
import RecommendationsPage from "@/pages/recommendations";
import ReportsPage from "@/pages/reports";
import SettingsPage from "@/pages/settings";
import SimulationPage from "@/pages/simulation";
import SuppliersPage from "@/pages/suppliers";
import WarehousesPage from "@/pages/warehouses";

export default function App() {
  return (
    <Routes>
      {/* Public auth routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* Authenticated application */}
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/forecast" element={<ForecastPage />} />
        <Route path="/digital-twin" element={<DigitalTwinPage />} />
        <Route path="/simulation" element={<SimulationPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/suppliers" element={<SuppliersPage />} />
        <Route path="/warehouses" element={<WarehousesPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
