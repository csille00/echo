# ellis-server: journal.ellisfam.space

Static site deploy matches [nixos-config `docs/deploying-a-static-site.md`](https://github.com/csille00/nixos-config).

1. Copy `journal.nix` → `nixos-config/modules/journal.nix`
2. Import in `hosts/ellis-server/configuration.nix`
3. In `cloudflare/hostnames.nix`, set:
   ```nix
   journal = { expose = "tailnet"; target = "http://localhost:8094"; protect = true; };
   ```
4. `sudo nixos-rebuild switch --flake .#ellis-server`

GitHub Actions (this repo) rsyncs `web/dist/` to `/var/www/journal/` on push to `main` after CI passes.
