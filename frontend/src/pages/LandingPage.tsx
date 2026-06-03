import { Link } from "react-router-dom";
import { SignedIn, SignedOut, SignInButton } from "../lib/auth";
import { Sparkles, Terminal, ShieldCheck, ArrowRight, Cpu } from "lucide-react";
import { GlassCard } from "../components/shared/GlassCard";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col relative overflow-hidden">
      {/* Background neon glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-900/10 rounded-full blur-[120px] animate-pulse-slow"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-emerald-900/10 rounded-full blur-[120px] animate-pulse-slow" style={{ animationDelay: "4s" }}></div>

      {/* Top Header/Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 glass bg-background/50 backdrop-blur-md">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-purple-600/20 p-1.5 rounded-xl border border-purple-500/20">
              <Sparkles className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-lg font-bold text-white uppercase tracking-wider">
              Resume<span className="text-gradient">Forge AI</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <SignedIn>
              <Link
                to="/dashboard"
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all duration-200"
              >
                Go to Dashboard
              </Link>
            </SignedIn>
            <SignedOut>
              <SignInButton mode="modal">
                <button className="px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-all duration-200">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-6 pt-24 pb-16 text-center max-w-4xl space-y-8 relative">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-semibold uppercase tracking-wider animate-bounce">
          <Cpu className="w-3.5 h-3.5" />
          LangGraph Multi-Agent Orchestration
        </div>

        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Tailor Your Resume and Beat the ATS with{" "}
          <span className="text-gradient">Agentic AI</span>
        </h1>

        <p className="text-base md:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Not just another GPT wrapper. Deploy a coordinated team of specialized AI career assistants
          that analyze job descriptions, recalculate compatibility, rewrite experience, and prepare mock interviews in parallel.
        </p>

        <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-4">
          <SignedIn>
            <Link
              to="/dashboard"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-sm shadow-lg hover:shadow-purple-500/20 transition-all duration-200 flex items-center justify-center gap-2 group"
            >
              Get Started
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-sm shadow-lg hover:shadow-purple-500/20 transition-all duration-200 flex items-center justify-center gap-2 group">
                Get Started
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </SignInButton>
          </SignedOut>
          <a
            href="#features"
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold text-sm border border-slate-800 transition-all duration-200"
          >
            Learn More
          </a>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="container mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-white text-center mb-12 uppercase tracking-widest">
          Specialized Agent Workflows
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <GlassCard className="space-y-4">
            <div className="bg-purple-500/10 p-3 rounded-xl border border-purple-500/20 w-fit text-purple-400">
              <Cpu className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">1. Job Description Dissector</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Dissects key requirements, hard skills, tools and target experience levels from job descriptions in structured JSON layouts.
            </p>
          </GlassCard>

          <GlassCard className="space-y-4">
            <div className="bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20 w-fit text-emerald-400">
              <Terminal className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">2. Experience Bullet Rewriter</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enhances work experiences bullet-by-bullet using Google's impact-oriented XYZ formula, naturally weaving in target skills.
            </p>
          </GlassCard>

          <GlassCard className="space-y-4">
            <div className="bg-blue-500/10 p-3 rounded-xl border border-blue-500/20 w-fit text-blue-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">3. Network & Prep Engine</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generates high-conversion LinkedIn connection templates alongside DSA, HR, and custom project-specific interview mock guides.
            </p>
          </GlassCard>
        </div>
      </section>

      {/* Bottom Footer */}
      <footer className="mt-auto border-t border-border/40 py-8 glass">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-center">
          <span className="text-xs text-slate-500">
            © 2026 ResumeForge AI. All rights reserved.
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-slate-600 tracking-wider">
              Built using LangGraph & Gemini
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
