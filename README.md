# Journal Search

AI-powered journal OCR and semantic search. Designed to run **self-hosted** — your Postgres, your files, your models. A new install uses Tesseract and Ollama. Google Cloud Vision is optional.

## Self-hosted stack

| Component | Default | Runs on |
|-----------|---------|---------|
| API + web UI | FastAPI + DBOS, UI served from `WEB_ROOT` | Your server / `docker compose` |
| Database | PostgreSQL + pgvector | `db` service or your Postgres |
| Workflow durability | DBOS (system tables in the same database) | Same Postgres |
| Object storage | Local filesystem (or Supabase Storage) | `data/uploads` or Supabase bucket |
| Auth | Email and password (first visitor creates the admin) | `.env` `AUTH_BACKEND=local` |
| Realtime | None (default) or Supabase `postgres_changes` | `.env` `REALTIME_BACKEND` |
| Embeddings | Ollama `nomic-embed-text` (768 dimensions) | `ollama` service |
| LLM cleanup | Off by default (optional Ollama) | `ollama` service if enabled |
| OCR | Tesseract (or Google Vision / Surya) | See `.env` |

DBOS Conductor (workflow ops UI) is optional and [self-hosted](https://docs.dbos.dev/production/hosting-conductor) — no DBOS Cloud required.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up
```

Open `http://localhost:8000`. The first person to sign up becomes the admin. Further signups are closed; an admin can add accounts with `POST /api/v1/auth/users`.

The API applies `src/journal_search/migrations/` on startup. Inside Compose it listens on `0.0.0.0`; on a host it binds to `127.0.0.1` until a reverse proxy is in front.

`AUTH_BACKEND=dev_header` is for local development only. The Vite dev server is documented in `web/README.md`.

Optional SSO is generic OpenID Connect: set `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and `PUBLIC_URL`. The login page gains a button that works with any provider that publishes a discovery document. `AUTH_BACKEND=authentik` is the older reverse-proxy header mode, separate from that login.

## Layering

Third-party integrations live behind **ports** (`src/journal_search/ports/`) with **adapters** per vendor. Swap backends via `.env` without touching API or workflow code:

| Concern | Port | Adapters |
|---------|------|----------|
| Database | SQLAlchemy + repository | Plain PostgreSQL (Supabase Postgres = same `DATABASE_URL`) |
| Storage | `StorageProvider` | `local`, `supabase` |
| Auth | `AuthProvider` | `local`, `dev_header`, `authentik`, `supabase` |
| Realtime | `RealtimeProvider` | `none`, `supabase` |
| OCR / embeddings / LLM | respective ports | Google Vision, Ollama, etc. |

Supabase SDK usage is confined to `adapters/supabase/`. Example: Supabase DB + local storage + local accounts + no realtime:

```env
DATABASE_URL=postgresql+asyncpg://...
STORAGE_BACKEND=local
AUTH_BACKEND=local
REALTIME_BACKEND=none
```

## NixOS

The flake provides the package and a module. In your NixOS flake:

```nix
{
  inputs.journal-search.url = "github:csille00/journal-search";

  outputs = { nixpkgs, journal-search, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      modules = [
        journal-search.nixosModules.default
        ./journal.nix
      ];
    };
  };
}
```

`journal.nix` is the host-specific file. A starting point is `nix/example.nix`:

```nix
{
  services.journal-search = {
    enable = true;
    environmentFile = "/var/lib/journal-search/secrets.env";
    settings = {
      PUBLIC_URL = "https://journal.example.com";
      SESSION_COOKIE_SECURE = true;
    };
  };
}
```

That creates a `journal_search` system user, a PostgreSQL database with pgvector, an Ollama service with `nomic-embed-text`, and a systemd service on `127.0.0.1:8000`. The module does not configure a web server. Point Caddy, nginx, Traefik, or any other reverse proxy at that address. Behind HTTPS, set `PUBLIC_URL` and `SESSION_COOKIE_SECURE` as above so OIDC redirects and the session cookie match the public site. The first signup is the admin. Secrets such as `OIDC_CLIENT_SECRET` go in the environment file, not in the Nix file.

`settings` overrides the defaults (`AUTH_BACKEND`, `OCR_PROVIDER`, `OIDC_ISSUER`, and the rest of the variables in `.env.example`). Set `database.createLocally = false` and put `DATABASE_URL` in the environment file to keep using an existing database. Set `ollama.enable = false` when embeddings are not local. Header auth such as `AUTH_BACKEND=authentik` stays in the reverse proxy, which injects the user-id header before the request reaches the service.

## Development (Nix)

```bash
nix-shell --run "uv pip install -e '.[dev]'"
cp .env.example .env
docker compose up db ollama   # Postgres + Ollama only
python -m journal_search
```

## Usage

```bash
python -m journal_search
python scripts/smoke_pipeline.py path/to/page.jpg
```
