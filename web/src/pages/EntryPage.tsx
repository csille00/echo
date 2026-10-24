import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { getEntry, updateEntry } from "../lib/api";
import { formatDisplayDate, toDateInputValue } from "../lib/dates";
import { useEntryImage } from "../hooks/useEntryImage";
import type { JournalEntry } from "../types";

export function EntryPage() {
  const { id } = useParams<{ id: string }>();
  const { accessToken, authenticated } = useAuth();
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [date, setDate] = useState("");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canImage =
    entry &&
    entry.processing_status === "completed" &&
    !entry.storage_path.startsWith("pending/");
  const { url: imageUrl } = useEntryImage(accessToken, id ?? null, Boolean(canImage));

  const load = async () => {
    if (!authenticated || !id) return;
    try {
      const e = await getEntry(accessToken, id);
      setEntry(e);
      setText(e.extracted_text ?? "");
      setDate(toDateInputValue(e.journal_date));
      setNotes(e.notes ?? "");
      setTags(e.tags.join(", "));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load entry");
    }
  };

  useEffect(() => {
    void load();
  }, [accessToken, id]);

  useEffect(() => {
    if (!entry) return;
    const active =
      entry.processing_status === "pending" || entry.processing_status === "processing";
    if (!active) return;
    const t = window.setInterval(() => void load(), 2500);
    return () => clearInterval(t);
  }, [entry?.processing_status, entry?.id]);

  const title =
    entry?.notes?.trim() ||
    entry?.storage_path.split("/").pop()?.replace(/^\d+_/, "") ||
    "Journal page";

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!authenticated || !id) return;
    setSaving(true);
    setError(null);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const updated = await updateEntry(
        accessToken,
        id,
        date
          ? {
              extracted_text: text,
              journal_date: date,
              notes: notes.trim() || null,
              tags: tagList,
            }
          : {
              extracted_text: text,
              clear_journal_date: true,
              notes: notes.trim() || null,
              tags: tagList,
            },
      );
      setEntry(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (!entry && !error) {
    return <p className="footnote" style={{ padding: 24 }}>Loading…</p>;
  }

  return (
    <>
      <header className="toolbar">
        <Link className="btn btn-ghost" to="/">‹ Calendar</Link>
        <div className="toolbar-actions">
          {editing ? (
            <button className="btn btn-ghost" type="button" onClick={() => setEditing(false)}>
              Cancel
            </button>
          ) : (
            <button className="btn btn-ghost" type="button" onClick={() => setEditing(true)}>
              Edit
            </button>
          )}
        </div>
      </header>

      <div className="content">
        {error ? <p className="login-error">{error}</p> : null}
        {entry?.processing_status === "failed" ? (
          <p className="login-error">{entry.error_message ?? "Processing failed"}</p>
        ) : null}
        {entry &&
        (entry.processing_status === "pending" || entry.processing_status === "processing") ? (
          <p className="status-processing footnote">Recognizing handwriting…</p>
        ) : null}

        <p className="footnote">{formatDisplayDate(entry?.journal_date ?? null)}</p>
        <h1 className="title-2" style={{ marginBottom: 24 }}>{title}</h1>

        {editing ? (
          <form onSubmit={(e) => void save(e)}>
            <div className="group">
              <p className="group-label">Date</p>
              <input type="date" value={date} onChange={(ev) => setDate(ev.target.value)} />
            </div>
            <div className="group">
              <p className="group-label">Title / notes</p>
              <input type="text" value={notes} onChange={(ev) => setNotes(ev.target.value)} />
            </div>
            <div className="group">
              <p className="group-label">Tags</p>
              <input type="text" value={tags} onChange={(ev) => setTags(ev.target.value)} />
            </div>
            <div className="group">
              <p className="group-label">Recognized text</p>
              <textarea
                className="text-editor"
                value={text}
                onChange={(ev) => setText(ev.target.value)}
                aria-label="Edit recognized text"
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </form>
        ) : (
          <div className="entry-layout">
            <div
              className="entry-image"
              style={
                imageUrl
                  ? { backgroundImage: `url(${imageUrl})`, backgroundSize: "contain", backgroundRepeat: "no-repeat", backgroundPosition: "center" }
                  : undefined
              }
            >
              {!imageUrl ? "Page scan" : null}
            </div>
            <div>
              <div className="entry-prose">{entry?.extracted_text?.trim() || "No text yet."}</div>
              <p className="caption" style={{ marginTop: 24 }}>
                Recognized text
                {entry?.updated_at ? ` · updated ${entry.updated_at.slice(0, 10)}` : ""}
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
