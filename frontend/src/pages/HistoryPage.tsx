import { useEffect } from "react";
import { Link } from "react-router-dom";
import { History, ArrowRight } from "lucide-react";
import { useSessionStore } from "../stores/useSessionStore";
import { GlassCard } from "../components/shared/GlassCard";

export default function HistoryPage() {
  const { sessions, fetchSessions, isLoading } = useSessionStore();

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <History className="w-6 h-6 text-purple-400" />
          Tailoring Execution History
        </h2>
        <p className="text-xs text-muted-foreground">
          Review details and final compilations of all past multi-agent optimization runs.
        </p>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 space-y-4">
          <History className="w-10 h-10 text-purple-400 animate-spin" />
          <span className="text-xs text-slate-500">Loading tailoring records...</span>
        </div>
      ) : sessions.length === 0 ? (
        <GlassCard className="flex flex-col items-center justify-center text-center p-12 space-y-4">
          <History className="w-12 h-12 text-slate-600" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-slate-300">No session history</h4>
            <p className="text-xs text-slate-500 max-w-xs">
              Configure and run your first tailoring session from the new dashboard wizard.
            </p>
          </div>
          <Link
            to="/dashboard/new"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all duration-200"
          >
            New Session
          </Link>
        </GlassCard>
      ) : (
        <div className="space-y-4">
          {sessions.map((session) => (
            <GlassCard
              key={session.id}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 hover:border-purple-500/30 hover:bg-slate-900/30 transition-all duration-200"
            >
              <div className="space-y-1">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 uppercase">
                  {session.status}
                </span>
                <h3 className="text-md font-bold text-white pt-1">
                  {session.target_company || "Target Company"}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Role: {session.target_role || "Software Engineer"} • Started {new Date(session.created_at).toLocaleDateString()}
                </p>
              </div>

              <div className="flex items-center gap-6 self-start sm:self-auto">
                {session.ats_score_before !== null && (
                  <div className="text-right">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block">
                      ATS Score
                    </span>
                    <span className="text-md font-extrabold text-white">
                      {session.ats_score_before}%
                    </span>
                  </div>
                )}
                
                <Link
                  to={`/dashboard/session/${session.id}`}
                  className="px-4 py-2 text-xs font-bold rounded-lg bg-purple-600/15 hover:bg-purple-600/25 text-purple-300 border border-purple-500/20 transition-all duration-200 flex items-center gap-1 group"
                >
                  View Details
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
