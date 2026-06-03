import { useEffect, useState } from "react";

interface ATSScoreGaugeProps {
  score: number; // 0 to 100
  size?: number;
  strokeWidth?: number;
}

export function ATSScoreGauge({ score, size = 160, strokeWidth = 12 }: ATSScoreGaugeProps) {
  const [currentScore, setCurrentScore] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  
  // Smooth initial animation incrementing up to target score
  useEffect(() => {
    const duration = 1200; // ms
    const steps = 60;
    const increment = score / steps;
    let step = 0;
    
    const timer = setInterval(() => {
      step++;
      setCurrentScore((prev) => {
        const next = prev + increment;
        return next >= score ? score : next;
      });
      if (step >= steps) {
        clearInterval(timer);
        setCurrentScore(score);
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [score]);

  const offset = circumference - (currentScore / 100) * circumference;

  // Determine color accents based on fit score
  const getGradientColors = () => {
    if (score < 50) return { from: "#ef4444", to: "#f97316" }; // Red to Orange
    if (score < 75) return { from: "#f97316", to: "#eab308" }; // Orange to Yellow
    return { from: "#10b981", to: "#34d399" };             // Emerald to Light Green
  };

  const colors = getGradientColors();

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full transform -rotate-90">
          <defs>
            <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={colors.from} />
              <stop offset="100%" stopColor={colors.to} />
            </linearGradient>
          </defs>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="stroke-muted"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Animated active score path */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="url(#scoreGradient)"
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.1s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-4xl font-extrabold tracking-tight text-white">
            {Math.round(currentScore)}
          </span>
          <span className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">
            ATS Score
          </span>
        </div>
      </div>
    </div>
  );
}
