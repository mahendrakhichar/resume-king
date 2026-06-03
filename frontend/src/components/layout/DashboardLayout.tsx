import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { cn } from "../../lib/utils";

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768);
  const location = useLocation();

  useEffect(() => {
    // Automatically close sidebar on mobile when navigating
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} sidebarOpen={sidebarOpen} />
      <div className="flex flex-1 relative overflow-hidden">
        {/* Backdrop for mobile when sidebar is open */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            className="md:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity duration-300 top-16"
          />
        )}
        <Sidebar 
          className={cn(
            "fixed md:sticky top-16 z-40 h-[calc(100vh-4rem)] transition-all duration-300 ease-in-out bg-background/95 md:bg-transparent md:translate-x-0",
            sidebarOpen ? "translate-x-0 w-64 opacity-100" : "-translate-x-full md:-translate-x-full opacity-0 w-0 overflow-hidden p-0 border-0"
          )} 
        />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl mx-auto w-full transition-all duration-300">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
