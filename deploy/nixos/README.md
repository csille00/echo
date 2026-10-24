# ellis-server: journal.ellisfam.space

Static site deploy matches [nixos-config `docs/deploying-a-static-site.md`](https://github.com/csille00/nixos-config).

1. Copy `journal.nix` → `nixos-config/modules/journal.nix`
2. Import in `hosts/ellis-server/configuration.nix`
3. In `cloudflare/hostnames.nix`, set:
   ```nix
   journal = { expose = "tailnet"; target = "http://localhost:8094"; protect = true; };
   ```
4. `sudo nixos-rebuild switch --flake .#ellis-server`

**Important:** Caddy only picks up `journal.nix` changes after rebuild. If `/api/*` returns 502, check
`curl http://127.0.0.1:8094/api/health` on ellis-server — the live config must proxy to
`192.168.1.54:8000`, not `100.70.187.21:8000`.

GitHub Actions (this repo) rsyncs `web/dist/` to `/var/www/journal/` on push to `main` after CI passes.
