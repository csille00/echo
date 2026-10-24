import { Link } from "react-router-dom";
import { formatShortDate } from "../lib/dates";
import type { JournalEntry } from "../types";

function statusClass(status: JournalEntry["processing_status"]): string {
  if (status === "completed") return "";
  if (status === "failed") return "status-processing";
  return "status-processing";
}

function statusLabel(entry: JournalEntry): string {
  if (entry.processing_status === "processing" || entry.processing_status === "pending") {
    return "Processing…";
  }
  if (entry.processing_status === "failed") {
    return entry.error_message ?? "Failed";
  }
  const text = entry.extracted_text?.trim();
  if (!text) return "No text yet";
  return text.length > 72 ? `${text.slice(0, 72)}…` : text;
}

export function EntryRow({ entry }: { entry: JournalEntry }) {
  const title =
    entry.notes?.trim() ||
    entry.storage_path.split("/").pop()?.replace(/^\d+_/, "") ||
    "Journal page";

  return (
    <Link className="row" to={`/entry/${entry.id}`}>
      <div className="row-thumb" />
      <div className="row-body">
        <p className="row-title">{title}</p>
        <p className={`row-sub ${statusClass(entry.processing_status)}`}>
          {formatShortDate(entry.journal_date)} · {statusLabel(entry)}
        </p>
      </div>
      <span className="row-chevron">›</span>
    </Link>
  );
}
