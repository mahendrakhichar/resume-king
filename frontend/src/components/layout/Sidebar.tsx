import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Sparkles, History } from "lucide-react";
import { cn } from "../../lib/utils";

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const location = useLocation();

  const links = [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/dashboard/new", label: "Tailor Application", icon: Sparkles },
    { to: "/dashboard/history", label: "History & Sessions", icon: History },
  ];

  return (
    <aside className={cn("w-64 border-r border-border glass h-[calc(100vh-4rem)] p-6 space-y-6 flex flex-col", className)}>
      <div className="space-y-2">
        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest px-3">
          Menu
        </span>
        <nav className="space-y-1 flex-1">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.to;

            return (
              <Link
                key={link.to}
                to={link.to}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-purple-600/15 text-purple-300 border border-purple-500/25 shadow-[0_0_10px_rgba(139,92,246,0.1)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent"
                )}
              >
                <Icon className={cn("w-4.5 h-4.5", isActive ? "text-purple-400" : "text-slate-400")} />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="pt-6 border-t border-border/40 mt-auto">
        <div className="p-4 rounded-xl bg-purple-950/10 border border-purple-500/15 space-y-2">
          <span className="text-xs font-semibold text-purple-300 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            Free Tier Plan
          </span>
          <p className="text-[10px] text-muted-foreground">
            Gemini & Groq free limits applied. Support 1,500 daily parsing requests.
          </p>
        </div>
      </div>
    </aside>
  );
}
