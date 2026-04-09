## Deploy On Render (Recommended For Your Prototype)

This setup deploys **frontend + backend on one shareable URL**.

### 1) Push this project to GitHub

If your repo is not on GitHub yet:

```bash
git init
git add .
git commit -m "Prototype ready for Render deploy"
```

Create a GitHub repo, then:

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```

### 2) Create Render Web Service

1. Open Render Dashboard -> **New +** -> **Web Service**
2. Connect your GitHub repo
3. Render auto-detects `render.yaml` and `Dockerfile`
4. Click **Create Web Service**

### 3) Set Secret Environment Variables in Render

In Render service -> **Environment** add:

- `PLACEMENTPRO_GROQ_API_KEY`
- `PLACEMENTPRO_GEMINI_API_KEY`
- `PLACEMENTPRO_TAVILY_API_KEY`
- `PLACEMENTPRO_JINA_API_KEY`
- `PLACEMENTPRO_EMAIL_FROM`
- `PLACEMENTPRO_RESEND_API_KEY`
- `PLACEMENTPRO_SENDGRID_API_KEY`

Then set:

- `PLACEMENTPRO_FRONTEND_BASE_URL=https://<your-render-service>.onrender.com`

and redeploy once.

### 4) Shareable URL

Your app is globally accessible at:

`https://<your-render-service>.onrender.com`

You can share this directly with judges/mentors.

### 5) Verify Production Endpoints

- `https://<your-render-service>.onrender.com/`
- `https://<your-render-service>.onrender.com/health`
- `https://<your-render-service>.onrender.com/api/dashboard/live-insights`
- `https://<your-render-service>.onrender.com/api/admin/analytics`
- `https://<your-render-service>.onrender.com/api/students/1/journey`

### Notes

- This setup uses persistent SQLite via Render Disk (`/var/data/placementpro.db`).
- If external keys are missing, the app still runs with fallback/simulated behavior.

