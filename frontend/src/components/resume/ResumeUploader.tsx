import React, { useState } from "react";
import { FileUp, Sparkles, AlertCircle, RotateCcw } from "lucide-react";
import { useResumeStore } from "../../stores/useResumeStore";

interface ResumeUploaderProps {
  onUploadSuccess?: (resumeId: string) => void;
}

export function ResumeUploader({ onUploadSuccess }: ResumeUploaderProps) {
  const uploadResume = useResumeStore((state) => state.uploadResume);
  const uploadProgress = useResumeStore((state) => state.uploadProgress);
  const uploadStage = useResumeStore((state) => state.uploadStage);
  const isUploading = useResumeStore((state) => state.isUploading);
  const error = useResumeStore((state) => state.error);
  const errorCategory = useResumeStore((state) => state.errorCategory);
  const clearError = useResumeStore((state) => state.clearError);

  const [dragActive, setDragActive] = useState(false);
  const [lastFile, setLastFile] = useState<File | null>(null);

  const handleFile = async (file: File) => {
    if (!file) return;

    // Quick validation
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (ext !== ".pdf" && ext !== ".docx") {
      useResumeStore.setState({
        error: "Invalid file type. Please upload a PDF or DOCX resume.",
        errorCategory: "parsing_error",
      });
      return;
    }

    setLastFile(file);
    clearError();

    try {
      const resume = await uploadResume(file);
      if (onUploadSuccess) {
        onUploadSuccess(resume.id);
      }
    } catch {
      // Error already set in the store
    }
  };

  const handleRetry = () => {
    if (lastFile) {
      handleFile(lastFile);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  // ─── Error message helper ─────────────────────────────────────────
  const getErrorIcon = () => {
    switch (errorCategory) {
      case "rate_limit":
        return "⚡";
      case "timeout":
        return "⏱️";
      case "network":
        return "🌐";
      case "auth":
        return "🔒";
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center text-center transition-all duration-300 relative ${
          dragActive
            ? "border-purple-500 bg-purple-500/5"
            : isUploading
            ? "border-purple-600/30 bg-purple-950/5 cursor-wait"
            : "border-border/60 hover:border-purple-500/50 hover:bg-slate-900/40 cursor-pointer"
        }`}
      >
        <input
          type="file"
          id="resume-file-input"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
          onChange={handleFileInput}
          accept=".pdf,.docx"
        />

        {isUploading ? (
          /* ─── Progress Bar Upload State ────────────────────────── */
          <div className="space-y-5 flex flex-col items-center w-full max-w-md">
            {/* Sparkle animation */}
            <div className="relative">
              <Sparkles className="w-10 h-10 text-purple-400 animate-pulse" />
              <div className="absolute inset-0 w-10 h-10 rounded-full bg-purple-500/20 animate-ping" />
            </div>

            {/* Stage label */}
            <div className="space-y-1 text-center">
              <h4 className="text-md font-bold text-white flex items-center justify-center gap-1.5">
                <Sparkles className="w-4 h-4 text-purple-400" />
                AI Processing Resume
              </h4>
              <p className="text-xs text-slate-400 min-h-[1.2rem] transition-all duration-300">
                {uploadStage}
              </p>
            </div>

            {/* Progress bar */}
            <div className="w-full space-y-2">
              <div className="w-full h-3 bg-slate-800/80 rounded-full overflow-hidden border border-slate-700/50">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden"
                  style={{
                    width: `${uploadProgress}%`,
                    background: uploadProgress < 100
                      ? "linear-gradient(90deg, #7c3aed, #a855f7, #c084fc)"
                      : "linear-gradient(90deg, #22c55e, #4ade80)",
                  }}
                >
                  {/* Shimmer effect */}
                  <div
                    className="absolute inset-0 opacity-30"
                    style={{
                      background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)",
                      animation: "shimmer 2s infinite",
                    }}
                  />
                </div>
              </div>

              {/* Percentage text */}
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Processing</span>
                <span className="font-mono font-bold text-purple-300">
                  {uploadProgress}%
                </span>
              </div>
            </div>
          </div>
        ) : (
          /* ─── Idle Drop Zone ───────────────────────────────────── */
          <div className="space-y-4 flex flex-col items-center">
            <div className="p-4 rounded-full bg-slate-900 border border-border group-hover:scale-105 transition-transform duration-200">
              <FileUp className="w-8 h-8 text-slate-400" />
            </div>
            <div className="space-y-1.5">
              <h4 className="text-md font-bold text-white">Drag & drop your resume</h4>
              <p className="text-xs text-muted-foreground">
                Supports PDF and DOCX formats (Max 10MB)
              </p>
            </div>
            <button className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 pointer-events-none">
              Browse Files
            </button>
          </div>
        )}
      </div>

      {/* ─── Error Toast with Retry ────────────────────────────────── */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-950/20 border border-red-500/20 text-sm animate-in slide-in-from-top-2 duration-300">
          <div className="flex items-center gap-2 shrink-0 mt-0.5">
            {getErrorIcon() ? (
              <span className="text-base">{getErrorIcon()}</span>
            ) : (
              <AlertCircle className="w-4.5 h-4.5 text-red-400" />
            )}
          </div>

          <div className="flex-1 space-y-2">
            <p className="text-red-200 text-xs leading-relaxed">{error}</p>

            {/* Category-specific hint */}
            {errorCategory === "rate_limit" && (
              <p className="text-red-400/60 text-[11px]">
                The AI model hit its request limit. The system automatically tries backup models.
              </p>
            )}
            {errorCategory === "timeout" && (
              <p className="text-red-400/60 text-[11px]">
                Server took longer than 5 minutes. This can happen with complex resumes or high AI traffic.
              </p>
            )}
            {errorCategory === "network" && (
              <p className="text-red-400/60 text-[11px]">
                Could not reach the server. Check your internet connection.
              </p>
            )}
          </div>

          {/* Retry button */}
          {lastFile && (errorCategory === "timeout" || errorCategory === "rate_limit" || errorCategory === "network" || errorCategory === "unknown") && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRetry();
              }}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/20 transition-colors duration-200"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Retry
            </button>
          )}
        </div>
      )}

      {/* Shimmer keyframe style (injected inline for portability) */}
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}
