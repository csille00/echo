# Echo

I built this project because I think writing in a paper journal is theraputic and should not go anywhere in the computer age, but I deeply fear something happening to my precious journals. The intent is to provide a clean and simple way to digitize journal entries, complete with OCR processing, and embedding to allow for semantic search across multiple entries. 

Scan journal pages, then search them. A new install uses Postgres, files on disk, Tesseract, and Ollama.

## Docker

```bash
cp .env.example .env
docker compose up
```

Open http://localhost:8000. The first account is the admin. Signups close after that. An admin adds users with `POST /api/v1/auth/users`.

Migrations run on startup. Other backends and OIDC are in `.env.example`. `AUTH_BACKEND=dev_header` is for development. The Vite app is in `web/`.

DBOS runs in this process and uses the same database. Conductor is optional: `docker-compose.dbos.yml`.

## NixOS

```nix
{
  inputs.echo.url = "github:csille00/journal-search";

  outputs = { nixpkgs, echo, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      modules = [
        echo.nixosModules.default
        ./echo.nix
      ];
    };
  };
}
```

Copy `nix/example.nix` to `echo.nix`. The service listens on `127.0.0.1:8000`, with Postgres (pgvector) and Ollama (`nomic-embed-text`). Point your reverse proxy at that address. Behind HTTPS, set `PUBLIC_URL` and `SESSION_COOKIE_SECURE`. Secrets go in `environmentFile`.

Set `database.createLocally = false` and `DATABASE_URL` in the environment file to use an existing database. Set `ollama.enable = false` to skip local embeddings.

## Development

```bash
nix-shell --run "uv pip install -e '.[dev]'"
cp .env.example .env
docker compose up db ollama
python -m echo
```

```bash
python scripts/smoke_pipeline.py path/to/page.jpg
```
