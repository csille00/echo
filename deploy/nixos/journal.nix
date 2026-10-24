{ ... }:

# journal.ellisfam.space — Journal Search web UI (Vite SPA) with /api proxied to xps-old.
# Copy to nixos-config/modules/journal.nix and import from hosts/ellis-server/configuration.nix.
# hostnames.nix: journal target = http://localhost:8094 (keep protect = true for Authentik).

let
  siteRoot = "/var/www/journal";
  port = 8094;
  apiUpstream = "http://100.70.187.21:8000";
in
{
  services.caddy.virtualHosts.":${toString port}" = {
    extraConfig = ''
      handle /api/* {
        reverse_proxy ${apiUpstream}
      }
      handle {
        root * ${siteRoot}
        try_files {path} /index.html
        file_server
      }

      header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
      }
    '';
  };

  systemd.tmpfiles.rules = [
    "d ${siteRoot} 0755 ellisserver users -"
  ];
}
