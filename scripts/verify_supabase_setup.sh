#!/usr/bin/env bash
# Verify Supabase prerequisites for journal-search (run on the Supabase host).
set -euo pipefail

DB_CONTAINER="${DB_CONTAINER:-supabase-journal-search-db}"

echo "==> Checking pgvector"
docker exec "$DB_CONTAINER" psql -U postgres -tAc \
  "SELECT extversion FROM pg_extension WHERE extname = 'vector';"

echo "==> Checking tables"
docker exec "$DB_CONTAINER" psql -U postgres -c "\dt public.*"

echo "==> Checking vector index"
docker exec "$DB_CONTAINER" psql -U postgres -tAc \
  "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_embeddings_vector';"

echo "==> Checking storage bucket"
docker exec "$DB_CONTAINER" psql -U postgres -tAc \
  "SELECT id FROM storage.buckets WHERE id = 'journal-pages';"

echo "==> Checking realtime publication"
docker exec "$DB_CONTAINER" psql -U postgres -tAc \
  "SELECT tablename FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'entries';"

echo "OK — Supabase prerequisites look good."
