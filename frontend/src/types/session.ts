export interface JDAnalysis {
  skills_required: string[];
  skills_preferred: string[];
  tools_and_technologies: string[];
  experience_level?: string;
  keywords: string[];
  responsibilities: string[];
  company_culture_hints?: string[];
}

export interface ATSSectionScore {
  section: string;
  score: number;
  max_score: number;
  feedback: string;
}

export interface ATSAnalysis {
  overall_score: number;
  keyword_match_rate: number;
  missing_keywords: string[];
  matched_keywords: string[];
  section_scores: ATSSectionScore[];
  suggestions: string[];
}

export type SessionStatus = "pending" | "running" | "review" | "completed" | "failed";

export interface SessionResponse {
  id: string;
  resume_id: string;
  job_description: string;
  target_company?: string;
  target_role?: string;
  status: SessionStatus;
  ats_score_before?: number;
  ats_score_after?: number;
  job_analysis?: JDAnalysis;
  parsed_resume?: any;
  created_at: string;
  updated_at: string;
}

export interface SessionListItem {
  id: string;
  target_company?: string;
  target_role?: string;
  status: SessionStatus;
  ats_score_before?: number;
  ats_score_after?: number;
  created_at: string;
}

export interface AgentResultResponse {
  id: string;
  agent_type: string;
  status: string;
  output_data?: unknown;
  reasoning?: string;
  error_message?: string;
  duration_ms?: number;
  created_at: string;
}

export interface HumanReviewDecision {
  review_id: string;
  action: "accepted" | "rejected" | "edited";
  final_content?: unknown;
}

// Real-time WebSocket message sent by the backend on each agent state change
export interface AgentStatusUpdate {
  session_id: string;
  agent_type: string;
  status: "running" | "success" | "failed";
  message?: string;
  duration_ms?: number;
}
