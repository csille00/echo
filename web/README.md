# Journal Search — web app

React UI for the journal-search API. Styling matches `mockups/`.

## Auth (Authentik SSO)

Production uses **Authentik forward-auth** at Caddy: the browser session cookie authenticates requests to the API. Set `VITE_AUTH_MODE=authentik` (default) and serve the built app on the same Authentik-protected hostname as the API (or a sibling host with the same SSO app).

API: `AUTH_BACKEND=authentik` — resolves the user from `X-Authentik-Uid` (set by the outpost) or from a Bearer JWT when `OIDC_JWKS_URL` is configured.

## Local dev (no SSO)

```bash
# API
AUTH_BACKEND=dev_header

# web/.env
VITE_AUTH_MODE=dev
VITE_DEV_USER_ID=<your-test-user-uuid>
```

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173 — API calls use the Vite proxy (`/api` → `localhost:8000`) unless `VITE_API_URL` is set.

Ensure API `ALLOWED_ORIGINS` includes `http://localhost:5173` when using cookies or CORS from the dev server.
