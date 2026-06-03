# Frontend Architecture — ResumeForge AI

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Framework | React 18 + TypeScript | Component-based UI with type safety |
| Build Tool | Vite | Fast HMR dev server, optimized production builds |
| State Management | Zustand | Lightweight, hook-based global state |
| HTTP Client | Axios | API communication with interceptors |
| Auth | Clerk React SDK | Authentication with transparent mock mode |
| Routing | React Router v6 | Client-side navigation |
| Icons | Lucide React | Consistent icon system |
| Styling | Tailwind CSS | Utility-first CSS framework |

---

## Key Architectural Decisions

### 1. Progressive Upload UX with Simulated Progress

**Problem**: Resume upload involves a single POST request that triggers a multi-step server pipeline (file save → text extraction → LLM parsing → DB save → vector indexing). Users saw a generic spinner with no indication of progress or time remaining.

**Solution**: Implemented a hybrid progress tracking system in `useResumeStore.ts`:
- **0–30%**: Real upload progress via Axios `onUploadProgress` callback (actual bytes transferred)
- **30–95%**: Simulated server-side processing stages with randomized increments (2-8% per 800ms tick)
- **95–100%**: Set when the server responds successfully

Stage labels provide context: "Uploading file...", "Extracting text from document...", "AI parsing resume structure...", "Indexing for semantic matching..."

**Trade-off**: True real-time progress would require WebSockets or SSE, adding significant complexity. The simulated approach provides perceived performance improvement with minimal overhead.

### 2. Error Categorization System

**Problem**: All errors displayed the same generic message ("Failed to process resume"), giving users no actionable information.

**Solution**: Errors are categorized at the store level with a `categorizeError()` function that inspects:
- HTTP status codes (429 → rate_limit, 401/403 → auth, 408 → timeout)
- Response body keywords ("timeout", "rate")
- Axios error codes (ERR_NETWORK, ECONNABORTED)

Each category triggers specific UI treatment:

| Category | Icon | Color | User Message | Retry? |
|---|---|---|---|---|
| `rate_limit` | ⚡ | Amber | "AI model rate limit reached" | ✅ |
| `timeout` | ⏱️ | Orange | "Server processing timed out" | ✅ |
| `network` | 🌐 | Blue | "Network connection issue" | ✅ |
| `auth` | 🔒 | Purple | "Authentication error" | ❌ |
| `parsing_error` | ❗ | Red | "Document could not be processed" | ❌ |

### 3. Transparent Mock Authentication

**Problem**: Clerk authentication required API keys and account setup for local development.

**Solution**: The `lib/auth.tsx` module detects when Clerk credentials are placeholder values and automatically switches to mock mode. The mock provides a synthetic user object with the same interface, allowing all components to work identically in dev and production without conditional logic.

### 4. Zustand State Architecture

State is split into focused stores for clean separation of concerns:
- **`useResumeStore`**: Resume CRUD, upload progress tracking, error state
- **`useSessionStore`**: Tailoring session lifecycle, agent results, review submissions

Both stores share the same error categorization pattern for consistent UX.

### 5. API Layer Design

The Axios client (`lib/api.ts`) is configured with:
- Base URL of `/api` (proxied to `localhost:8000` via Vite config)
- JWT auth token injection via `setAuthToken()`
- 5-minute timeout for upload requests (matching backend agent timeout)

---

## File Structure

```
frontend/src/
├── components/
│   ├── resume/
│   │   ├── ResumeUploader.tsx   # Drag-drop + progress bar upload
│   │   └── ResumeDiffViewer.tsx  # Before/after comparison view
│   ├── shared/
│   │   ├── GlassCard.tsx        # Reusable glassmorphism card
│   │   └── ErrorToast.tsx       # Category-aware error notifications
│   ├── layout/                  # Navbar, sidebar, page shells
│   ├── agents/                  # Agent result display cards
│   ├── job/                     # Job description input components
│   └── review/                  # Human-in-the-loop review UI
├── pages/
│   ├── LandingPage.tsx          # Marketing/hero page
│   ├── DashboardPage.tsx        # Resume management hub
│   ├── NewSessionPage.tsx       # Create tailoring session wizard
│   ├── SessionPage.tsx          # Live session progress & results
│   └── HistoryPage.tsx          # Past session browser
├── stores/
│   ├── useResumeStore.ts        # Resume state + upload progress
│   └── useSessionStore.ts       # Session state + error handling
├── lib/
│   ├── api.ts                   # Axios HTTP client
│   ├── auth.tsx                 # Clerk/Mock auth provider
│   └── utils.ts                 # Shared utilities
├── types/                       # TypeScript interfaces
├── App.tsx                      # Router + layout composition
├── main.tsx                     # React DOM entry point
└── index.css                    # Global design tokens
```
