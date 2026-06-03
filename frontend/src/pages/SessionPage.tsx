import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { Loader2, FileDown, ArrowLeft, Check, AlertTriangle, Copy, Award, MessageSquare, Terminal, ChevronDown, ChevronUp } from "lucide-react";

import { useSessionStore } from "../stores/useSessionStore";
import api from "../lib/api";
import { useWebSocket } from "../hooks/useWebSocket";
import { GlassCard } from "../components/shared/GlassCard";
import { AgentWorkflowPanel } from "../components/agents/AgentWorkflowPanel";
import { ATSScoreGauge } from "../components/agents/ATSScoreGauge";
import { HumanReviewPanel } from "../components/review/HumanReviewPanel";
import { SkillGapGraph } from "../components/agents/SkillGapGraph";
import { HiringDebatePanel } from "../components/agents/HiringDebatePanel";
import type { HumanReviewDecision } from "../types/session";


export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const {
    activeSession,
    agentResults,
    fetchSessionDetail,
    fetchAgentResults,
    submitReviews,
  } = useSessionStore();
  const [reviewIsSubmitting, setReviewIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<"dashboard" | "interview" | "outreach" | "ats">("dashboard");
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [openTips, setOpenTips] = useState<Record<number, boolean>>({});
  
  const [prevStatus, setPrevStatus] = useState<string | null>(null);
  const [showScoreCelebration, setShowScoreCelebration] = useState(false);
  const [timerFinished, setTimerFinished] = useState(false);

  useEffect(() => {
    if (activeSession) {
      if (prevStatus && prevStatus !== "completed" && activeSession.status === "completed") {
        setShowScoreCelebration(true);
        setTimerFinished(false);
        
        // Minimum time timer
        const timer = setTimeout(() => {
          setTimerFinished(true);
        }, 2000);

        // Safety timeout to close celebration regardless after 8 seconds
        const safetyTimer = setTimeout(() => {
          setShowScoreCelebration(false);
        }, 8000);

        return () => {
          clearTimeout(timer);
          clearTimeout(safetyTimer);
        };
      }
      setPrevStatus(activeSession.status);
    }
  }, [activeSession?.status, prevStatus]);

  useEffect(() => {
    if (showScoreCelebration && timerFinished) {
      const hasAfterScore = activeSession?.ats_score_after != null;
      if (hasAfterScore) {
        // Let the user see the final score for 1.5 seconds, then close the overlay
        const closeTimer = setTimeout(() => {
          setShowScoreCelebration(false);
        }, 1500);
        return () => clearTimeout(closeTimer);
      }
    }
  }, [showScoreCelebration, timerFinished, activeSession?.ats_score_after]);

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const toggleTip = (idx: number) => {
    setOpenTips((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // Poll agent results on startup
  useEffect(() => {
    if (id) {
      fetchSessionDetail(id);
      fetchAgentResults(id);
    }
  }, [id, fetchSessionDetail, fetchAgentResults]);

  // WebSocket message receiver callback
  const handleWebSocketMessage = useCallback(
    (update: unknown) => {
      console.log("WS live update:", update);
      if (id) {
        // Refresh session detail and execution logs
        fetchSessionDetail(id);
        fetchAgentResults(id);
      }
    },
    [id, fetchSessionDetail, fetchAgentResults]
  );

  // Bind WebSocket
  useWebSocket(id, handleWebSocketMessage);

  const handleReviewSubmit = async (decisions: HumanReviewDecision[]) => {
    if (!id) return;
    setReviewIsSubmitting(true);
    try {
      await submitReviews(id, decisions);
      setReviewIsSubmitting(false);
      // Reload session
      fetchSessionDetail(id);
    } catch (e) {
      setReviewIsSubmitting(false);
      console.error(e);
    }
  };

  const handleDownloadPDF = async () => {
    if (!id) return;
    try {
      const response = await api.get(`/export/${id}/pdf`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const contentDisposition = response.headers["content-disposition"];
      let filename = "tailored-resume.pdf";
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Failed to download PDF", e);
    }
  };

  if (!activeSession) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-10 h-10 text-purple-400 animate-spin" />
        <span className="text-xs text-muted-foreground">Syncing session telemetry...</span>
      </div>
    );
  }

  // Filter agent results to get rewriter and project optimization results for the review pane
  const suggestions = agentResults
    .filter((r) => r.agent_type === "resume_rewriter" || r.agent_type === "project_optimizer")
    .map((r) => ({
      id: r.id,
      agent_type: r.agent_type,
      output_data: r.output_data,
      reasoning: r.reasoning,
    }));

  // Find completed agent outputs
  const interviewResult = agentResults.find((r) => r.agent_type === "interview_agent" && r.status === "success");
  const recruiterResult = agentResults.find((r) => r.agent_type === "recruiter_agent" && r.status === "success");
  const atsResult = activeSession.status === "completed"
    ? [...agentResults].reverse().find((r) => r.agent_type === "ats_matcher" && r.status === "success")
    : agentResults.find((r) => r.agent_type === "ats_matcher" && r.status === "success");

  // Typecast or parse their data
  const interviewData = interviewResult?.output_data as {
    questions?: { category: string; question: string; difficulty?: string; tips?: string }[];
    preparation_tips?: string[];
  } | undefined;

  const recruiterData = recruiterResult?.output_data as {
    linkedin_connection?: string;
    referral_request?: string;
    cold_email?: string;
    follow_up?: string;
  } | undefined;

  const atsData = atsResult?.output_data as {
    overall_score?: number;
    keyword_match_rate?: number;
    missing_keywords?: string[];
    matched_keywords?: string[];
    suggestions?: string[];
  } | undefined;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Session Breadcrumbs & Meta */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            to="/dashboard"
            className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 w-fit group"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            Back to Dashboard
          </Link>
          <h2 className="text-2xl font-bold text-white">
            Tailoring for {activeSession.target_company || "Target Company"}
          </h2>
          <p className="text-xs text-muted-foreground">
            Target Role: {activeSession.target_role || "Software Engineer"}
          </p>
        </div>

        {activeSession.status === "completed" && !showScoreCelebration && (
          <div className="flex flex-wrap items-center gap-3 self-start md:self-center animate-fadeIn">
            {(activeSession.ats_score_after ?? activeSession.ats_score_before) != null && (
              <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-purple-950/40 border border-purple-500/30 shadow-[0_0_15px_rgba(139,92,246,0.1)] select-none">
                <span className="text-[9px] font-extrabold text-purple-300 uppercase tracking-widest">
                  ATS Score
                </span>
                <span className="text-xs font-black text-white px-2 py-0.5 rounded bg-purple-600/30">
                  {Math.round(activeSession.ats_score_after ?? activeSession.ats_score_before ?? 0)}
                </span>
              </div>
            )}
            <button
              onClick={handleDownloadPDF}
              className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs shadow-lg hover:shadow-purple-500/20 transition-all duration-200 flex items-center justify-center gap-1.5"
            >
              <FileDown className="w-4 h-4" />
              Download PDF Resume
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Side: Graph pipeline timeline */}
        <div className={activeSession.status === "completed" ? "lg:col-span-3 space-y-6" : "lg:col-span-2 space-y-6"}>
          {activeSession.status === "review" && suggestions.length > 0 ? (
            <HumanReviewPanel
              suggestions={suggestions}
              onSubmit={handleReviewSubmit}
              isSubmitting={reviewIsSubmitting}
              parsedResume={activeSession.parsed_resume}
              jobAnalysis={activeSession.job_analysis}
              initialAtsData={atsData}
            />
          ) : activeSession.status === "completed" ? (
            <div className="space-y-6">
              {/* Tab Navigation */}
              <div className="flex border-b border-border/50 gap-4 overflow-x-auto pb-px">
                <button
                  onClick={() => setActiveTab("dashboard")}
                  className={`pb-3 text-sm font-semibold border-b-2 transition-all px-1 whitespace-nowrap ${
                    activeTab === "dashboard"
                      ? "border-purple-500 text-purple-400 font-bold"
                      : "border-transparent text-muted-foreground hover:text-white"
                  }`}
                >
                  Overview &amp; Download
                </button>
                {atsData && (
                  <button
                    onClick={() => setActiveTab("ats")}
                    className={`pb-3 text-sm font-semibold border-b-2 transition-all px-1 whitespace-nowrap ${
                      activeTab === "ats"
                        ? "border-purple-500 text-purple-400 font-bold"
                        : "border-transparent text-muted-foreground hover:text-white"
                    }`}
                  >
                    ATS Match Insights
                  </button>
                )}
                {interviewData?.questions && interviewData.questions.length > 0 && (
                  <button
                    onClick={() => setActiveTab("interview")}
                    className={`pb-3 text-sm font-semibold border-b-2 transition-all px-1 whitespace-nowrap ${
                      activeTab === "interview"
                        ? "border-purple-500 text-purple-400 font-bold"
                        : "border-transparent text-muted-foreground hover:text-white"
                    }`}
                  >
                    Mock Interview Vault
                  </button>
                )}
                {recruiterData && (
                  <button
                    onClick={() => setActiveTab("outreach")}
                    className={`pb-3 text-sm font-semibold border-b-2 transition-all px-1 whitespace-nowrap ${
                      activeTab === "outreach"
                        ? "border-purple-500 text-purple-400 font-bold"
                        : "border-transparent text-muted-foreground hover:text-white"
                    }`}
                  >
                    Recruiter Outreach Suite
                  </button>
                )}
              </div>

              {/* Tab Content */}
              {/* Tab Content */}
              <div className={activeTab === "dashboard" ? "block space-y-6" : "hidden"}>
                {/* Slim download banner */}
                <GlassCard className="flex flex-col md:flex-row items-center justify-between p-6 gap-4 border-emerald-500/20">
                  <div className="flex items-center gap-3.5">
                    <div className="bg-emerald-500/10 p-2.5 rounded-full border border-emerald-500/20 text-emerald-400">
                      <Check className="w-5 h-5" />
                    </div>
                    <div className="space-y-0.5 text-left">
                      <h4 className="text-sm font-bold text-white">Tailoring Complete &amp; Compiled!</h4>
                      <p className="text-xs text-slate-400">
                        Your final customized resume is ready for download in standard, ATS-optimized PDF.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleDownloadPDF}
                    className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-lg hover:shadow-emerald-500/20 transition-all duration-200 flex items-center gap-1.5 shrink-0"
                  >
                    <FileDown className="w-4 h-4" />
                    Download Resume PDF
                  </button>
                </GlassCard>

                {/* Hiring Committee Debate Widget */}
                {!showScoreCelebration && <HiringDebatePanel sessionId={id!} />}
              </div>

              {atsData && (
                <div className={activeTab === "ats" ? "block" : "hidden"}>
                  <GlassCard className="p-8 space-y-8">
                    <div className="flex items-center gap-2">
                      <Award className="w-5 h-5 text-purple-400" />
                      <h3 className="text-lg font-bold text-white">ATS Alignment &amp; Skill Gap Mapping</h3>
                    </div>

                    {/* Traditional Keyword List Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-background/40 p-4 rounded-xl border border-border/50">
                        <span className="text-xs text-muted-foreground block mb-2 font-semibold">Matched Keywords</span>
                        {atsData.matched_keywords && atsData.matched_keywords.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5 font-mono">
                            {atsData.matched_keywords.map((kw, idx) => (
                              <span key={idx} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                {kw}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">No keywords matched yet.</span>
                        )}
                      </div>

                      <div className="bg-background/40 p-4 rounded-xl border border-border/50">
                        <span className="text-xs text-muted-foreground block mb-2 font-semibold">Missing Keywords (Skill Gaps)</span>
                        {atsData.missing_keywords && atsData.missing_keywords.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5 font-mono">
                            {atsData.missing_keywords.map((kw, idx) => (
                              <span key={idx} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                                {kw}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">Excellent! No major keyword gaps.</span>
                        )}
                      </div>
                    </div>

                    {/* Skill Gap Interactive Network Graph */}
                    <div className="pt-6 border-t border-border/40">
                      <SkillGapGraph
                        matchedKeywords={atsData.matched_keywords}
                        missingKeywords={atsData.missing_keywords}
                      />
                    </div>

                    {atsData.suggestions && atsData.suggestions.length > 0 && (
                      <div className="space-y-3 pt-4 border-t border-border/40">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">ATS Optimization Roadmap</h4>
                        <ul className="space-y-2 list-disc pl-4 text-xs text-slate-300">
                          {atsData.suggestions.map((sug, idx) => (
                            <li key={idx} className="leading-relaxed">{sug}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </GlassCard>
                </div>
              )}

              {interviewData && (
                <div className={activeTab === "interview" ? "block" : "hidden"}>
                  <GlassCard className="p-8 space-y-6">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-5 h-5 text-purple-400" />
                      <h3 className="text-lg font-bold text-white">Technical &amp; Behavioral Interview Vault</h3>
                    </div>

                    <p className="text-xs text-muted-foreground">
                      Custom-curated DSA, HR, System Design, and Resume-specific questions based on the target requirements.
                    </p>

                    <div className="space-y-4 mt-4">
                      {interviewData.questions?.map((item, idx) => (
                        <div key={idx} className="bg-background/35 rounded-xl border border-border/40 p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                              {item.category === "hr" ? "Behavioral & HR" : item.category === "dsa" ? "DSA / Algorithms" : item.category === "system_design" ? "System Design" : "Project / Resume Audit"}
                            </span>
                            {item.difficulty && (
                              <span className={`text-[10px] font-bold ${
                                item.difficulty.toLowerCase() === "easy" ? "text-emerald-400" : item.difficulty.toLowerCase() === "medium" ? "text-amber-400" : "text-red-400"
                              }`}>
                                {item.difficulty}
                              </span>
                            )}
                          </div>
                          <h4 className="text-xs md:text-sm font-semibold text-white leading-relaxed">
                            {item.question}
                          </h4>
                          {item.tips && (
                            <div className="space-y-2">
                              <button
                                onClick={() => toggleTip(idx)}
                                className="text-[10px] font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-0.5"
                              >
                                {openTips[idx] ? (
                                  <>Hide Interview Strategy <ChevronUp className="w-3 h-3" /></>
                                ) : (
                                  <>Reveal Interview Strategy <ChevronDown className="w-3 h-3" /></>
                                )}
                              </button>
                              {openTips[idx] && (
                                <div className="text-[11px] text-emerald-400/90 bg-emerald-950/20 p-3 rounded-lg border border-emerald-500/10 leading-relaxed">
                                  <strong>Prep Tip:</strong> {item.tips}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {interviewData.preparation_tips && interviewData.preparation_tips.length > 0 && (
                      <div className="mt-6 pt-6 border-t border-border/40 space-y-3">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Expert Preparation Tips</h4>
                        <ul className="space-y-1.5 list-disc pl-4 text-xs text-slate-300">
                          {interviewData.preparation_tips.map((tip, idx) => (
                            <li key={idx} className="leading-relaxed">{tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </GlassCard>
                </div>
              )}

              {recruiterData && (
                <div className={activeTab === "outreach" ? "block" : "hidden"}>
                  <GlassCard className="p-8 space-y-6">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-5 h-5 text-purple-400" />
                      <h3 className="text-lg font-bold text-white">Recruiter Outreach Suite</h3>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Copy these customized templates to build direct human connections with hiring managers and referrers.
                    </p>

                    <div className="space-y-6 mt-4">
                      {recruiterData.linkedin_connection && (
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-slate-300">LinkedIn Connection Request (300 Char Limit)</span>
                            <button
                              onClick={() => handleCopy(recruiterData.linkedin_connection!, "linkedin")}
                              className="text-[10px] font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                            >
                              <Copy className="w-3 h-3" />
                              {copiedText === "linkedin" ? "Copied!" : "Copy"}
                            </button>
                          </div>
                          <div className="bg-background/40 p-3.5 rounded-xl border border-border/50 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap select-all">
                            {recruiterData.linkedin_connection}
                          </div>
                        </div>
                      )}

                      {recruiterData.referral_request && (
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-slate-300">Warm Referral Request Draft</span>
                            <button
                              onClick={() => handleCopy(recruiterData.referral_request!, "referral")}
                              className="text-[10px] font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                            >
                              <Copy className="w-3 h-3" />
                              {copiedText === "referral" ? "Copied!" : "Copy"}
                            </button>
                          </div>
                          <div className="bg-background/40 p-3.5 rounded-xl border border-border/50 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap select-all">
                            {recruiterData.referral_request}
                          </div>
                        </div>
                      )}

                      {recruiterData.cold_email && (
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-slate-300">Direct Cold Outreach Email</span>
                            <button
                              onClick={() => handleCopy(recruiterData.cold_email!, "email")}
                              className="text-[10px] font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1"
                            >
                              <Copy className="w-3 h-3" />
                              {copiedText === "email" ? "Copied!" : "Copy"}
                            </button>
                          </div>
                          <div className="bg-background/40 p-3.5 rounded-xl border border-border/50 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap select-all">
                            {recruiterData.cold_email}
                          </div>
                        </div>
                      )}
                    </div>
                  </GlassCard>
                </div>
              )}
            </div>
          ) : activeSession.status === "failed" ? (
            <GlassCard className="flex flex-col items-center justify-center text-center p-12 space-y-6">
              <div className="bg-red-500/10 p-4 rounded-full border border-red-500/20 text-red-400">
                <AlertTriangle className="w-10 h-10" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-white">Agent Execution Error</h3>
                <p className="text-xs text-slate-400 max-w-sm">
                  An error occurred during one of the agent runs. Check your API keys in the `.env` settings.
                </p>
              </div>
            </GlassCard>
          ) : (
            <GlassCard className="flex flex-col items-center justify-center text-center p-12 space-y-6">
              <Loader2 className="w-12 h-12 text-purple-400 animate-spin" />
              <div className="space-y-2">
                <h3 className="text-lg font-bold text-white">AI Multi-Agent Workflow In Progress...</h3>
                <p className="text-xs text-slate-400 max-w-sm">
                  The agents are currently executing analysis, scoring, and rewrites in parallel. Follow the workflow tracker on the right.
                </p>
              </div>
            </GlassCard>
          )}
        </div>

        {/* Right Side: Score indicator & Workflow pipeline */}
        {activeSession.status !== "completed" && (
          <div className="space-y-6">
            {/* Score Gauge */}
            {activeSession.ats_score_before != null && (
              <GlassCard className="flex flex-col items-center justify-center text-center py-8">
                <ATSScoreGauge score={activeSession.ats_score_before} />
                <div className="mt-4">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                    Initial Fit Compatibility
                  </span>
                </div>
              </GlassCard>
            )}

            {/* Real-time Agent workflow tracker panel */}
            {activeSession.status === "running" && (
              <GlassCard>
                <AgentWorkflowPanel
                  results={agentResults}
                  currentAgent="resume_parser"
                  status={activeSession.status}
                />
              </GlassCard>
            )}
          </div>
        )}
      </div>

      {/* Full-Screen Score Celebration Overlay */}
      {showScoreCelebration && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/70 backdrop-blur-md animate-fadeIn transition-all duration-500">
          <div className="scale-110 md:scale-125 transform transition-transform duration-500 flex flex-col items-center justify-center p-8 rounded-2xl bg-slate-950/80 border border-purple-500/25 shadow-[0_0_50px_rgba(139,92,246,0.3)]">
            <h3 className="text-sm font-black text-purple-300 uppercase tracking-widest mb-6 animate-pulse">
              {activeSession.ats_score_after != null ? "ATS Score Optimized!" : "Calculating Final ATS Score..."}
            </h3>
            <ATSScoreGauge score={Math.round(activeSession.ats_score_after ?? activeSession.ats_score_before ?? 0)} />
            <p className="text-[11px] text-slate-400 mt-4 max-w-xs text-center leading-normal">
              {activeSession.ats_score_after != null 
                ? `Compatibility improved from ${Math.round(activeSession.ats_score_before || 0)}% to ${Math.round(activeSession.ats_score_after)}%!`
                : "Scanning final resume metrics, technical keywords, and optimization layers..."
              }
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
