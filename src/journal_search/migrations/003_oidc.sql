-- Link a local account to an OpenID Connect identity (any issuer).

ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_issuer TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_subject TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_oidc_identity
    ON users (oidc_issuer, oidc_subject)
    WHERE oidc_subject IS NOT NULL;
