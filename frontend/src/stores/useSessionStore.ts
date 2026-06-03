import { create } from "zustand";
import api from "../lib/api";
import type { SessionResponse, SessionListItem, AgentResultResponse, HumanReviewDecision } from "../types/session";
import type { ErrorCategory } from "./useResumeStore";

type ApiError = {
  response?: { status?: number; data?: { detail?: string; category?: string } };
  code?: string;
};

function categorizeSessionError(e: unknown): { message: string; category: ErrorCategory } {
  const err = e as ApiError;

  if (!err.response && (err.code === "ERR_NETWORK" || err.code === "ECONNABORTED")) {
    return { message: "Network connection issue — check your internet and retry.", category: "network" };
  }

  const status = err.response?.status;
  const detail = err.response?.data?.detail || "";

  if (status === 429) return { message: "AI rate limit reached — please try again later.", category: "rate_limit" };
  if (status === 401 || status === 403) return { message: "Authentication error — please sign in again.", category: "auth" };
  if (detail.toLowerCase().includes("timeout")) return { message: "Processing timed out — the AI agent exceeded the 5-minute limit.", category: "timeout" };
  if (detail.toLowerCase().includes("rate")) return { message: "AI model rate limit reached — backup model was tried.", category: "rate_limit" };

  return { message: detail || "Failed to process request.", category: "unknown" };
}


interface SessionState {
  sessions: SessionListItem[];
  activeSession: SessionResponse | null;
  agentResults: AgentResultResponse[];
  isLoading: boolean;
  error: string | null;
  errorCategory: ErrorCategory | null;

  debateCache: Record<string, any>;
  debateVisibleCounts: Record<string, number>;
  debateFinished: Record<string, boolean>;

  fetchSessions: () => Promise<void>;
  fetchSessionDetail: (id: string) => Promise<void>;
  fetchAgentResults: (id: string) => Promise<void>;
  createSession: (resumeId: string, jd: string, company?: string, role?: string) => Promise<SessionResponse>;
  submitReviews: (sessionId: string, decisions: HumanReviewDecision[]) => Promise<void>;
  clearError: () => void;
  setDebateCache: (sessionId: string, data: any) => void;
  setDebateVisibleCount: (sessionId: string, count: number) => void;
  setDebateFinished: (sessionId: string, finished: boolean) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeSession: null,
  agentResults: [],
  isLoading: false,
  error: null,
  errorCategory: null,
  debateCache: {},
  debateVisibleCounts: {},
  debateFinished: {},

  clearError: () => set({ error: null, errorCategory: null }),
  
  setDebateCache: (sessionId, data) => set((state) => ({
    debateCache: { ...state.debateCache, [sessionId]: data }
  })),
  setDebateVisibleCount: (sessionId, count) => set((state) => ({
    debateVisibleCounts: { ...state.debateVisibleCounts, [sessionId]: count }
  })),
  setDebateFinished: (sessionId, finished) => set((state) => ({
    debateFinished: { ...state.debateFinished, [sessionId]: finished }
  })),

  fetchSessions: async () => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      const response = await api.get("/sessions");
      set({ sessions: response.data, isLoading: false });
    } catch (e) {
      const { message, category } = categorizeSessionError(e);
      set({ error: message, errorCategory: category, isLoading: false });
    }
  },

  fetchSessionDetail: async (id: string) => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      const response = await api.get(`/sessions/${id}`);
      set({ activeSession: response.data, isLoading: false });
    } catch (e) {
      const { message, category } = categorizeSessionError(e);
      set({ error: message, errorCategory: category, isLoading: false });
    }
  },

  fetchAgentResults: async (id: string) => {
    try {
      const response = await api.get(`/sessions/${id}/results`);
      set({ agentResults: response.data });
    } catch (e) {
      console.error("Failed to load agent logs:", e);
    }
  },

  createSession: async (resumeId: string, jd: string, company?: string, role?: string) => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      const response = await api.post("/sessions", {
        resume_id: resumeId,
        job_description: jd,
        target_company: company,
        target_role: role,
      });
      const newSession = response.data;
      set((state) => ({
        sessions: [newSession, ...state.sessions],
        activeSession: newSession,
        isLoading: false,
      }));
      return newSession;
    } catch (e) {
      const { message, category } = categorizeSessionError(e);
      set({ error: message, errorCategory: category, isLoading: false });
      throw new Error(message, { cause: e });
    }
  },

  submitReviews: async (sessionId: string, decisions: HumanReviewDecision[]) => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      const response = await api.post(`/sessions/${sessionId}/review`, { decisions });
      // Update active session status to completed
      set((state) => ({
        activeSession: state.activeSession
          ? { ...state.activeSession, status: response.data.status }
          : null,
        isLoading: false,
      }));
    } catch (e) {
      const { message, category } = categorizeSessionError(e);
      set({ error: message, errorCategory: category, isLoading: false });
      throw new Error(message, { cause: e });
    }
  },
}));
