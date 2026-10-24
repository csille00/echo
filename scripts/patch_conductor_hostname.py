#!/usr/bin/env python3
"""Add conductor.ellisfam.space to nixos-config on ellis-server."""

from pathlib import Path

hostnames = Path.home() / "nixos-config/cloudflare/hostnames.nix"
text = hostnames.read_text()
entry = (
    '    conductor      = { expose = "tailnet"; target = "http://100.70.187.21:18080"; '
    'protect = true; }; # DBOS Console on xps-old (SSO)\n'
)
needle = (
    '    journal-search = { expose = "tailnet"; target = "http://192.168.1.54:54323"; '
    'protect = true; }; # Supabase Studio: journal-search instance on xps-old (SSO)\n'
)
if "conductor      = { expose" not in text:
    if needle not in text:
        raise SystemExit("hostnames anchor missing")
    hostnames.write_text(text.replace(needle, needle + entry))
    print("hostnames.nix: added conductor")
else:
    print("hostnames.nix: already has conductor")

apps = Path.home() / "nixos-config/authentik/blueprints/applications.yaml"
atext = apps.read_text()
if "provider-conductor" not in atext:
    block = """

  # --- DBOS Conductor Console (forward auth) -------------------------------
  - model: authentik_providers_proxy.proxyprovider
    id: provider-conductor
    identifiers:
      name: conductor
    attrs:
      mode: forward_single
      external_host: https://conductor.ellisfam.space
      authorization_flow:
        !Find [
          authentik_flows.flow,
          [slug, default-provider-authorization-implicit-consent],
        ]
      invalidation_flow:
        !Find [authentik_flows.flow, [slug, default-provider-invalidation-flow]]

  - model: authentik_core.application
    id: app-conductor
    identifiers:
      slug: conductor
    attrs:
      name: DBOS Conductor
      group: Infrastructure
      provider: !KeyOf provider-conductor
"""
    marker = "  # --- Blog Supabase Studio (forward auth) --------------------------------"
    if marker not in atext:
        raise SystemExit("applications anchor missing")
    apps.write_text(atext.replace(marker, block + "\n" + marker))
    print("applications.yaml: added conductor")
else:
    print("applications.yaml: already has conductor")
