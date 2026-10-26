import { useCallback, useEffect, useState } from "react";
import { listEntries } from "../lib/api";
import { getAuthMode } from "../lib/authMode";
import type { JournalEntry } from "../types";

export function useEntries(accessToken: string | null) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (accessToken === null && getAuthMode() === "supabase") return;
    try {
      const data = await listEntries(accessToken);
      setEntries(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load entries");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const hasActiveProcessing = entries.some(
    (e) => e.processing_status === "pending" || e.processing_status === "processing",
  );

  useEffect(() => {
    if (!hasActiveProcessing) return;
    const id = window.setInterval(() => void refresh(), 2500);
    return () => clearInterval(id);
  }, [hasActiveProcessing, refresh]);

  return { entries, loading, error, refresh };
}
