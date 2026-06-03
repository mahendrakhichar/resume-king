import React, { useState } from "react";
import { Sparkles, Loader2, AlertCircle } from "lucide-react";

interface JobDescriptionInputProps {
  onSubmit: (jd: string, company?: string, role?: string) => void;
  isLoading?: boolean;
}

export function JobDescriptionInput({ onSubmit, isLoading = false }: JobDescriptionInputProps) {
  const [jd, setJd] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (jd.trim().length < 50) {
      setValidationError("Job description must be at least 50 characters to analyze keyword fit.");
      return;
    }

    onSubmit(jd, company.trim() || undefined, role.trim() || undefined);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Target Company Name */}
        <div className="space-y-2">
          <label htmlFor="company-input" className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Target Company
          </label>
          <input
            type="text"
            id="company-input"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Google, Stripe"
            className="w-full px-4 py-3 rounded-xl bg-slate-900/60 border border-border/80 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-sm text-white placeholder-slate-500 transition-all duration-200"
          />
        </div>

        {/* Target Role Name */}
        <div className="space-y-2">
          <label htmlFor="role-input" className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Target Role
          </label>
          <input
            type="text"
            id="role-input"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. Senior Frontend Engineer"
            className="w-full px-4 py-3 rounded-xl bg-slate-900/60 border border-border/80 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-sm text-white placeholder-slate-500 transition-all duration-200"
          />
        </div>
      </div>

      {/* Raw Job Description Textarea */}
      <div className="space-y-2">
        <label htmlFor="jd-textarea" className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex justify-between">
          <span>Job Description Details</span>
          <span className="text-[10px] text-muted-foreground font-normal">Min 50 chars</span>
        </label>
        <textarea
          id="jd-textarea"
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste full job description listing requirements, skills and qualifications..."
          rows={8}
          className="w-full px-4 py-3 rounded-xl bg-slate-900/60 border border-border/80 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-sm text-white placeholder-slate-500 transition-all duration-200 resize-y"
        />
      </div>

      {validationError && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-red-950/20 border border-red-500/20 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Submit Trigger */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-3.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-semibold text-sm shadow-lg hover:shadow-purple-500/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-wait flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Initializing workflow agent graph...
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4" />
            Start AI Multi-Agent Workflow
          </>
        )}
      </button>
    </form>
  );
}
