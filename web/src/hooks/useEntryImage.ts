import { useEffect, useState } from "react";
import { fetchEntryImageBlob } from "../lib/api";
import { getAuthMode } from "../lib/authMode";

export function useEntryImage(accessToken: string | null, entryId: string | null, enabled = true) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const needsToken = getAuthMode() === "supabase";
    if (!entryId || !enabled || (needsToken && !accessToken)) {
      setUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setLoading(true);
    fetchEntryImageBlob(accessToken, entryId)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setUrl(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, entryId, enabled]);

  return { url, loading };
}
