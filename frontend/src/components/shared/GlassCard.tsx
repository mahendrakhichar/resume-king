import React from "react";
import { cn } from "../../lib/utils";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  accented?: boolean;
}

export function GlassCard({ children, className, accented = false, ...props }: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl p-6 transition-all duration-300",
        accented ? "glass-accent shadow-[0_0_20px_rgba(139,92,246,0.15)]" : "glass shadow-xl",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
