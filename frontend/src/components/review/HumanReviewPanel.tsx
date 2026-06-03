import { useState, useMemo } from "react";
import { Sparkles, Loader2, Check, Award, AlertCircle, BookOpen, Layers } from "lucide-react";
import { ResumeDiffViewer } from "../resume/ResumeDiffViewer";
import { GlassCard } from "../shared/GlassCard";
import type { HumanReviewDecision } from "../../types/session";

interface SuggestionItem {
  id: string; // AgentResult ID
  agent_type: string; // resume_rewriter | project_optimizer
  output_data: unknown; // Suggested array
  reasoning?: string;
}

interface HumanReviewPanelProps {
  suggestions: SuggestionItem[];
  onSubmit: (decisions: HumanReviewDecision[]) => void;
  isSubmitting?: boolean;
  parsedResume?: any;
  jobAnalysis?: any;
  initialAtsData?: any;
}

// Internal typed shapes that come from the backend agent output
interface RewrittenBullet {
  original?: string;
  suggested?: string;
  reasoning?: string;
}

interface JobRewrite {
  company?: string;
  rewritten_bullets?: RewrittenBullet[];
}

interface ProjectRewrite {
  name?: string;
  technologies?: string[];
  rewritten_bullets?: RewrittenBullet[];
}

export function HumanReviewPanel({
  suggestions,
  onSubmit,
  isSubmitting = false,
  parsedResume,
  jobAnalysis,
  initialAtsData
}: HumanReviewPanelProps) {
  // Store decisions state: maps bullet index to accepted/rejected/edited
  // We use key format: "{suggestionId}_{bulletIdx}"
  const [decisions, setDecisions] = useState<Record<string, "accepted" | "rejected" | "edited">>({});

  const rewriterSuggestion = suggestions.find((s) => s.agent_type === "resume_rewriter");
  const projectSuggestion = suggestions.find((s) => s.agent_type === "project_optimizer");

  // Keep local states for edited content
  const [experienceData, setExperienceData] = useState<JobRewrite[]>(() => {
    const item = suggestions.find((s) => s.agent_type === "resume_rewriter");
    return item ? (JSON.parse(JSON.stringify(item.output_data)) as JobRewrite[]) : [];
  });

  const [projectData, setProjectData] = useState<ProjectRewrite[]>(() => {
    const item = suggestions.find((s) => s.agent_type === "project_optimizer");
    return item ? (JSON.parse(JSON.stringify(item.output_data)) as ProjectRewrite[]) : [];
  });

  const handleDecision = (
    suggestionId: string,
    idx: number,
    action: "accepted" | "rejected" | "edited"
  ) => {
    const key = `${suggestionId}_${idx}`;
    setDecisions((prev) => ({
      ...prev,
      [key]: action,
    }));
  };

  // Live edits handlers
  const handleExperienceBulletEdit = (jobIdx: number, bulletIdx: number, newValue: string) => {
    setExperienceData(prev => {
      const next = [...prev];
      if (next[jobIdx]?.rewritten_bullets?.[bulletIdx]) {
        next[jobIdx].rewritten_bullets[bulletIdx].suggested = newValue;
      }
      return next;
    });
    if (rewriterSuggestion) {
      handleDecision(rewriterSuggestion.id, jobIdx * 10 + bulletIdx, "edited");
    }
  };

  const handleProjectBulletEdit = (projIdx: number, bulletIdx: number, newValue: string) => {
    setProjectData(prev => {
      const next = [...prev];
      if (next[projIdx]?.rewritten_bullets?.[bulletIdx]) {
        next[projIdx].rewritten_bullets[bulletIdx].suggested = newValue;
      }
      return next;
    });
    if (projectSuggestion) {
      handleDecision(projectSuggestion.id, projIdx * 10 + bulletIdx, "edited");
    }
  };

  // --- Real-time ATS Sandbox Rescoring ---
  const targetKeywords = useMemo(() => {
    const matched = initialAtsData?.matched_keywords || [];
    const missing = initialAtsData?.missing_keywords || [];
    const seen = new Set<string>();
    const uniq: string[] = [];
    [...matched, ...missing].forEach(kw => {
      const normalized = kw.trim().toLowerCase();
      if (normalized && !seen.has(normalized)) {
        seen.add(normalized);
        uniq.push(kw);
      }
    });
    return uniq;
  }, [initialAtsData]);

  const liveAtsMetrics = useMemo(() => {
    if (targetKeywords.length === 0) return { score: 0, matched: [], missing: [] };

    let resumeText = "";
    if (parsedResume?.skills) {
      resumeText += " " + parsedResume.skills.join(" ");
    }
    if (parsedResume?.summary) {
      resumeText += " " + parsedResume.summary;
    }

    experienceData.forEach((job, jobIdx) => {
      resumeText += " " + (job.company || "");
      job.rewritten_bullets?.forEach((bullet, bulletIdx) => {
        const key = `${rewriterSuggestion?.id}_${jobIdx * 10 + bulletIdx}`;
        const decision = decisions[key] || "accepted"; // Default to accepted
        if (decision === "rejected") {
          resumeText += " " + (bullet.original || "");
        } else {
          resumeText += " " + (bullet.suggested || "");
        }
      });
    });

    projectData.forEach((proj, projIdx) => {
      resumeText += " " + (proj.name || "") + " " + (proj.technologies?.join(" ") || "");
      proj.rewritten_bullets?.forEach((bullet, bulletIdx) => {
        const key = `${projectSuggestion?.id}_${projIdx * 10 + bulletIdx}`;
        const decision = decisions[key] || "accepted"; // Default to accepted
        if (decision === "rejected") {
          resumeText += " " + (bullet.original || "");
        } else {
          resumeText += " " + (bullet.suggested || "");
        }
      });
    });

    const textLower = resumeText.toLowerCase();
    const matched: string[] = [];
    const missing: string[] = [];

    targetKeywords.forEach(kw => {
      const kwLower = kw.toLowerCase();
      // Look for keyword in full text (fuzzy word match)
      if (textLower.includes(kwLower)) {
        matched.push(kw);
      } else {
        missing.push(kw);
      }
    });

    // Score is matching rate
    const score = Math.round((matched.length / targetKeywords.length) * 100);
    return { score, matched, missing };
  }, [experienceData, projectData, targetKeywords, decisions, parsedResume, rewriterSuggestion, projectSuggestion]);

  const handleSubmit = () => {
    const compiledDecisions: HumanReviewDecision[] = [];

    // Experience: Send edited experienceData
    if (rewriterSuggestion) {
      compiledDecisions.push({
        review_id: rewriterSuggestion.id,
        action: "accepted", 
        final_content: experienceData, 
      });
    }

    // Projects: Send edited projectData
    if (projectSuggestion) {
      compiledDecisions.push({
        review_id: projectSuggestion.id,
        action: "accepted",
        final_content: projectData,
      });
    }

    onSubmit(compiledDecisions);
  };

  return (
    <div className="space-y-8">
      {/* Dynamic Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border/50 pb-6">
        <div className="space-y-1">
          <h3 className="text-xl font-bold text-white flex items-center gap-1.5">
            <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
            Human-in-the-Loop Validation Suite &amp; Live Sandbox
          </h3>
          <p className="text-xs text-slate-400">
            Edit optimized experience bullets, technologies, and projects. Watch your ATS fit score update live!
          </p>
        </div>
      </div>

      {/* Live Rescoring Sidebar Widget (Data-Dense Dashboard Block) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-8">
          {/* Experience rewrites sandbox */}
          {rewriterSuggestion && rewriterSuggestion.output_data && (
            <div className="space-y-6">
              {experienceData.map((job, jobIdx) => {
                if (!job.rewritten_bullets || job.rewritten_bullets.length === 0) return null;

                const diffBullets = job.rewritten_bullets.map((b) => ({
                  original: b.original ?? "",
                  suggested: b.suggested ?? "",
                  reasoning: b.reasoning ?? "",
                }));

                return (
                  <ResumeDiffViewer
                    key={jobIdx}
                    sectionName={`Professional Experience${job.company ? ` at ${job.company}` : ""}`}
                    bullets={diffBullets}
                    onBulletEdit={(bulletIdx, newVal) => handleExperienceBulletEdit(jobIdx, bulletIdx, newVal)}
                    onDecision={(bulletIdx, action) =>
                      handleDecision(rewriterSuggestion.id, jobIdx * 10 + bulletIdx, action)
                    }
                    decisions={Object.entries(decisions)
                      .filter(([key]) => key.startsWith(`${rewriterSuggestion.id}_`))
                      .reduce((acc, [key, val]) => {
                        const idx = parseInt(key.split("_")[1]);
                        if (Math.floor(idx / 10) === jobIdx) {
                          acc[idx % 10] = val;
                        }
                        return acc;
                      }, {} as Record<number, "accepted" | "rejected" | "edited">)}
                  />
                );
              })}
            </div>
          )}

          {/* Project optimizations sandbox */}
          {projectSuggestion && projectSuggestion.output_data && (
            <div className="space-y-6">
              {projectData.map((proj, projIdx) => {
                if (!proj.rewritten_bullets || proj.rewritten_bullets.length === 0) return null;

                const diffBullets = proj.rewritten_bullets.map((b) => ({
                  original: b.original ?? "",
                  suggested: b.suggested ?? "",
                  reasoning: b.reasoning ?? "",
                }));

                return (
                  <ResumeDiffViewer
                    key={projIdx}
                    sectionName={`Project${proj.name ? `: ${proj.name}` : ""}`}
                    bullets={diffBullets}
                    onBulletEdit={(bulletIdx, newVal) => handleProjectBulletEdit(projIdx, bulletIdx, newVal)}
                    onDecision={(bulletIdx, action) =>
                      handleDecision(projectSuggestion.id, projIdx * 10 + bulletIdx, action)
                    }
                    decisions={Object.entries(decisions)
                      .filter(([key]) => key.startsWith(`${projectSuggestion.id}_`))
                      .reduce((acc, [key, val]) => {
                        const idx = parseInt(key.split("_")[1]);
                        if (Math.floor(idx / 10) === projIdx) {
                          acc[idx % 10] = val;
                        }
                        return acc;
                      }, {} as Record<number, "accepted" | "rejected" | "edited">)}
                  />
                );
              })}
            </div>
          )}

          {/* Fallback: no suggestions */}
          {!rewriterSuggestion && !projectSuggestion && (
            <div className="text-center text-sm text-muted-foreground py-8">
              No AI suggestions available to review yet.
            </div>
          )}
        </div>

        {/* Live Cockpit Widget - Densely Packed */}
        <div className="space-y-6 self-start">
          <GlassCard className="p-5 border-purple-500/30 space-y-6">
            <div className="flex items-center gap-1.5 border-b border-border pb-3">
              <Award className="w-4 h-4 text-purple-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Live Sandbox Scoring
              </h4>
            </div>

            <div className="flex flex-col items-center py-4 bg-background/30 rounded-xl border border-border/50">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">
                Real-Time Fit Score
              </span>
              <div className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
                {liveAtsMetrics.score}%
              </div>
              <span className="text-[10px] text-emerald-400 font-semibold mt-1 flex items-center gap-0.5">
                Baseline Check: {initialAtsData?.overall_score || 50}%
              </span>
            </div>

            {/* Keyword Tracking lists */}
            <div className="space-y-4">
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  Live Matched Keywords ({liveAtsMetrics.matched.length})
                </span>
                <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto p-2 bg-background/30 rounded-lg border border-border/40 select-none">
                  {liveAtsMetrics.matched.length > 0 ? (
                    liveAtsMetrics.matched.map((kw, idx) => (
                      <span
                        key={idx}
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      >
                        {kw}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] text-slate-500 italic">Type matching skills to unlock!</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest flex items-center gap-1">
                  Missing Keywords ({liveAtsMetrics.missing.length})
                </span>
                <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto p-2 bg-background/30 rounded-lg border border-border/40 select-none">
                  {liveAtsMetrics.missing.length > 0 ? (
                    liveAtsMetrics.missing.map((kw, idx) => (
                      <span
                        key={idx}
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20"
                      >
                        {kw}
                      </span>
                    ))
                  ) : (
                    <span className="text-[10px] text-emerald-400 font-semibold italic">Perfect! All matched!</span>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-border/40 space-y-2 text-[10px] text-slate-400 leading-normal">
              <div className="flex items-start gap-1">
                <BookOpen className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                <span>Add missing key competencies inside the AI text areas to organically lift compatibility ratings.</span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Review completion trigger */}
      <button
        onClick={handleSubmit}
        disabled={isSubmitting}
        className="w-full py-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-lg hover:shadow-emerald-500/20 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Compiling final PDF templates...
          </>
        ) : (
          <>
            <Check className="w-5 h-5" />
            Accept &amp; Finalize Tailored Resume
          </>
        )}
      </button>
    </div>
  );
}
