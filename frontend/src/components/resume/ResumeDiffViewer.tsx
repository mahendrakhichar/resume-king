import { Sparkles } from "lucide-react";
import { GlassCard } from "../shared/GlassCard";

interface DiffBullet {
  original: string;
  suggested: string;
  reasoning: string;
}

interface ResumeDiffViewerProps {
  sectionName: string;
  bullets: DiffBullet[];
  onDecision?: (idx: number, action: "accepted" | "rejected" | "edited") => void;
  onBulletEdit?: (idx: number, newValue: string) => void;
  decisions?: Record<number, "accepted" | "rejected" | "edited">;
}

export function ResumeDiffViewer({
  sectionName,
  bullets,
  onDecision,
  onBulletEdit,
  decisions = {}
}: ResumeDiffViewerProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 pb-2 border-b border-border">
        <h4 className="text-md font-bold text-white uppercase tracking-wider">{sectionName}</h4>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          AI Suggestion Diff
        </span>
      </div>

      <div className="space-y-4">
        {bullets.map((bullet, idx) => {
          const status = decisions[idx];

          return (
            <GlassCard
              key={idx}
              className={`border-l-4 transition-all duration-300 ${
                status === "accepted"
                  ? "border-l-emerald-500 bg-emerald-950/5"
                  : status === "rejected"
                  ? "border-l-red-500 bg-red-950/5"
                  : "border-l-purple-500"
              }`}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Original content pane */}
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                    Original Bullet
                  </span>
                  <div className="p-3 rounded-lg bg-red-950/10 border border-red-500/10 text-sm text-red-200/90 text-justify">
                    {bullet.original}
                  </div>
                </div>

                {/* Suggested optimization pane (Sandbox) */}
                <div className="space-y-2 relative">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-1">
                      <Sparkles className="w-3 h-3 animate-spin" style={{ animationDuration: "3s" }} />
                      AI Optimization (Editable Sandbox)
                    </span>
                  </div>
                  <textarea
                    value={bullet.suggested}
                    onChange={(e) => onBulletEdit?.(idx, e.target.value)}
                    rows={Math.max(3, Math.ceil(bullet.suggested.length / 60))}
                    className="w-full p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-sm text-emerald-100 font-medium focus:outline-none focus:border-emerald-500/50 resize-y transition-all leading-relaxed"
                    placeholder="Refine your bullet point here..."
                  />
                </div>
              </div>

              {/* AI reasoning tag */}
              {bullet.reasoning && (
                <div className="mt-3 text-xs text-purple-300/80 bg-purple-950/10 p-2.5 rounded-lg border border-purple-500/15">
                  <strong>Why this change:</strong> {bullet.reasoning}
                </div>
              )}

              {/* Accept / Reject controls */}
              {onDecision && (
                <div className="flex items-center justify-end gap-3 mt-4 pt-3 border-t border-border/40">
                  <button
                    onClick={() => onDecision(idx, "rejected")}
                    className={`px-3 py-1 text-xs rounded-lg border transition-all duration-200 ${
                      status === "rejected"
                        ? "bg-red-500/20 text-red-300 border-red-500/50"
                        : "border-border hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20"
                    }`}
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => onDecision(idx, "accepted")}
                    className={`px-3 py-1 text-xs rounded-lg border transition-all duration-200 font-semibold ${
                      status === "accepted"
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                        : "border-border hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/20"
                    }`}
                  >
                    Accept
                  </button>
                </div>
              )}
            </GlassCard>
          );
        })}
      </div>
    </div>
  );
}
