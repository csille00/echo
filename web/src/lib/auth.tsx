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
import { fetchWhoami } from "./api";
import { getAuthMode } from "./authMode";
import { supabase } from "./supabase";

type AuthContextValue = {
  /** True when the API accepts requests for this user. */
  authenticated: boolean;
  userId: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Supabase access token only; null for Authentik cookie SSO. */
  accessToken: string | null;
  authMode: ReturnType<typeof getAuthMode>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const authMode = getAuthMode();
  const [session, setSession] = useState<Session | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshAuthentik = useCallback(async () => {
    try {
      const me = await fetchWhoami(null);
      setUserId(me.user_id);
    } catch {
      setUserId(null);
    }
  }, []);

  useEffect(() => {
    if (authMode === "supabase") {
      supabase.auth.getSession().then(({ data }) => {
        setSession(data.session);
        setUserId(data.session?.user.id ?? null);
        setLoading(false);
      });
      const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
        setSession(s);
        setUserId(s?.user.id ?? null);
      });
      return () => sub.subscription.unsubscribe();
    }

    if (authMode === "authentik") {
      void refreshAuthentik().finally(() => setLoading(false));
      return;
    }

    // dev: user id from env; optional override in sessionStorage
    const stored = sessionStorage.getItem("journal-dev-user-id");
    const fromEnv = import.meta.env.VITE_DEV_USER_ID;
    setUserId(stored || fromEnv || null);
    setLoading(false);
    return undefined;
  }, [authMode, refreshAuthentik]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (authMode !== "supabase") {
        throw new Error("Password sign-in is only used with VITE_AUTH_MODE=supabase");
      }
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
    },
    [authMode],
  );

  const signOut = useCallback(async () => {
    if (authMode === "supabase") {
      await supabase.auth.signOut();
      return;
    }
    if (authMode === "dev") {
      sessionStorage.removeItem("journal-dev-user-id");
      setUserId(import.meta.env.VITE_DEV_USER_ID || null);
      return;
    }
    const logout = import.meta.env.VITE_AUTHENTIK_LOGOUT_URL;
    if (logout) {
      window.location.href = logout;
      return;
    }
    window.location.reload();
  }, [authMode]);

  const authenticated =
    authMode === "authentik" ? userId !== null : authMode === "dev" ? Boolean(userId) : Boolean(session);

  const value = useMemo(
    () => ({
      authenticated,
      userId,
      loading,
      signIn,
      signOut,
      accessToken: authMode === "supabase" ? (session?.access_token ?? null) : null,
      authMode,
    }),
    [authenticated, userId, loading, signIn, signOut, session, authMode],
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
