/**
 * Typed fetch client for the ResiliChain backend.
 *
 * - Attaches the bearer access token
 * - Transparently refreshes an expired access token once (single-flight)
 * - Normalizes backend errors ({"error": {code, message, details}})
 */

import type { TokenPair } from "@/types";

const API_URL: string =
  (import.meta.env.VITE_API_URL || "").replace(/\/$/, "") || "/api/v1";

const ACCESS_KEY = "rc_access_token";
const REFRESH_KEY = "rc_refresh_token";

export const tokenStore = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: TokenPair) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  /** Return the raw Response (for file downloads). */
  raw?: boolean;
  /** Skip the 401 → refresh → retry cycle (used by auth endpoints). */
  skipRefresh?: boolean;
}

function buildUrl(
  path: string,
  params?: RequestOptions["params"],
): string {
  const url = `${API_URL}${path}`;
  if (!params) return url;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  const qs = query.toString();
  return qs ? `${url}?${qs}` : url;
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refresh = tokenStore.refresh;
      if (!refresh) return false;
      try {
        const res = await fetch(buildUrl("/auth/refresh"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const tokens = (await res.json()) as TokenPair;
        tokenStore.set(tokens);
        return true;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "http_error";
  let message = `Request failed (${res.status})`;
  let details: unknown;
  try {
    const body = await res.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details;
    } else if (body?.detail) {
      message = String(body.detail);
    }
  } catch {
    // non-JSON error body — keep defaults
  }
  return new ApiError(res.status, code, message, details);
}

export async function api<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, params, raw = false, skipRefresh = false } =
    options;

  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const access = tokenStore.access;
    if (access) headers["Authorization"] = `Bearer ${access}`;
    return fetch(buildUrl(path, params), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();

  if (res.status === 401 && !skipRefresh && tokenStore.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await doFetch();
    } else {
      tokenStore.clear();
      window.dispatchEvent(new CustomEvent("rc:unauthorized"));
    }
  }

  if (!res.ok) throw await parseError(res);
  if (raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
