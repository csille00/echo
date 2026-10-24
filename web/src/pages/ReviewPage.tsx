import { FormEvent, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { uploadEntry } from "../lib/api";

export function ReviewPage() {
  const { accessToken, authenticated } = useAuth();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [journalDate, setJournalDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPick = (f: File | null) => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  };

  const onSubmit = async (e: FormEvent, another = false) => {
    e.preventDefault();
    if (!authenticated || !file) return;
    setBusy(true);
    setError(null);
    try {
      const { entry_id } = await uploadEntry(accessToken, file, {
        journalDate,
        notes: notes.trim() || undefined,
        tags: tags.trim() || undefined,
      });
      if (another) {
        onPick(null);
        if (fileRef.current) fileRef.current.value = "";
        setNotes("");
      } else {
        navigate(`/entry/${entry_id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <header className="toolbar">
        <Link className="btn btn-ghost" to="/">Cancel</Link>
        <span className="title-3">Scan</span>
        <button
          className="btn btn-primary"
          type="button"
          disabled={!file || busy}
          onClick={(e) => void onSubmit(e as unknown as FormEvent)}
        >
          {busy ? "Uploading…" : "Upload"}
        </button>
      </header>

      <div className="content">
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ marginBottom: 16 }}
          onChange={(e) => onPick(e.target.files?.[0] ?? null)}
        />

        <div
          className="scan-preview"
          style={
            preview
              ? { backgroundImage: `url(${preview})`, backgroundSize: "contain", backgroundRepeat: "no-repeat", backgroundPosition: "center" }
              : undefined
          }
        >
          {!preview ? "Choose a photo of a journal page" : null}
        </div>

        {error ? <p className="login-error">{error}</p> : null}

        <div className="group">
          <div className="inset">
            <label className="row" style={{ cursor: "pointer" }}>
              <div className="row-body">
                <p className="row-title">Date</p>
              </div>
              <input
                type="date"
                value={journalDate}
                onChange={(e) => setJournalDate(e.target.value)}
                style={{ border: "none", background: "transparent", color: "var(--label-secondary)" }}
              />
            </label>
            <label className="row">
              <div className="row-body">
                <p className="row-title">Title / notes</p>
              </div>
              <input
                type="text"
                placeholder="Optional"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                style={{ border: "none", background: "transparent", textAlign: "right", flex: 1 }}
              />
            </label>
            <label className="row">
              <div className="row-body">
                <p className="row-title">Tags</p>
              </div>
              <input
                type="text"
                placeholder="comma-separated"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                style={{ border: "none", background: "transparent", textAlign: "right", flex: 1 }}
              />
            </label>
          </div>
        </div>

        <p className="caption">
          After upload, OCR runs in the background. Open the entry to review and fix recognized text.
        </p>

        <button
          className="btn btn-ghost"
          type="button"
          disabled={!file || busy}
          style={{ marginTop: 8 }}
          onClick={(e) => void onSubmit(e as unknown as FormEvent, true)}
        >
          Upload and scan another
        </button>
      </div>
    </>
  );
}
