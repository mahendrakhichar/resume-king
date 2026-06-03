# Deployment Guide — ResumeForge AI

## Architecture Overview

```
                    ┌─────────────┐
                    │   Client    │
                    │  (Browser)  │
                    └──────┬──────┘
                           │ HTTPS
                    ┌──────▼──────┐
                    │   Vercel    │ ← Frontend (React + Vite)
                    │   / Netlify │
                    └──────┬──────┘
                           │ API calls
                    ┌──────▼──────┐
                    │   Railway   │ ← Backend (FastAPI + Uvicorn)
                    │   / Render  │
                    └──┬────┬─────┘
                       │    │
            ┌──────────┘    └──────────┐
     ┌──────▼──────┐          ┌───────▼───────┐
     │   Neon DB   │          │  OpenRouter   │
     │ (PostgreSQL)│          │  (LLM Gateway)│
     └─────────────┘          └───────────────┘
```

---

## Environment Variables

### Backend (.env)

```bash
# ─── Database (Required) ─────────────────────────────────────
# Get from: https://console.neon.tech → Your Project → Connection Details
# IMPORTANT: Must use postgresql+asyncpg:// prefix for the async driver
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require

# ─── OpenRouter AI (Required) ────────────────────────────────
# Get from: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ─── Model Routing ──────────────────────────────────────────
# Customize which models handle which tasks
# Browse models: https://openrouter.ai/models
MAIN_MODEL=qwen/qwen3-coder              # Heavy reasoning (resume rewriting, ATS scoring)
FAST_MODEL=google/gemma-4-26b-a4b-it     # Structured output (JD analysis, parsing)
FALLBACK_MODEL=minimax/minimax-m2.5      # Cheap fallback when others fail

# ─── Legacy AI Providers (Optional — additional fallbacks) ───
# These are tried if OpenRouter fails entirely
GOOGLE_API_KEY=                           # https://aistudio.google.com/app/apikey
GROQ_API_KEY=                             # https://console.groq.com/keys
OPENAI_API_KEY=                           # https://platform.openai.com/api-keys

# ─── Authentication ──────────────────────────────────────────
# Get from: https://dashboard.clerk.com → Your App → API Keys
# Leave as placeholders for mock mode (local development)
CLERK_SECRET_KEY=your_clerk_secret_key
CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

# ─── Application ─────────────────────────────────────────────
APP_ENV=development                       # development | production
APP_DEBUG=true                            # Set false in production
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=10
CHROMA_PERSIST_DIR=./chroma_db
```

### Frontend (.env)

```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx  # From Clerk dashboard
VITE_API_BASE_URL=http://localhost:8000   # Backend URL (only for production)
```

---

## Neon Database Setup

1. **Create account**: Go to [neon.tech](https://neon.tech) and sign up
2. **Create project**: Click "New Project" → choose region closest to your deployment
3. **Get connection string**: Dashboard → Connection Details → select "Connection string"
4. **Format for asyncpg**: Replace `postgresql://` with `postgresql+asyncpg://`
5. **Tables auto-create**: In development mode, tables are created automatically on startup via `init_db()`

> **Note**: The Neon pooler endpoint (contains `-pooler` in hostname) is recommended for serverless deployments. For persistent servers, use the direct endpoint.

---

## OpenRouter Setup

1. **Create account**: Go to [openrouter.ai](https://openrouter.ai) and sign up
2. **Add credits**: Settings → Billing → add credits ($5 is plenty for development)
3. **Generate API key**: Settings → Keys → Create Key
4. **Choose models**: Browse [openrouter.ai/models](https://openrouter.ai/models) to customize MAIN/FAST/FALLBACK tiers

### Model Selection Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Model Routing                         │
│                                                          │
│  MAIN_MODEL ─── Heavy tasks (rewriting, scoring, prep)  │
│  FAST_MODEL ─── Quick tasks (parsing, analysis, QA)     │
│  FALLBACK   ─── Used when primary/fast models fail      │
│                                                          │
│  Fallback Chain:                                         │
│  Assigned → Fast → Fallback → Main → Gemini → Groq     │
└─────────────────────────────────────────────────────────┘
```

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Production Deployment Options

### Backend → Railway / Render

1. Push code to GitHub
2. Connect repo to Railway/Render
3. Set environment variables from the list above
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Set `APP_ENV=production` and `APP_DEBUG=false`

### Frontend → Vercel / Netlify

1. Connect GitHub repo
2. Set build command: `npm run build`
3. Set output directory: `dist`
4. Set environment variables (`VITE_CLERK_PUBLISHABLE_KEY`, `VITE_API_BASE_URL`)

---

## Health Check

After deployment, verify:

```bash
curl https://your-backend-url.com/health
# Expected: {"status":"healthy","app":"ResumeForge AI","version":"0.1.0","environment":"production"}
```
