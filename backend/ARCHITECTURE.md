# Backend Architecture — ResumeForge AI

## System Overview

ResumeForge AI is a multi-agent resume optimization platform that uses LangGraph to orchestrate a pipeline of specialized AI agents for resume tailoring, ATS scoring, and interview preparation.

```
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                             │
│                                                                │
│  ┌─────────┐   ┌───────────────┐   ┌────────────────────┐    │
│  │ API      │──▶│ Auth Service  │   │ LLM Service        │    │
│  │ Routes   │   │ (Clerk/Mock)  │   │ (OpenRouter +      │    │
│  │          │   └───────────────┘   │  Task-Based Routing)│    │
│  │ /resumes │                       └────────────────────┘    │
│  │ /sessions│                              ▲                   │
│  │ /export  │                              │                   │
│  └────┬─────┘                              │                   │
│       │           ┌────────────────────────┘                   │
│       ▼           ▼                                            │
│  ┌─────────────────────────────────────────┐                  │
│  │        LangGraph Workflow Engine         │                  │
│  │                                          │                  │
│  │  JD Analyzer ──▶ ATS Matcher ──┐         │                  │
│  │                                 │         │                  │
│  │     ┌───────────────────────────┤         │                  │
│  │     ▼           ▼           ▼   │         │                  │
│  │  Rewriter   Recruiter   Interview│         │                  │
│  │     │           │           │   │         │                  │
│  │     └───────────┴───────────┘   │         │                  │
│  │                 ▼               │         │                  │
│  │              Validator          │         │                  │
│  └─────────────────────────────────┘         │                  │
│                                               │                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │                  │
│  │PostgreSQL│  │ ChromaDB │  │ File     │   │                  │
│  │ (Neon)   │  │ (Vectors)│  │ Storage  │   │                  │
│  └──────────┘  └──────────┘  └──────────┘   │                  │
└──────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

### 1. OpenRouter as Unified LLM Gateway

**Problem**: Managing separate API keys and rate limits across Google Gemini, Groq, and OpenAI was fragile and led to inconsistent error handling.

**Solution**: Integrated [OpenRouter](https://openrouter.ai) as the primary unified provider. All LLM calls now route through a single API gateway, while still maintaining direct provider keys as fallbacks.

**Implementation** (`services/llm_service.py`):
- Task-based model routing via `get_model_for_task(task_type)` maps each agent's workload to the optimal model tier
- 3-tier model hierarchy: `MAIN_MODEL` (heavy reasoning) → `FAST_MODEL` (structured output) → `FALLBACK_MODEL` (cheap/fast)
- Automatic fallback chain: assigned model → fast → fallback → main → legacy providers (Gemini/Groq)

| Agent Task | Model Tier | Model | Rationale |
|---|---|---|---|
| Resume Rewriting | MAIN | qwen/qwen3-coder | Quality writing requires deep reasoning |
| ATS Matching | MAIN | qwen/qwen3-coder | Scoring accuracy matters |
| Interview Prep | MAIN | qwen/qwen3-coder | Deep knowledge generation |
| JD Analysis | FAST | google/gemma-4-26b-a4b-it | Structured extraction |
| Resume Parsing | FAST | google/gemma-4-26b-a4b-it | Speed + structured output |
| Project Optimization | FAST | google/gemma-4-26b-a4b-it | Template-based output |
| Recruiter Outreach | FAST | google/gemma-4-26b-a4b-it | Template generation |
| Validation QA | FAST | google/gemma-4-26b-a4b-it | Quick QA check |
| Quick Summary | FALLBACK | minimax/minimax-m2.5 | Speed + cost |

### 2. Timeout Enforcement & Error Categorization

**Problem**: LLM calls could hang indefinitely, blocking the workflow and leaving users with no feedback.

**Solution**: Dual-layer timeout enforcement:
- **Per-LLM-call timeout** (120s): `asyncio.wait_for()` wrapping every `llm.ainvoke()` call in `llm_service.py`
- **Per-agent timeout** (300s / 5 min): `asyncio.wait_for()` wrapping `self._run(state)` in `agents/base.py`

**Error Categorization**: All errors are classified into categories (`rate_limit`, `timeout`, `network`, `auth`, `unknown`) enabling the frontend to show context-specific error messages and retry buttons.

### 3. Neon PostgreSQL + asyncpg Connection Handling

**Problem**: Neon's PostgreSQL proxy returns `channel_binding=require` in connection parameters, which crashes older `asyncpg` drivers with `TypeError: connect() got an unexpected keyword argument 'channel_binding'`.

**Solution**: Implemented a startup monkeypatch in `db/database.py` that intercepts `asyncpg.connect()` calls and strips the `channel_binding` parameter while properly mapping `sslmode` to the `ssl` boolean that asyncpg expects.

```python
# Monkeypatch: strip channel_binding and map sslmode → ssl
_original_connect = asyncpg_connect.__wrapped__ if hasattr(asyncpg_connect, '__wrapped__') else asyncpg_connect
async def _patched_connect(*args, **kwargs):
    kwargs.pop("channel_binding", None)
    if "sslmode" in kwargs:
        kwargs["ssl"] = kwargs.pop("sslmode") in ("require", "verify-ca", "verify-full")
    return await _original_connect(*args, **kwargs)
```

### 4. Transparent Mock Authentication

**Problem**: Local development required Clerk account setup, creating friction for new developers and CI environments.

**Solution**: When `CLERK_SECRET_KEY` is set to the placeholder value `your_clerk_secret_key`, the auth service automatically switches to mock mode, returning a synthetic user (`user_mock_123456`) for all requests. This is transparent — no code changes needed between dev and production.

### 5. Eliminating Redundant Resume Parsing

**Problem**: Resume text was being parsed by the LLM twice — once during upload (`parsers/resume_extractor.py`), and potentially again by agents that re-read `raw_resume_text` from state.

**Solution**: The structured `parsed_resume` dict from the initial upload is passed directly into the workflow's initial state (`sessions.py` line 215). All agents now consume `state["parsed_resume"]` exclusively, avoiding redundant LLM calls. This saves ~10-15 seconds and one LLM API call per session.

### 6. Multi-Agent Workflow with Conditional Routing

The LangGraph workflow uses conditional edges for intelligent routing:
- If initial ATS score ≥ 90%, skip rewriting entirely → jump to validation
- Otherwise, fork into parallel execution: Rewriter, Recruiter, and Interview agents run concurrently
- All parallel branches merge at the Validator node

### 7. Vector Indexing Strategy (ChromaDB)

Parsed resume sections are indexed in ChromaDB for semantic similarity matching during the ATS scoring phase. This allows keyword matching beyond exact string comparison — detecting semantic equivalents like "CI/CD" matching "continuous integration".

---

## File Structure

```
backend/
├── agents/           # AI agent implementations
│   ├── base.py       # Base class with timeout, logging, error handling
│   ├── jd_analyzer.py
│   ├── ats_matcher.py
│   ├── resume_rewriter.py
│   ├── project_optimizer.py
│   ├── recruiter_agent.py
│   ├── interview_agent.py
│   └── validator.py
├── api/              # FastAPI route handlers
│   └── routes/
├── config/           # Settings & environment config
├── db/               # Database connection & migrations
├── models/           # SQLAlchemy ORM models
├── parsers/          # PDF/DOCX text extraction + LLM parsing
├── schemas/          # Pydantic request/response schemas
├── services/         # LLM service, auth service, vector service
├── workflows/        # LangGraph state, nodes, graph compilation
├── utils/            # Logger, file handlers
└── templates/        # PDF generation templates
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Neon PostgreSQL connection string (postgresql+asyncpg://) |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter unified API key |
| `OPENROUTER_BASE_URL` | ❌ | OpenRouter endpoint (default: https://openrouter.ai/api/v1) |
| `MAIN_MODEL` | ❌ | Heavy reasoning model (default: qwen/qwen3-coder) |
| `FAST_MODEL` | ❌ | Fast structured output model (default: google/gemma-4-26b-a4b-it) |
| `FALLBACK_MODEL` | ❌ | Cheap fallback model (default: minimax/minimax-m2.5) |
| `GOOGLE_API_KEY` | ❌ | Direct Gemini fallback |
| `GROQ_API_KEY` | ❌ | Direct Groq fallback |
| `CLERK_SECRET_KEY` | ❌ | Clerk auth (placeholder = mock mode) |
