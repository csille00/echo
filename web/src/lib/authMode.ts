export type AuthMode = "local" | "authentik" | "dev" | "supabase";

let mode: AuthMode = "local";

export function getAuthMode(): AuthMode {
  return mode;
}

export function setAuthMode(next: AuthMode): void {
  mode = next;
}

export function authModeFromBackend(backend: string): AuthMode {
  if (backend === "dev_header") return "dev";
  if (backend === "authentik" || backend === "supabase" || backend === "local") {
    return backend;
  }
  return "local";
}

/** Used when /api/v1/auth/config cannot be loaded (older API, or the API is down). */
export function fallbackAuthMode(): AuthMode {
  const raw = import.meta.env.VITE_AUTH_MODE;
  if (raw === "dev" || raw === "supabase" || raw === "authentik" || raw === "local") {
    return raw;
  }
  return "local";
}

export function usesCookieSession(): boolean {
  const current = getAuthMode();
  return current === "local" || current === "authentik";
}
