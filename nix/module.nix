# NixOS module for Journal Search.
#
# The service listens on 127.0.0.1:8000. Publish it with whatever reverse
# proxy the host already uses.
#
#   services.journal-search.enable = true;
{ self }:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.journal-search;
  settingsEnv = lib.mapAttrs (_: envValue) cfg.settings;
  envValue =
    value:
    if lib.isBool value then
      lib.boolToString value
    else
      toString value;

  # TCP to localhost: PostgresDsn rejects an empty host, which is what a Unix-socket URL needs.
  # The matching pg_hba rule trusts this user from localhost only.
  localDatabaseUrl = "postgresql+asyncpg://${cfg.user}@127.0.0.1:5432/${cfg.database.name}";

  environment =
    {
      API_HOST = cfg.host;
      LISTEN_PORT = toString cfg.port;
      LOCAL_STORAGE_PATH = "${cfg.dataDir}/uploads";
      STORAGE_BACKEND = "local";
      AUTH_BACKEND = "local";
      REALTIME_BACKEND = "none";
      OCR_PROVIDER = "tesseract";
      EMBEDDING_PROVIDER = "ollama";
      EMBEDDING_MODEL = "nomic-embed-text";
      EMBEDDING_DIMENSION = "768";
      OLLAMA_BASE_URL = cfg.ollama.url;
      LLM_PROVIDER = "ollama";
      LLM_CLEANUP_ENABLED = "false";
      DEBUG = "false";
    }
    // lib.optionalAttrs cfg.database.createLocally { DATABASE_URL = localDatabaseUrl; }
    // settingsEnv;
in
{
  options.services.journal-search = {
    enable = lib.mkEnableOption "Journal Search";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      defaultText = lib.literalExpression "inputs.journal-search.packages.\${system}.default";
      description = "Journal Search package. Includes the API and the built web UI.";
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "journal_search";
      description = ''
        System user. The local PostgreSQL role uses the same name.
        Use only letters, digits, and underscores.
      '';
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "journal_search";
      description = "System group for the service and its data directory.";
    };

    host = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      example = "0.0.0.0";
      description = ''
        Address the API binds to. Leave this on localhost and point a reverse proxy at
        {option}`services.journal-search.port`.
      '';
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8000;
      description = "Port the API binds to.";
    };

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/journal-search";
      description = "State directory. Uploaded pages are stored in `uploads` inside this directory.";
    };

    environmentFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "/run/secrets/journal-search.env";
      description = ''
        Absolute path to an environment file. Use it for secrets such as `OIDC_CLIENT_SECRET`.
        The file is not copied into the Nix store. Values here override {option}`settings`.
      '';
    };

    settings = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.oneOf [
          lib.types.str
          lib.types.int
          lib.types.bool
        ]
      );
      default = { };
      example = lib.literalExpression ''
        {
          AUTH_BACKEND = "authentik";
          AUTHENTIK_UID_HEADER = "X-Authentik-Uid";
          OIDC_ISSUER = "https://auth.example.com/application/o/journal/";
          OIDC_CLIENT_ID = "journal";
          OIDC_DISPLAY_NAME = "Ellis SSO";
        }
      '';
      description = ''
        Extra environment variables for the service. These override the module defaults.
        Do not put secrets here; they are written to the Nix store. Use {option}`environmentFile`.
      '';
    };

    database.createLocally = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Create a PostgreSQL database with pgvector on this machine and point the service at it.
        Set this to false and provide `DATABASE_URL` to use a database elsewhere.
      '';
    };

    database.name = lib.mkOption {
      type = lib.types.str;
      default = "journal_search";
      description = "Database name. The service user owns it when it is created locally.";
    };

    ollama.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Enable the Ollama service and download {option}`services.journal-search.ollama.model`.
        Turn this off when embeddings come from another machine or another provider.
      '';
    };

    ollama.model = lib.mkOption {
      type = lib.types.str;
      default = "nomic-embed-text";
      description = "Ollama embedding model to pull. Must match `EMBEDDING_MODEL` and a 768-dimension index.";
    };

    ollama.url = lib.mkOption {
      type = lib.types.str;
      default = "http://127.0.0.1:11434";
      description = "Ollama base URL used for embeddings.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = builtins.match "[A-Za-z_][A-Za-z0-9_]*" cfg.user != null;
        message = "services.journal-search.user must contain only letters, digits, and underscores.";
      }
      {
        assertion = builtins.match "[A-Za-z_][A-Za-z0-9_]*" cfg.database.name != null;
        message = "services.journal-search.database.name must contain only letters, digits, and underscores.";
      }
      {
        assertion =
          cfg.database.createLocally
          || cfg.settings ? DATABASE_URL
          || cfg.environmentFile != null;
        message = ''
          journal-search needs a database. Leave database.createLocally enabled, set settings.DATABASE_URL,
          or provide DATABASE_URL in environmentFile.
        '';
      }
    ];

    users.users = lib.mkIf (cfg.user == "journal_search") {
      ${cfg.user} = {
        isSystemUser = true;
        group = cfg.group;
        home = cfg.dataDir;
      };
    };
    users.groups = lib.mkIf (cfg.group == "journal_search") {
      ${cfg.group} = { };
    };

    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} - -"
      "d ${cfg.dataDir}/uploads 0750 ${cfg.user} ${cfg.group} - -"
    ];

    services.postgresql = lib.mkIf cfg.database.createLocally {
      enable = true;
      extensions = lib.mkDefault (ps: [ ps.pgvector ]);
      ensureDatabases = [ cfg.database.name ];
      ensureUsers = [
        {
          name = cfg.user;
          ensureDBOwnership = cfg.database.name == cfg.user;
        }
      ];
      authentication = ''
        host ${cfg.database.name} ${cfg.user} 127.0.0.1/32 trust
        host ${cfg.database.name} ${cfg.user} ::1/128 trust
      '';
    };

    systemd.services.journal-search-init-db = lib.mkIf cfg.database.createLocally {
      description = "Create the pgvector extension for Journal Search";
      after = [ "postgresql-setup.service" ];
      requires = [ "postgresql-setup.service" ];
      serviceConfig = {
        Type = "oneshot";
        User = "postgres";
        RemainAfterExit = true;
      };
      path = [ config.services.postgresql.package ];
      script = ''
        psql -v ON_ERROR_STOP=1 -d ${cfg.database.name} -c 'CREATE EXTENSION IF NOT EXISTS vector'
        psql -v ON_ERROR_STOP=1 -d postgres -c 'ALTER DATABASE ${cfg.database.name} OWNER TO ${cfg.user}'
      '';
    };

    services.ollama = lib.mkIf cfg.ollama.enable {
      enable = true;
      loadModels = [ cfg.ollama.model ];
    };

    systemd.services.journal-search = {
      description = "Journal Search";
      wantedBy = [ "multi-user.target" ];
      after = [
        "network-online.target"
      ]
      ++ lib.optional cfg.database.createLocally "journal-search-init-db.service"
      ++ lib.optional cfg.ollama.enable "ollama.service";
      wants = [ "network-online.target" ];
      requires = lib.optional cfg.database.createLocally "journal-search-init-db.service";
      environment = environment;
      serviceConfig = {
        ExecStart = lib.getExe cfg.package;
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        EnvironmentFile = lib.optional (cfg.environmentFile != null) cfg.environmentFile;
        Restart = "on-failure";
        RestartSec = 2;
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ReadWritePaths = [
          cfg.dataDir
          "/run/postgresql"
        ];
      };
    };
  };
}
