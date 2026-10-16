import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SignedIn, SignedOut, RedirectToSignIn, useAuth } from "./lib/auth";

import LandingPage from "./pages/LandingPage";
import DashboardPage from "./pages/DashboardPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionPage from "./pages/SessionPage";
import HistoryPage from "./pages/HistoryPage";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import api from "./lib/api";

// ─── Server Wake-Up Banner ─────────────────────────────────────────────────
// Shown when the first cold-start request takes > 8 seconds (Render free tier)
export let showWakeUpBanner: (() => void) | null = null;
export let hideWakeUpBanner: (() => void) | null = null;

function WakeUpBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    showWakeUpBanner = () => setVisible(true);
    hideWakeUpBanner = () => setVisible(false);
    return () => {
      showWakeUpBanner = null;
      hideWakeUpBanner = null;
    };
  }, []);

  if (!visible) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "24px",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "12px 20px",
        borderRadius: "14px",
        background: "rgba(17,24,39,0.95)",
        border: "1px solid rgba(139,92,246,0.35)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(139,92,246,0.1)",
        backdropFilter: "blur(12px)",
        maxWidth: "480px",
        width: "calc(100vw - 48px)",
        animation: "slideUpBanner 0.4s cubic-bezier(0.34,1.56,0.64,1)",
      }}
    >
      {/* Spinner */}
      <div style={{
        width: "20px",
        height: "20px",
        borderRadius: "50%",
        border: "2px solid rgba(139,92,246,0.3)",
        borderTopColor: "#a855f7",
        animation: "spin 0.9s linear infinite",
        flexShrink: 0,
      }} />
      <div style={{ flex: 1 }}>
        <p style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "#e2e8f0", lineHeight: 1.3 }}>
          Waking up server…
        </p>
        <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8", lineHeight: 1.4, marginTop: "2px" }}>
          Free tier backend is starting up — this can take up to 60 seconds on first use. Please wait ☕
        </p>
      </div>
      <style>{`
        @keyframes slideUpBanner {
          from { opacity: 0; transform: translateX(-50%) translateY(16px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

// ─── Auth Guard ────────────────────────────────────────────────────────────
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}

// ─── Auth + 401-Retry Interceptor ─────────────────────────────────────────
// Injects fresh Clerk JWT on every request.
// On 401, grabs a brand-new token (skipCache: true) and retries once.
// This handles expired tokens after backend cold-start sleep.
function AuthInterceptor({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();
  // Track in-flight requests so we can show the wake-up banner if one stalls
  const pendingCount = useRef(0);
  const wakeUpTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const requestInterceptor = api.interceptors.request.use(
      async (config) => {
        try {
          const token = await getToken();
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } catch (error) {
          console.error("Error fetching auth token", error);
        }

        // Start a wake-up banner timer if requests are taking > 8s
        pendingCount.current += 1;
        if (pendingCount.current === 1 && !wakeUpTimer.current) {
          wakeUpTimer.current = setTimeout(() => {
            showWakeUpBanner?.();
          }, 8000);
        }

        return config;
      },
      (error) => Promise.reject(error)
    );

    const responseInterceptor = api.interceptors.response.use(
      (response) => {
        // Request resolved — clear banner if no more pending
        pendingCount.current = Math.max(0, pendingCount.current - 1);
        if (pendingCount.current === 0) {
          if (wakeUpTimer.current) {
            clearTimeout(wakeUpTimer.current);
            wakeUpTimer.current = null;
          }
          hideWakeUpBanner?.();
        }
        return response;
      },
      async (error) => {
        pendingCount.current = Math.max(0, pendingCount.current - 1);
        if (pendingCount.current === 0) {
          if (wakeUpTimer.current) {
            clearTimeout(wakeUpTimer.current);
            wakeUpTimer.current = null;
          }
          hideWakeUpBanner?.();
        }

        // ── 401 retry with fresh token ────────────────────────────────
        // Only retry once (guard via _retried flag on config)
        const originalRequest = error.config as typeof error.config & { _retried?: boolean };
        if (error.response?.status === 401 && !originalRequest._retried) {
          originalRequest._retried = true;
          try {
            // Force-refresh: skip Clerk's in-memory cache to get a new JWT
            const freshToken = await getToken({ skipCache: true } as Parameters<typeof getToken>[0]);
            if (freshToken) {
              originalRequest.headers.Authorization = `Bearer ${freshToken}`;
              return api(originalRequest);
            }
          } catch (refreshError) {
            console.error("Token refresh failed:", refreshError);
          }
        }

        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.request.eject(requestInterceptor);
      api.interceptors.response.eject(responseInterceptor);
      if (wakeUpTimer.current) clearTimeout(wakeUpTimer.current);
    };
  }, [getToken]);

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthInterceptor>
        <WakeUpBanner />
        <Routes>
          {/* Public landing page */}
          <Route path="/" element={<LandingPage />} />

          {/* Authenticated Dashboard Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="new" element={<NewSessionPage />} />
            <Route path="session/:id" element={<SessionPage />} />
            <Route path="history" element={<HistoryPage />} />
          </Route>

          {/* Catch-all redirection back to Landing */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthInterceptor>
    </BrowserRouter>
  );
}
