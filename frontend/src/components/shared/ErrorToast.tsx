import React, { useEffect, useState } from "react";
import { AlertCircle, RotateCcw, X, Wifi, Clock, Zap, Lock } from "lucide-react";
import type { ErrorCategory } from "../../stores/useResumeStore";

interface ErrorToastProps {
  message: string;
  category?: ErrorCategory | null;
  onRetry?: () => void;
  onDismiss?: () => void;
  autoDismissMs?: number;
}

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; color: string; hint: string }> = {
  rate_limit: {
    icon: <Zap className="w-4.5 h-4.5" />,
    color: "amber",
    hint: "The AI model hit its request limit. The system automatically tries backup models.",
  },
  timeout: {
    icon: <Clock className="w-4.5 h-4.5" />,
    color: "orange",
    hint: "Server took longer than 5 minutes. This can happen with complex resumes or high AI traffic.",
  },
  network: {
    icon: <Wifi className="w-4.5 h-4.5" />,
    color: "blue",
    hint: "Could not reach the server. Check your internet connection.",
  },
  auth: {
    icon: <Lock className="w-4.5 h-4.5" />,
    color: "purple",
    hint: "Your session has expired. Please sign in again.",
  },
  unknown: {
    icon: <AlertCircle className="w-4.5 h-4.5" />,
    color: "red",
    hint: "",
  },
  parsing_error: {
    icon: <AlertCircle className="w-4.5 h-4.5" />,
    color: "red",
    hint: "The document could not be processed. Try a different file format.",
  },
};

export function ErrorToast({ message, category, onRetry, onDismiss, autoDismissMs }: ErrorToastProps) {
  const [visible, setVisible] = useState(true);
  const config = CATEGORY_CONFIG[category || "unknown"] || CATEGORY_CONFIG.unknown;

  useEffect(() => {
    if (autoDismissMs && autoDismissMs > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        onDismiss?.();
      }, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [autoDismissMs, onDismiss]);

  if (!visible) return null;

  const colorMap: Record<string, string> = {
    red: "bg-red-950/25 border-red-500/25 text-red-200",
    amber: "bg-amber-950/25 border-amber-500/25 text-amber-200",
    orange: "bg-orange-950/25 border-orange-500/25 text-orange-200",
    blue: "bg-blue-950/25 border-blue-500/25 text-blue-200",
    purple: "bg-purple-950/25 border-purple-500/25 text-purple-200",
  };

  const iconColorMap: Record<string, string> = {
    red: "text-red-400",
    amber: "text-amber-400",
    orange: "text-orange-400",
    blue: "text-blue-400",
    purple: "text-purple-400",
  };

  const containerClasses = colorMap[config.color] || colorMap.red;
  const iconClasses = iconColorMap[config.color] || iconColorMap.red;

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl border text-sm ${containerClasses}`}
      style={{ animation: "slideInFromTop 0.3s ease-out" }}
      role="alert"
    >
      {/* Icon */}
      <div className={`shrink-0 mt-0.5 ${iconClasses}`}>{config.icon}</div>

      {/* Content */}
      <div className="flex-1 space-y-1.5">
        <p className="text-xs leading-relaxed font-medium">{message}</p>
        {config.hint && (
          <p className="text-[11px] opacity-60">{config.hint}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        {onRetry && (category === "timeout" || category === "rate_limit" || category === "network" || category === "unknown") && (
          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors duration-200"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={() => {
              setVisible(false);
              onDismiss();
            }}
            className="p-1 rounded-md hover:bg-white/10 transition-colors"
          >
            <X className="w-3.5 h-3.5 opacity-50" />
          </button>
        )}
      </div>

      <style>{`
        @keyframes slideInFromTop {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
