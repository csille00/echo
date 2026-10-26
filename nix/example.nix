# Drop-in host config. Import the module from the flake, then:
#
#   imports = [ ./example.nix ];
#
# Point your reverse proxy at 127.0.0.1:8000. Put secrets in the environment
# file, not in this file.
{ ... }:
{
  services.echo = {
    enable = true;
    environmentFile = "/var/lib/echo/secrets.env";

    # Overrides. The defaults are local accounts, Tesseract, and Ollama.
    settings = {
      # Behind HTTPS:
      # PUBLIC_URL = "https://journal.example.com";
      # SESSION_COOKIE_SECURE = true;

      # Proxy header auth, implemented in the reverse proxy:
      # AUTH_BACKEND = "authentik";
      # AUTHENTIK_UID_HEADER = "X-Authentik-Uid";

      # Or generic OpenID Connect. The client secret belongs in environmentFile.
      # OIDC_ISSUER = "https://auth.example.com/application/o/journal/";
      # OIDC_CLIENT_ID = "journal";
      # OIDC_DISPLAY_NAME = "SSO";
    };
  };

  # The environment file is not created for you. Example contents:
  #   OIDC_CLIENT_SECRET=...
  #   DATABASE_URL=postgresql+asyncpg://...   # only when database.createLocally is false
}
