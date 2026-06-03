import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Plus, FileText, ArrowRight, ShieldAlert, Sparkles } from "lucide-react";
import { useResumeStore } from "../stores/useResumeStore";
import { useSessionStore } from "../stores/useSessionStore";
import { GlassCard } from "../components/shared/GlassCard";

export default function DashboardPage() {
  const { resumes, fetchResumes, deleteResume } = useResumeStore();
  const { sessions, fetchSessions } = useSessionStore();

  useEffect(() => {
    fetchResumes();
    fetchSessions();
  }, [fetchResumes, fetchSessions]);

  return (
    <div className="space-y-8">
      {/* Header Panel */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Application Optimization Cockpit</h2>
          <p className="text-xs text-muted-foreground">
            Manage your resumes and monitor live tailoring sessions.
          </p>
        </div>
        <Link
          to="/dashboard/new"
          className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs shadow-lg hover:shadow-purple-500/20 transition-all duration-200 flex items-center justify-center gap-1.5 self-start"
        >
          <Plus className="w-4 h-4" />
          New Tailoring Session
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="flex flex-col justify-between h-32">
          <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
            Total Resumes
          </span>
          <span className="text-3xl font-extrabold text-white">{resumes.length}</span>
        </GlassCard>

        <GlassCard className="flex flex-col justify-between h-32">
          <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
            Tailoring Runs
          </span>
          <span className="text-3xl font-extrabold text-white">{sessions.length}</span>
        </GlassCard>

        <GlassCard className="flex flex-col justify-between h-32" accented>
          <span className="text-xs font-bold text-purple-300 uppercase tracking-widest flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            Avg. ATS Improvement
          </span>
          <span className="text-3xl font-extrabold text-gradient">+24%</span>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Resumes List Column */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-md font-bold text-white uppercase tracking-wider px-1">Uploaded Resumes</h3>
          {resumes.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center text-center p-8 space-y-4">
              <FileText className="w-12 h-12 text-slate-600" />
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-slate-300">No resumes found</h4>
                <p className="text-xs text-slate-500 max-w-xs">
                  Upload your first PDF or DOCX resume to start tailoring.
                </p>
              </div>
              <Link
                to="/dashboard/new"
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all duration-200"
              >
                Upload Resume
              </Link>
            </GlassCard>
          ) : (
            <div className="space-y-3">
              {resumes.map((resume) => (
                <GlassCard key={resume.id} className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className="bg-slate-800 p-2.5 rounded-xl border border-slate-700 text-slate-300">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="space-y-0.5">
                      <h4 className="text-sm font-bold text-white truncate max-w-xs">
                        {resume.original_filename}
                      </h4>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        Version {resume.version} • {resume.file_type}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => deleteResume(resume.id)}
                    className="text-xs text-slate-500 hover:text-red-400 p-2 rounded-lg hover:bg-slate-800/40 transition-colors duration-200"
                  >
                    Delete
                  </button>
                </GlassCard>
              ))}
            </div>
          )}
        </div>

        {/* Recent sessions column */}
        <div className="space-y-4">
          <h3 className="text-md font-bold text-white uppercase tracking-wider px-1">Recent Runs</h3>
          {sessions.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center text-center p-8 space-y-4">
              <ShieldAlert className="w-12 h-12 text-slate-600" />
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-slate-300">No session runs yet</h4>
                <p className="text-xs text-slate-500 max-w-xs">
                  Run your first tailoring pipeline against a job description.
                </p>
              </div>
            </GlassCard>
          ) : (
            <div className="space-y-3">
              {sessions.slice(0, 4).map((session) => (
                <GlassCard key={session.id} className="p-4 flex flex-col justify-between gap-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="text-sm font-bold text-white">
                        {session.target_company || "Target Company"}
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        {session.target_role || "Software Engineer"}
                      </p>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 uppercase">
                      {session.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-border/40 mt-1">
                    <span className="text-xs text-slate-400">
                      ATS: {session.ats_score_before ? `${session.ats_score_before}%` : "Pending"}
                    </span>
                    <Link
                      to={`/dashboard/session/${session.id}`}
                      className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 group"
                    >
                      Audit
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </Link>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
