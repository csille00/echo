import type { JournalEntry, SearchHit } from "../types";
import { getAuthMode, usesCookieSession } from "./authMode";

const base = () => import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function authHeaders(accessToken: string | null): Record<string, string> {
  const mode = getAuthMode();
  if (mode === "dev") {
    const userId =
      sessionStorage.getItem("journal-dev-user-id") || import.meta.env.VITE_DEV_USER_ID;
    if (userId) return { "X-User-ID": userId };
    return {};
  }
  if (mode === "supabase" && accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return {};
}

async function apiFetch<T>(
  path: string,
  accessToken: string | null,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    ...authHeaders(accessToken),
  };
  if (init?.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${base()}${path}`, {
    ...init,
    credentials: usesCookieSession() ? "include" : "same-origin",
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail ?? detail;
    } catch {
      /* plain */
    }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type AuthConfig = {
  auth_backend: string;
  needs_setup: boolean;
  oidc_enabled?: boolean;
  oidc_display_name?: string;
};

export function oidcStartUrl(): string {
  const root = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";
  return `${root}/api/v1/auth/oidc/start`;
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const res = await fetch(`${base()}/api/v1/auth/config`, { credentials: "include" });
  if (!res.ok) throw new ApiError("Auth config unavailable", res.status);
  return res.json() as Promise<AuthConfig>;
}

export async function fetchWhoami(accessToken: string | null): Promise<{ user_id: string }> {
  return apiFetch("/api/v1/auth/whoami", accessToken);
}

export async function login(email: string, password: string): Promise<void> {
  await apiFetch("/api/v1/auth/login", null, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function registerAccount(body: {
  email: string;
  name: string;
  password: string;
}): Promise<void> {
  await apiFetch("/api/v1/auth/register", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function logout(): Promise<void> {
  await apiFetch("/api/v1/auth/logout", null, { method: "POST" });
}

export async function listEntries(accessToken: string | null): Promise<JournalEntry[]> {
  return apiFetch("/api/v1/entries/?limit=200", accessToken);
}

export async function getEntry(accessToken: string | null, id: string): Promise<JournalEntry> {
  return apiFetch(`/api/v1/entries/${id}`, accessToken);
}

export async function updateEntry(
  accessToken: string | null,
  id: string,
  body: {
    journal_date?: string | null;
    clear_journal_date?: boolean;
    extracted_text?: string;
    tags?: string[];
    notes?: string | null;
  },
): Promise<JournalEntry> {
  return apiFetch(`/api/v1/entries/${id}`, accessToken, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function uploadEntry(
  accessToken: string | null,
  file: File,
  opts?: { journalDate?: string; tags?: string; notes?: string },
): Promise<{ entry_id: string }> {
  const form = new FormData();
  form.append("file", file);
  if (opts?.journalDate) form.append("journal_date", opts.journalDate);
  if (opts?.tags) form.append("tags", opts.tags);
  if (opts?.notes) form.append("notes", opts.notes);
  const data = await apiFetch<{ entry_id: string }>("/api/v1/entries/upload", accessToken, {
    method: "POST",
    body: form,
  });
  return data;
}

export async function searchEntries(
  accessToken: string | null,
  query: string,
  limit = 8,
): Promise<SearchHit[]> {
  const data = await apiFetch<{ results: SearchHit[] }>("/api/v1/search/", accessToken, {
    method: "POST",
    body: JSON.stringify({ query, limit }),
  });
  return data.results;
}

export async function fetchEntryImageBlob(
  accessToken: string | null,
  entryId: string,
): Promise<Blob> {
  const res = await fetch(`${base()}/api/v1/entries/${entryId}/image`, {
    credentials: usesCookieSession() ? "include" : "same-origin",
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new ApiError("Image unavailable", res.status);
  return res.blob();
}
