import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, FileText, ArrowRight } from "lucide-react";
import { useResumeStore } from "../stores/useResumeStore";
import { useSessionStore } from "../stores/useSessionStore";
import { GlassCard } from "../components/shared/GlassCard";
import { ResumeUploader } from "../components/resume/ResumeUploader";
import { JobDescriptionInput } from "../components/job/JobDescriptionInput";

export default function NewSessionPage() {
  const navigate = useNavigate();
  const { resumes, fetchResumes } = useResumeStore();
  const createSession = useSessionStore((state) => state.createSession);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [sessionIsLoading, setSessionIsLoading] = useState(false);
  const [step, setStep] = useState<"resume" | "job">("resume");

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  const handleUploadSuccess = (resumeId: string) => {
    setSelectedResumeId(resumeId);
    setStep("job");
  };

  const handleSelectExisting = (id: string) => {
    setSelectedResumeId(id);
    setStep("job");
  };

  const handleJobSubmit = async (jd: string, company?: string, role?: string) => {
    if (!selectedResumeId) return;

    setSessionIsLoading(true);
    try {
      const session = await createSession(selectedResumeId, jd, company, role);
      setSessionIsLoading(false);
      navigate(`/dashboard/session/${session.id}`);
    } catch (e) {
      setSessionIsLoading(false);
      console.error(e);
    }
  };

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Step Indicators */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Create Tailoring Session</h2>
          <p className="text-xs text-muted-foreground">
            Configure resume options and target job details.
          </p>
        </div>
        
        {/* Visual Dots */}
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border transition-all duration-300 ${
              step === "resume"
                ? "bg-purple-500/10 text-purple-300 border-purple-500/30"
                : "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
            }`}
          >
            {step === "resume" ? "Step 1: Resume" : "Step 2: Job Description"}
          </span>
        </div>
      </div>

      {step === "resume" ? (
        <div className="space-y-6">
          <GlassCard className="space-y-6">
            <div className="space-y-1">
              <h3 className="text-md font-bold text-white flex items-center gap-1.5">
                <FileText className="w-5 h-5 text-purple-400" />
                Upload New Resume
              </h3>
              <p className="text-xs text-slate-400">
                Let Gemini extract your structured experiences, skills, and certifications.
              </p>
            </div>
            <ResumeUploader onUploadSuccess={handleUploadSuccess} />
          </GlassCard>

          {resumes.length > 0 && (
            <GlassCard className="space-y-4">
              <h3 className="text-md font-bold text-white">Or Select Existing Resume</h3>
              <div className="grid grid-cols-1 gap-3">
                {resumes.map((resume) => (
                  <div
                    key={resume.id}
                    onClick={() => handleSelectExisting(resume.id)}
                    className="p-4 rounded-xl border border-border/60 bg-slate-900/30 hover:border-purple-500/50 hover:bg-slate-900/60 cursor-pointer flex items-center justify-between transition-all duration-200"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-slate-400" />
                      <div className="text-left">
                        <h4 className="text-sm font-bold text-white truncate max-w-xs">
                          {resume.original_filename}
                        </h4>
                        <p className="text-[10px] text-muted-foreground uppercase">
                          Version {resume.version} • {resume.file_type}
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500" />
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      ) : (
        <GlassCard className="space-y-6">
          <div className="space-y-1">
            <h3 className="text-md font-bold text-white flex items-center gap-1.5">
              <Sparkles className="w-5 h-5 text-purple-400" />
              Target Job Specification
            </h3>
            <p className="text-xs text-slate-400">
              Provide job description details to guide the AI multi-agent rewrite process.
            </p>
          </div>
          
          <JobDescriptionInput onSubmit={handleJobSubmit} isLoading={sessionIsLoading} />

          <button
            onClick={() => setStep("resume")}
            className="w-full py-2.5 rounded-xl border border-border hover:bg-slate-900 text-slate-300 font-semibold text-xs transition-colors duration-200"
          >
            Go Back
          </button>
        </GlassCard>
      )}
    </div>
  );
}
