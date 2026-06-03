import { Link } from "react-router-dom";
import { SignedIn, SignedOut, SignInButton, UserButton } from "../../lib/auth";
import { Sparkles, Menu, X } from "lucide-react";

interface NavbarProps {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export function Navbar({ onToggleSidebar, sidebarOpen }: NavbarProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border glass bg-background/80">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/40 border border-transparent hover:border-border/40 transition-all duration-200"
              aria-label="Toggle Sidebar"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          )}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="bg-purple-600/20 p-2 rounded-xl border border-purple-500/30 group-hover:scale-105 transition-transform duration-200">
              <Sparkles className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white group-hover:text-purple-400 transition-colors duration-200">
              Resume<span className="text-gradient">Forge AI</span>
            </span>
          </Link>
        </div>

        <nav className="flex items-center gap-6">
          <SignedIn>
            <Link
              to="/dashboard"
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors duration-200"
            >
              Dashboard
            </Link>
          </SignedIn>

          <div className="flex items-center gap-4">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="px-4 py-2 text-sm font-semibold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-lg hover:shadow-purple-500/20 transition-all duration-200">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <UserButton afterSignOutUrl="/" appearance={{
                elements: {
                  avatarBox: "w-9 h-9 border border-purple-500/30"
                }
              }} />
            </SignedIn>
          </div>
        </nav>
      </div>
    </header>
  );
}
