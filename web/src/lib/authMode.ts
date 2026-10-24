export type AuthMode = "authentik" | "dev" | "supabase";

export function getAuthMode(): AuthMode {
  const raw = import.meta.env.VITE_AUTH_MODE;
  if (raw === "dev" || raw === "supabase" || raw === "authentik") {
    return raw;
  }
  return "authentik";
}

export function usesCookieSession(): boolean {
  return getAuthMode() === "authentik";
}
