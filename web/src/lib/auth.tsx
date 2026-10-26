import type { Session } from "@supabase/supabase-js";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, fetchAuthConfig, fetchWhoami, login, logout, registerAccount } from "./api";
import {
  authModeFromBackend,
  fallbackAuthMode,
  getAuthMode,
  setAuthMode,
  type AuthMode,
} from "./authMode";
import { supabase } from "./supabase";

type AuthContextValue = {
  /** True when the API accepts requests for this user. */
  authenticated: boolean;
  userId: string | null;
  /** False when the API could not be contacted. */
  apiReachable: boolean;
  /** True when no local account exists yet. */
  needsSetup: boolean;
  oidcEnabled: boolean;
  oidcDisplayName: string;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Supabase access token only; null for cookie sessions. */
  accessToken: string | null;
  authMode: AuthMode;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function loadSessionUser(): Promise<string | null> {
  const me = await fetchWhoami(null);
  return me.user_id;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authMode, setMode] = useState<AuthMode>("local");
  const [session, setSession] = useState<Session | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [apiReachable, setApiReachable] = useState(true);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [oidcEnabled, setOidcEnabled] = useState(false);
  const [oidcDisplayName, setOidcDisplayName] = useState("SSO");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const finish = () => {
      if (!cancelled) setLoading(false);
    };

    const applyMode = (next: AuthMode) => {
      setAuthMode(next);
      if (!cancelled) setMode(next);
    };

    void (async () => {
      let next = fallbackAuthMode();
      try {
        const config = await fetchAuthConfig();
        next = authModeFromBackend(config.auth_backend);
        applyMode(next);
        if (!cancelled) {
          setNeedsSetup(config.needs_setup);
          setOidcEnabled(Boolean(config.oidc_enabled));
          setOidcDisplayName(config.oidc_display_name || "SSO");
          setApiReachable(true);
        }
      } catch (err) {
        applyMode(next);
        const reachable = err instanceof ApiError;
        if (!cancelled) setApiReachable(reachable);
        if (!reachable) {
          finish();
          return;
        }
      }

      if (next === "supabase") {
        const { data } = await supabase.auth.getSession();
        if (!cancelled) {
          setSession(data.session);
          setUserId(data.session?.user.id ?? null);
        }
        finish();
        return;
      }

      if (next === "dev") {
        const stored = sessionStorage.getItem("journal-dev-user-id");
        const fromEnv = import.meta.env.VITE_DEV_USER_ID;
        if (!cancelled) setUserId(stored || fromEnv || null);
        finish();
        return;
      }

      try {
        const id = await loadSessionUser();
        if (!cancelled) {
          setUserId(id);
          setApiReachable(true);
        }
      } catch (err) {
        if (!cancelled) {
          setUserId(null);
          setApiReachable(!(err instanceof ApiError) ? false : err.status < 500);
        }
      }
      finish();
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (authMode !== "supabase") return undefined;
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setUserId(next?.user.id ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, [authMode]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (getAuthMode() === "supabase") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        return;
      }
      if (getAuthMode() !== "local") {
        throw new Error("Password sign-in is not used in this auth mode");
      }
      await login(email, password);
      setUserId(await loadSessionUser());
      setNeedsSetup(false);
      setApiReachable(true);
    },
    [],
  );

  const register = useCallback(async (email: string, password: string, name: string) => {
    await registerAccount({ email, password, name });
    setUserId(await loadSessionUser());
    setNeedsSetup(false);
    setApiReachable(true);
  }, []);

  const signOut = useCallback(async () => {
    const mode = getAuthMode();
    if (mode === "supabase") {
      await supabase.auth.signOut();
      return;
    }
    if (mode === "dev") {
      sessionStorage.removeItem("journal-dev-user-id");
      setUserId(import.meta.env.VITE_DEV_USER_ID || null);
      return;
    }
    if (mode === "local") {
      await logout();
      setUserId(null);
      return;
    }
    const logoutUrl = import.meta.env.VITE_AUTHENTIK_LOGOUT_URL;
    if (logoutUrl) {
      window.location.href = logoutUrl;
      return;
    }
    window.location.reload();
  }, []);

  const authenticated =
    authMode === "authentik" ? true : authMode === "dev" ? Boolean(userId) : authMode === "local" ? Boolean(userId) : Boolean(session);

  const value = useMemo(
    () => ({
      authenticated,
      userId,
      apiReachable,
      needsSetup,
      oidcEnabled,
      oidcDisplayName,
      loading,
      signIn,
      register,
      signOut,
      accessToken: authMode === "supabase" ? (session?.access_token ?? null) : null,
      authMode,
    }),
    [
      authenticated,
      userId,
      apiReachable,
      needsSetup,
      oidcEnabled,
      oidcDisplayName,
      loading,
      signIn,
      register,
      signOut,
      session,
      authMode,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

/** Persist a dev user id chosen on the login screen. */
export function setDevUserId(id: string) {
  sessionStorage.setItem("journal-dev-user-id", id);
}
