#!/usr/bin/env python3
"""Apply journal static-site module to nixos-config on ellis-server (run on that host)."""

from pathlib import Path

REPO = Path.home() / "nixos-config"
MODULE_DST = REPO / "modules" / "journal.nix"
# When run from a journal-search checkout on the server:
MODULE_SRC = Path(__file__).resolve().parents[1] / "deploy" / "nixos" / "journal.nix"
HOSTNAMES = REPO / "cloudflare" / "hostnames.nix"
CONFIG = REPO / "hosts" / "ellis-server" / "configuration.nix"

old_journal = (
    '    journal    = { expose = "tailnet"; target = "http://192.168.1.54:8000"; '
    "protect = true; };  # Journal Search API on xps-old\n"
)
new_journal = (
    '    journal    = { expose = "tailnet"; target = "http://localhost:8094"; '
    "protect = true; };  # Journal Search UI + /api proxy (modules/journal.nix)\n"
)

import_line = "    ../../modules/journal.nix\n"
blog_import = "    ../../modules/blog.nix\n"


def main() -> None:
    if not REPO.is_dir():
        raise SystemExit(f"Expected nixos-config at {REPO}")

    if MODULE_SRC.is_file():
        MODULE_DST.write_text(MODULE_SRC.read_text())
        print(f"Wrote {MODULE_DST}")
    elif not MODULE_DST.is_file():
        raise SystemExit(f"Missing {MODULE_DST} — copy deploy/nixos/journal.nix first")

    ht = HOSTNAMES.read_text()
    if new_journal.strip() in ht:
        print("hostnames.nix: journal entry already updated")
    elif old_journal in ht:
        HOSTNAMES.write_text(ht.replace(old_journal, new_journal))
        print("hostnames.nix: updated journal target to :8094")
    else:
        raise SystemExit("hostnames.nix: could not find journal line to patch")

    cfg = CONFIG.read_text()
    if import_line.strip() in cfg:
        print("configuration.nix: journal.nix already imported")
    elif blog_import in cfg:
        CONFIG.write_text(cfg.replace(blog_import, blog_import + import_line))
        print("configuration.nix: imported journal.nix")
    else:
        raise SystemExit("configuration.nix: could not find blog.nix import anchor")


if __name__ == "__main__":
    main()
