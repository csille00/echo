import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageToolbar, ScanLink } from "../components/Layout";
import { useAuth } from "../lib/auth";
import { useEntries } from "../hooks/useEntries";
import { useEntryImage } from "../hooks/useEntryImage";
import { searchEntries } from "../lib/api";
import type { JournalEntry, SearchHit } from "../types";

function PhotoCell({
  entry,
  accessToken,
}: {
  entry: JournalEntry;
  accessToken: string | null;
}) {
  const canLoad =
    entry.processing_status === "completed" && !entry.storage_path.startsWith("pending/");
  const { url } = useEntryImage(accessToken, entry.id, canLoad);

  return (
    <Link className="photo-cell" to={`/entry/${entry.id}`}>
      <div
        className="photo-cell-inner"
        style={url ? { backgroundImage: `url(${url})`, backgroundSize: "cover" } : undefined}
      />
    </Link>
  );
}

export function BrowsePage() {
  const { accessToken, authenticated } = useAuth();
  const { entries, loading, error } = useEntries(accessToken);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const byYear = useMemo(() => {
    const map = new Map<string, JournalEntry[]>();
    const sorted = [...entries].sort((a, b) => entrySortKey(b).localeCompare(entrySortKey(a)));
    for (const e of sorted) {
      const y = (e.journal_date ?? e.created_at).slice(0, 4);
      const list = map.get(y) ?? [];
      list.push(e);
      map.set(y, list);
    }
    return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [entries]);

  const runSearch = async () => {
    if (!authenticated || !query.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      const results = await searchEntries(accessToken, query.trim());
      setHits(results);
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : "Search failed");
      setHits(null);
    } finally {
      setSearching(false);
    }
  };

  return (
    <>
      <PageToolbar title="Browse" action={<ScanLink />} />
      <div className="content">
        {error ? <p className="login-error">{error}</p> : null}
        <form
          className="search-row"
          onSubmit={(e) => {
            e.preventDefault();
            void runSearch();
          }}
        >
          <input
            className="search-field"
            type="search"
            placeholder="Search your journals"
            aria-label="Search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (!e.target.value.trim()) setHits(null);
            }}
          />
          <button className="btn btn-primary" type="submit" disabled={searching || !query.trim()}>
            {searching ? "…" : "Search"}
          </button>
        </form>

        {searchError ? <p className="login-error">{searchError}</p> : null}
        {hits ? (
          <div className="group">
            <p className="group-label">Search results</p>
            <div className="inset">
              {hits.length === 0 ? (
                <p className="footnote" style={{ padding: 16 }}>No matches.</p>
              ) : (
                hits.map((h) => (
                  <Link key={`${h.entry_id}-${h.chunk_text.slice(0, 24)}`} className="row" to={`/entry/${h.entry_id}`}>
                    <div className="row-body">
                      <p className="row-title">{h.journal_date ?? "Undated"}</p>
                      <p className="row-sub">{h.chunk_text}</p>
                    </div>
                    <span className="row-chevron">›</span>
                  </Link>
                ))
              )}
            </div>
          </div>
        ) : null}

        {loading ? <p className="footnote">Loading entries…</p> : null}
        {byYear.map(([year, list]) => (
          <div className="group" key={year}>
            <p className="group-label">{year}</p>
            <div className="photo-grid">
              {list.map((e) => (
                <PhotoCell key={e.id} entry={e} accessToken={accessToken} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function entrySortKey(e: JournalEntry): string {
  return e.journal_date ?? e.created_at;
}
