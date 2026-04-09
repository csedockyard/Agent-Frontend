## Vercel Deployment (Prototype Stage 1)

This repo is configured for a single Vercel project:
- Frontend: React/Vite static app (`frontend/dist`)
- Backend: FastAPI serverless function (`api/index.py`)

### 1) Install Vercel CLI

```bash
npm i -g vercel
```

### 2) Deploy from project root

```bash
vercel
```

For production:

```bash
vercel --prod
```

### 3) Add Environment Variables in Vercel Dashboard

Project -> Settings -> Environment Variables:

- `PLACEMENTPRO_ENABLE_EXTERNAL_AI`
- `PLACEMENTPRO_PRIMARY_LLM`
- `PLACEMENTPRO_MAX_LLM_DECISIONS_PER_CYCLE`
- `PLACEMENTPRO_GROQ_API_KEY`
- `PLACEMENTPRO_GROQ_MODEL`
- `PLACEMENTPRO_GEMINI_API_KEY`
- `PLACEMENTPRO_GEMINI_MODEL`
- `PLACEMENTPRO_TAVILY_API_KEY`
- `PLACEMENTPRO_JINA_API_KEY`
- `PLACEMENTPRO_EMAIL_FROM`
- `PLACEMENTPRO_RESEND_API_KEY`
- `PLACEMENTPRO_SENDGRID_API_KEY`
- `PLACEMENTPRO_FRONTEND_BASE_URL` (set this to your Vercel URL after first deploy)

Optional frontend var:
- `VITE_API_BASE_URL` (leave empty for same-domain API routing)

### 4) Important Runtime Note

On Vercel, SQLite is stored in `/tmp/placementpro.db` for serverless write access.
This is perfect for prototype/demo flow but not durable storage.

For production persistence, move to managed DB (Postgres/Supabase/Neon).

### 5) Smoke Test URLs

- `/` -> dashboard loads
- `/api/dashboard/live-insights`
- `/api/admin/analytics`
- `/api/students/1/journey`
- `/api/simulations/what-if` (POST)
- `/api/agents/run-cycle` (POST)

