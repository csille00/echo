# Journal Search

AI-powered journal OCR and semantic search. Designed to run **self-hosted** — your Postgres, your files, your models. **Google Cloud Vision** is the only external cloud dependency (for OCR).

## Self-hosted stack

| Component | Default | Runs on |
|-----------|---------|---------|
| API + workflows | FastAPI + DBOS | Your server / `docker compose` |
| Database | PostgreSQL + pgvector | `db` service or your Postgres |
| Workflow durability | DBOS (system DB auto-created) | Same Postgres |
| Object storage | Local filesystem (or Supabase Storage) | `data/uploads` or Supabase bucket |
| Auth | Dev header, Authentik SSO, or Supabase JWT | `.env` `AUTH_BACKEND` |
| Realtime | None (default) or Supabase `postgres_changes` | `.env` `REALTIME_BACKEND` |
| Embeddings | Google `text-embedding-004` (default) or Ollama | Google API or `ollama` service |
| LLM cleanup | Off by default (optional Ollama) | `ollama` service if enabled |
| OCR | Google Vision (default) or Tesseract/Surya on-prem | See `.env` |

DBOS Conductor (workflow ops UI) is optional and [self-hosted](https://docs.dbos.dev/production/hosting-conductor) — no DBOS Cloud required.

## Quick start (Docker)

```bash
cp .env.example .env
# Add Google Vision credentials to .env, then:
docker compose up
```

API: `http://localhost:8000` — upload via `POST /api/v1/entries/upload` with header `X-User-ID: <uuid>` (when `AUTH_BACKEND=dev_header`).

A React UI lives in `web/` for local development (see `web/README.md`). Production hosting is not wired in this repo.

## Layering

Third-party integrations live behind **ports** (`src/journal_search/ports/`) with **adapters** per vendor. Swap backends via `.env` without touching API or workflow code:

| Concern | Port | Adapters |
|---------|------|----------|
| Database | SQLAlchemy + repository | Plain PostgreSQL (Supabase Postgres = same `DATABASE_URL`) |
| Storage | `StorageProvider` | `local`, `supabase` |
| Auth | `AuthProvider` | `dev_header`, `authentik`, `supabase` |
| Realtime | `RealtimeProvider` | `none`, `supabase` |
| OCR / embeddings / LLM | respective ports | Google Vision, Ollama, etc. |

Supabase SDK usage is confined to `adapters/supabase/`. Example: Supabase DB + local storage + dev auth + no realtime:

```env
DATABASE_URL=postgresql+asyncpg://...
STORAGE_BACKEND=local
AUTH_BACKEND=dev_header
REALTIME_BACKEND=none
```

## Development (Nix)

```bash
nix-shell --run "uv pip install -e '.[dev,ocr-google-vision,llm-cleanup]'"
cp .env.example .env
docker compose up db ollama   # Postgres + Ollama only
python -m journal_search
```

## Usage

```bash
python -m journal_search
python scripts/smoke_pipeline.py path/to/page.jpg
```
