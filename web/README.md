# Journal Search — web app

React UI for the journal-search API. Styling matches `mockups/`.

## Local dev

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

Ensure API `ALLOWED_ORIGINS` includes `http://localhost:5173` when the browser talks to the API cross-origin.
