import { useEffect, useState } from "react";
import { MessageSquare, ShieldCheck, Terminal, Award, HelpCircle, Loader2 } from "lucide-react";
import { GlassCard } from "../shared/GlassCard";
import api from "../../lib/api";
import { useSessionStore } from "../../stores/useSessionStore";

interface DebateMessage {
  speaker: "AI Recruiter" | "AI Tech Lead";
  text: string;
}

interface DebateResponse {
  dialogue: DebateMessage[];
  decision: "Approve" | "Approve with Reservations" | "Reject";
  summary_verdict: string;
}

interface HiringDebatePanelProps {
  sessionId: string;
}

export function HiringDebatePanel({ sessionId }: HiringDebatePanelProps) {
  const {
    debateCache,
    debateVisibleCounts,
    debateFinished,
    setDebateCache,
    setDebateVisibleCount,
    setDebateFinished,
  } = useSessionStore();

  const cachedDebate = debateCache[sessionId] as DebateResponse | undefined;
  const isFinished = debateFinished[sessionId] || false;
  const initialCount = debateVisibleCounts[sessionId] || 0;

  const [loading, setLoading] = useState(!cachedDebate);
  const [error, setError] = useState(false);
  const [visibleMessages, setVisibleMessages] = useState<DebateMessage[]>(() => {
    if (cachedDebate) {
      if (isFinished) {
        return cachedDebate.dialogue || [];
      } else {
        return (cachedDebate.dialogue || []).slice(0, initialCount);
      }
    }
    return [];
  });

  useEffect(() => {
    let active = true;
    let intervalId: any = null;

    const getDebate = async () => {
      let data = cachedDebate;
      if (!data) {
        try {
          setLoading(true);
          const res = await api.get<DebateResponse>(`/sessions/${sessionId}/debate`);
          if (active) {
            data = res.data;
            setDebateCache(sessionId, data);
            setLoading(false);
          }
        } catch (e) {
          console.error("Failed to load committee debate:", e);
          if (active) {
            setError(true);
            setLoading(false);
          }
          return;
        }
      }

      if (!data || !active) return;

      const dialogue = data.dialogue || [];
      const doneAlready = debateFinished[sessionId] || false;

      if (doneAlready) {
        setVisibleMessages(dialogue);
      } else {
        let count = debateVisibleCounts[sessionId] || 0;
        setVisibleMessages(dialogue.slice(0, count));

        intervalId = setInterval(() => {
          if (count < dialogue.length) {
            const nextMsg = dialogue[count];
            if (nextMsg) {
              setVisibleMessages((prev) => [...prev, nextMsg]);
            }
            count++;
            setDebateVisibleCount(sessionId, count);
          } else {
            setDebateFinished(sessionId, true);
            if (intervalId) clearInterval(intervalId);
          }
        }, 1500);
      }
    };

    getDebate();

    return () => {
      active = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const debateData = cachedDebate;

  if (loading) {
    return (
      <GlassCard className="p-8 flex flex-col items-center justify-center text-center space-y-4 min-h-[300px] border-purple-500/10">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        <div className="space-y-1">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center justify-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-purple-400" />
            Committee Convening...
          </h4>
          <p className="text-[10px] text-slate-400 max-w-xs">
            Assembling AI Tech Lead and AI Recruiter agents. Analyzing tailored resume metrics against job demands...
          </p>
        </div>
      </GlassCard>
    );
  }

  if (error || !debateData) {
    return (
      <GlassCard className="p-8 flex flex-col items-center justify-center text-center space-y-4 min-h-[300px] border-red-500/10">
        <HelpCircle className="w-8 h-8 text-red-400" />
        <div className="space-y-1">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">Debate Unavailable</h4>
          <p className="text-[10px] text-slate-400">
            Hiring committee failed to form consensus. Please refresh or check connection.
          </p>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Slack-style Chat interface */}
      <GlassCard className="lg:col-span-2 p-4 bg-background/25 border-border/40 min-h-[300px] flex flex-col justify-between">
        {/* Room Header */}
        <div className="w-full flex items-center justify-between border-b border-border/40 pb-3 mb-4 select-none">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-extrabold text-white font-mono lowercase">
              #hiring-committee-debate
            </span>
          </div>
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Active Channel
          </span>
        </div>

        {/* Dialog Stream bubble list */}
        <div className="flex-1 space-y-4 overflow-y-auto max-h-72 p-2 select-text font-sans text-xs">
          {visibleMessages.map((msg, idx) => {
            if (!msg || !msg.speaker) return null;
            const isTech = msg.speaker === "AI Tech Lead";
            return (
              <div key={idx} className="flex items-start gap-3 animate-fadeIn">
                {/* Custom User Avatar */}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border select-none ${
                  isTech 
                    ? "bg-purple-950/40 border-purple-500/30 text-purple-300"
                    : "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
                }`}>
                  {isTech ? "👨‍💻" : "🕵️‍♂️"}
                </div>

                {/* Bubble details */}
                <div className="space-y-1 leading-normal">
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${isTech ? "text-purple-400" : "text-emerald-400"}`}>
                      {msg.speaker}
                    </span>
                    <span className="text-[8px] text-slate-500">Agent</span>
                  </div>
                  <p className="text-slate-200 leading-relaxed text-justify bg-background/20 p-2.5 rounded-r-lg rounded-bl-lg border border-border/30 max-w-md">
                    {msg.text}
                  </p>
                </div>
              </div>
            );
          })}

          {visibleMessages.length < (debateData.dialogue?.length || 0) && (
            <div className="flex items-center gap-2 text-slate-500 pl-11 text-[10px] select-none">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Agents deliberating...</span>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Decision and summary verdict card */}
      <GlassCard className="p-4 bg-background/25 border-border/40 min-h-[300px] flex flex-col justify-between select-text">
        <div className="space-y-4">
          <div className="flex items-center gap-1.5 border-b border-border/40 pb-3">
            <ShieldCheck className="w-4 h-4 text-purple-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              Committee Decision
            </h4>
          </div>

          {/* Glowing Status badge */}
          {visibleMessages.length === (debateData.dialogue?.length || 0) ? (
            <div className="space-y-4">
              <div className="flex flex-col items-center justify-center py-5 bg-background/40 rounded-xl border border-border/50 select-none">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">
                  Consensus Verdict
                </span>
                <span className={`text-xs font-extrabold px-3 py-1 rounded-full uppercase tracking-wider border shadow-md ${
                  debateData.decision === "Approve"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-emerald-500/5"
                    : debateData.decision === "Approve with Reservations"
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30 shadow-amber-500/5"
                    : "bg-red-500/10 text-red-400 border-red-500/30 shadow-red-500/5"
                }`}>
                  {debateData.decision}
                </span>
              </div>

              {/* Verdict Summary block */}
              <div className="space-y-1.5 leading-normal">
                <span className="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                  <Award className="w-3.5 h-3.5 text-purple-400" />
                  Hiring Verdict Summary
                </span>
                <p className="text-[11px] text-slate-300 leading-relaxed text-justify bg-background/25 p-3 rounded-lg border border-border/40 font-medium">
                  {debateData.summary_verdict}
                </p>
              </div>
            </div>
          ) : (
            <div className="h-40 flex flex-col items-center justify-center text-center p-4 space-y-2 select-none">
              <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
              <span className="text-[10px] text-slate-400">Waiting for consensus...</span>
            </div>
          )}
        </div>

        <div className="text-[9px] text-slate-500 leading-normal pt-2 border-t border-border/40 select-none">
          Hiring decisions are computed using multi-perspective semantic alignment evaluations across experience levels, frameworks, and system scaling requirements.
        </div>
      </GlassCard>
    </div>
  );
}
