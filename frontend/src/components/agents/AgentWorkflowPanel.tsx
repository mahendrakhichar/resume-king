import { motion } from "framer-motion";
import { CheckCircle2, Loader2, PlayCircle, AlertCircle, Sparkles } from "lucide-react";
import type { AgentResultResponse } from "../../types/session";

interface AgentWorkflowPanelProps {
  results: AgentResultResponse[];
  currentAgent?: string;
  status: string; // pending, running, completed, failed
}

interface WorkflowStep {
  id: string;
  label: string;
  description: string;
  agentType: string;
}

const STEPS: WorkflowStep[] = [
  { id: "parser", label: "Resume Parsing", description: "Structured JSON extraction from PDF/DOCX via Gemini", agentType: "resume_parser" },
  { id: "analyzer", label: "Job Description Analyzer", description: "Dissects target skills, tech stack and roles from JD", agentType: "jd_analyzer" },
  { id: "matcher", label: "ATS Match Checker", description: "Calculates fit index and evaluates missing buzzwords", agentType: "ats_matcher" },
  { id: "rewriter", label: "Experience Optimizations", description: "Rewrites bullets applying the Google XYZ formula", agentType: "resume_rewriter" },
  { id: "project", label: "Project Enhancements", description: "Polishes projects with system architectural phrasing", agentType: "project_optimizer" },
  { id: "recruiter", label: "Recruiter Message Suite", description: "Generates custom LinkedIn notes and referral drafts", agentType: "recruiter_agent" },
  { id: "interview", label: "Mock Interview Vault", description: "Prepares tailored DSA, HR and project audit questions", agentType: "interview_agent" },
  { id: "validator", label: "Consistency Audit", description: "Guarantees no hallucinations or styling inconsistencies", agentType: "validator" }
];

export function AgentWorkflowPanel({ results, currentAgent, status }: AgentWorkflowPanelProps) {
  // Helpers to fetch state status of a specific step
  const getStepStatus = (agentType: string) => {
    const result = results.find((r) => r.agent_type === agentType);
    if (result) return result.status; // success, failed, running
    
    if (status === "running" && currentAgent === agentType) return "running";
    return "pending";
  };

  const getStatusIcon = (stepStatus: string) => {
    switch (stepStatus) {
      case "success":
        return <CheckCircle2 className="w-6 h-6 text-emerald-400" />;
      case "running":
        return <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />;
      case "failed":
        return <AlertCircle className="w-6 h-6 text-red-400" />;
      default:
        return <PlayCircle className="w-6 h-6 text-muted-foreground opacity-55" />;
    }
  };

  const getStepClass = (stepStatus: string) => {
    switch (stepStatus) {
      case "success":
        return "border-emerald-500/20 bg-emerald-500/5";
      case "running":
        return "border-purple-500/50 bg-purple-500/10 shadow-[0_0_15px_rgba(168,85,247,0.2)] animate-pulse";
      case "failed":
        return "border-red-500/30 bg-red-500/5";
      default:
        return "border-border/30 bg-muted/5 opacity-60";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400 animate-bounce" />
          <h3 className="text-lg font-bold text-white">Multi-Agent Workflow Tracker</h3>
        </div>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30 uppercase">
          {status}
        </span>
      </div>

      <div className="relative pl-6 space-y-4 border-l border-border/50 ml-3">
        {STEPS.map((step, idx) => {
          const stepStatus = getStepStatus(step.agentType);
          const activeResult = results.find((r) => r.agent_type === step.agentType);

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`relative flex flex-col p-4 rounded-xl border transition-all duration-300 ${getStepClass(
                stepStatus
              )}`}
            >
              {/* Timeline marker node dot */}
              <div className="absolute -left-[37px] top-4 bg-background p-1 rounded-full border border-border">
                {getStatusIcon(stepStatus)}
              </div>

              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm text-white">{step.label}</span>
                {activeResult?.duration_ms && (
                  <span className="text-[10px] text-muted-foreground">
                    {activeResult.duration_ms}ms
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
              
              {/* Show Reasoning logs if agent finished successfully */}
              {stepStatus === "success" && activeResult?.reasoning && (
                <div className="mt-2 text-[11px] text-emerald-400/80 bg-emerald-950/20 p-2 rounded-lg border border-emerald-500/10">
                  <strong>AI Logic:</strong> {activeResult.reasoning}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
