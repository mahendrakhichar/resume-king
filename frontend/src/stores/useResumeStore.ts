import { create } from "zustand";
import api from "../lib/api";
import type { ResumeListItem, ResumeDetail } from "../types/resume";

// ─── Upload Progress Stages ────────────────────────────────────────
const UPLOAD_STAGES = [
  { at: 0, label: "Preparing upload..." },
  { at: 30, label: "Uploading file to server..." },
  { at: 45, label: "Extracting text from document..." },
  { at: 60, label: "AI parsing resume structure..." },
  { at: 75, label: "Saving to database..." },
  { at: 85, label: "Indexing for semantic matching..." },
  { at: 95, label: "Finalizing..." },
  { at: 100, label: "Complete!" },
];

function getStageLabel(progress: number): string {
  for (let i = UPLOAD_STAGES.length - 1; i >= 0; i--) {
    if (progress >= UPLOAD_STAGES[i].at) return UPLOAD_STAGES[i].label;
  }
  return UPLOAD_STAGES[0].label;
}

// ─── Error Categories ─────────────────────────────────────────────
export type ErrorCategory = "rate_limit" | "timeout" | "network" | "auth" | "parsing_error" | "unknown";

function categorizeError(e: unknown): { message: string; category: ErrorCategory } {
  const err = e as { response?: { status?: number; data?: { detail?: string; category?: string } }; code?: string; message?: string };

  // Network errors (no response at all)
  if (!err.response && (err.code === "ERR_NETWORK" || err.code === "ECONNABORTED")) {
    return {
      message: "Network connection issue — check your internet and retry.",
      category: "network",
    };
  }

  const status = err.response?.status;
  const detail = err.response?.data?.detail || "";
  const serverCategory = err.response?.data?.category;

  // Server-provided category
  if (serverCategory) {
    return { message: detail || "An error occurred", category: serverCategory as ErrorCategory };
  }

  // HTTP-based classification
  if (status === 429) return { message: "AI model rate limit reached — please wait and retry.", category: "rate_limit" };
  if (status === 401 || status === 403) return { message: "Authentication error — please sign in again.", category: "auth" };
  if (status === 408 || detail.toLowerCase().includes("timeout")) return { message: "Server processing timed out — click Retry to try again.", category: "timeout" };
  if (status === 500 && detail.toLowerCase().includes("rate")) return { message: "AI model rate limit reached — switched to backup model, retrying...", category: "rate_limit" };

  return {
    message: detail || "Resume processing failed. Please try again.",
    category: "unknown",
  };
}

// ─── Store Definition ─────────────────────────────────────────────

interface ResumeState {
  resumes: ResumeListItem[];
  activeResume: ResumeDetail | null;
  isLoading: boolean;
  error: string | null;
  errorCategory: ErrorCategory | null;

  // Upload progress tracking
  uploadProgress: number;       // 0-100
  uploadStage: string;          // Human-readable stage label
  isUploading: boolean;

  fetchResumes: () => Promise<void>;
  fetchResumeDetail: (id: string) => Promise<void>;
  uploadResume: (file: File) => Promise<ResumeDetail>;
  deleteResume: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useResumeStore = create<ResumeState>((set) => ({
  resumes: [],
  activeResume: null,
  isLoading: false,
  error: null,
  errorCategory: null,
  uploadProgress: 0,
  uploadStage: "",
  isUploading: false,

  clearError: () => set({ error: null, errorCategory: null }),

  fetchResumes: async () => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      const response = await api.get("/resumes");
      set({ resumes: response.data, isLoading: false });
    } catch (e) {
      const { message, category } = categorizeError(e);
      set({ error: message, errorCategory: category, isLoading: false });
    }
  },

  fetchResumeDetail: async (id: string) => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      const response = await api.get(`/resumes/${id}`);
      set({ activeResume: response.data, isLoading: false });
    } catch (e) {
      const { message, category } = categorizeError(e);
      set({ error: message, errorCategory: category, isLoading: false });
    }
  },

  uploadResume: async (file: File) => {
    set({
      isUploading: true,
      uploadProgress: 0,
      uploadStage: getStageLabel(0),
      error: null,
      errorCategory: null,
    });

    // Simulated server-side progress after upload completes
    let simulationTimer: ReturnType<typeof setInterval> | null = null;

    const startSimulation = () => {
      let simProgress = 35;
      simulationTimer = setInterval(() => {
        simProgress += Math.random() * 6 + 2; // Random 2-8% jumps
        if (simProgress >= 95) {
          simProgress = 95; // Cap until real completion
          if (simulationTimer) clearInterval(simulationTimer);
        }
        set({
          uploadProgress: Math.round(simProgress),
          uploadStage: getStageLabel(Math.round(simProgress)),
        });
      }, 800);
    };

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post("/resumes/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000, // 5 min timeout for large files + AI parsing
        onUploadProgress: (progressEvent) => {
          // Real upload progress: 0-30%
          if (progressEvent.total) {
            const uploadPct = Math.round((progressEvent.loaded / progressEvent.total) * 30);
            set({
              uploadProgress: uploadPct,
              uploadStage: getStageLabel(uploadPct),
            });

            // When upload completes, start simulating server processing
            if (progressEvent.loaded >= progressEvent.total && !simulationTimer) {
              startSimulation();
            }
          }
        },
      });

      // Upload + processing complete
      if (simulationTimer) clearInterval(simulationTimer);
      set({
        uploadProgress: 100,
        uploadStage: getStageLabel(100),
      });

      const newResume = response.data;

      // Brief pause to show 100% completion
      await new Promise((r) => setTimeout(r, 600));

      set((state) => ({
        resumes: [newResume, ...state.resumes],
        activeResume: newResume,
        isUploading: false,
        uploadProgress: 0,
        uploadStage: "",
      }));
      return newResume;

    } catch (e) {
      if (simulationTimer) clearInterval(simulationTimer);
      const { message, category } = categorizeError(e);
      set({
        error: message,
        errorCategory: category,
        isUploading: false,
        uploadProgress: 0,
        uploadStage: "",
      });
      throw new Error(message, { cause: e });
    }
  },

  deleteResume: async (id: string) => {
    set({ isLoading: true, error: null, errorCategory: null });
    try {
      await api.delete(`/resumes/${id}`);
      set((state) => ({
        resumes: state.resumes.filter((r) => r.id !== id),
        activeResume: state.activeResume?.id === id ? null : state.activeResume,
        isLoading: false,
      }));
    } catch (e) {
      const { message, category } = categorizeError(e);
      set({ error: message, errorCategory: category, isLoading: false });
    }
  },
}));
