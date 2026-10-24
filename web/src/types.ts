export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface JournalEntry {
  id: string;
  storage_path: string;
  extracted_text: string | null;
  journal_date: string | null;
  tags: string[];
  notes: string | null;
  processing_status: ProcessingStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SearchHit {
  entry_id: string;
  chunk_text: string;
  similarity: number;
  journal_date: string | null;
  tags: string[];
}
