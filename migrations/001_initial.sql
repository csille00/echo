-- Initial schema for journal-search (self-hosted PostgreSQL + pgvector)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    storage_path TEXT NOT NULL,
    extracted_text TEXT,
    ocr_model TEXT,
    ocr_confidence REAL,
    journal_date DATE,
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entries_user_id ON entries(user_id);
CREATE INDEX IF NOT EXISTS idx_entries_user_date ON entries(user_id, journal_date DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_entries_user_status ON entries(user_id, processing_status);

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text TEXT NOT NULL,
    embedding vector,
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_entry_id ON embeddings(entry_id);

CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entries_updated_at
    BEFORE UPDATE ON entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE entries IS 'Journal page entries with OCR-extracted text';
COMMENT ON TABLE embeddings IS 'Vector embeddings for semantic search';
COMMENT ON COLUMN entries.user_id IS 'Owner of this entry - all queries must filter by this';
COMMENT ON COLUMN embeddings.user_id IS 'Denormalized from entries for efficient filtered vector search';
