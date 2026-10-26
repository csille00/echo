# Journal Search — web app

React UI for the journal-search API.

The UI loads `GET /api/v1/auth/config` and follows the API. With `AUTH_BACKEND=local` (the default), the first visitor creates an admin account and later visits use email and password. The session is an HTTP-only cookie.

## Local dev

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. API calls use the Vite proxy (`/api` → `localhost:8000`) unless `VITE_API_URL` is set.

`VITE_AUTH_MODE` is only a fallback for when the API has no `/auth/config` endpoint. `VITE_AUTH_MODE=dev` plus `VITE_DEV_USER_ID` matches `AUTH_BACKEND=dev_header` on the API.

Ensure API `ALLOWED_ORIGINS` includes `http://localhost:5173` when the browser talks to the API cross-origin.
