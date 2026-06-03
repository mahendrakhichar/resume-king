import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SignedIn, SignedOut, RedirectToSignIn, useAuth } from "./lib/auth";

import LandingPage from "./pages/LandingPage";
import DashboardPage from "./pages/DashboardPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionPage from "./pages/SessionPage";
import HistoryPage from "./pages/HistoryPage";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import api from "./lib/api";

// Standard Auth Guard wrapper enforcing Clerk signed-in state
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

// Request interceptor to dynamically inject the Clerk JWT token into axios headers
function AuthInterceptor({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

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
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.request.eject(requestInterceptor);
    };
  }, [getToken]);

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthInterceptor>
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
