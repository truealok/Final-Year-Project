/** Authentication provider: session bootstrap, login/signup/logout. */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { tokenStore } from "@/services/api";
import { AuthApi } from "@/services/endpoints";
import type { User, UserRole } from "@/types";

interface AuthContextValue {
  user: User | null;
  /** True while the stored session is being validated on first load. */
  initializing: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (email: string, password: string, fullName: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (...roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  // Validate any stored session on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!tokenStore.access && !tokenStore.refresh) {
        setInitializing(false);
        return;
      }
      try {
        const me = await AuthApi.me();
        if (!cancelled) setUser(me);
      } catch {
        tokenStore.clear();
      } finally {
        if (!cancelled) setInitializing(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Force logout when a refresh cycle fails anywhere in the app.
  useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener("rc:unauthorized", handler);
    return () => window.removeEventListener("rc:unauthorized", handler);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await AuthApi.login(email, password);
    tokenStore.set(response.tokens);
    setUser(response.user);
    return response.user;
  }, []);

  const signup = useCallback(
    async (email: string, password: string, fullName: string) => {
      const response = await AuthApi.signup(email, password, fullName);
      tokenStore.set(response.tokens);
      setUser(response.user);
      return response.user;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await AuthApi.logout();
    } catch {
      // Even if the server call fails, clear the local session.
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    setUser(await AuthApi.me());
  }, []);

  const hasRole = useCallback(
    (...roles: UserRole[]) => (user ? roles.includes(user.role) : false),
    [user],
  );

  const value = useMemo(
    () => ({ user, initializing, login, signup, logout, refreshUser, hasRole }),
    [user, initializing, login, signup, logout, refreshUser, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
