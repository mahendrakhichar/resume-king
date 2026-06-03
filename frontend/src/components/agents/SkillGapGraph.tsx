import { useState, useMemo } from "react";
import { HelpCircle, CheckCircle2, AlertTriangle, Sparkles, BookOpen } from "lucide-react";
import { GlassCard } from "../shared/GlassCard";

interface SkillGapGraphProps {
  matchedKeywords?: string[];
  missingKeywords?: string[];
}

interface Node {
  id: string;
  label: string;
  type: "root" | "category" | "skill";
  status?: "matched" | "missing";
  x: number;
  y: number;
  category?: string;
}

interface Edge {
  source: string;
  target: string;
}

export function SkillGapGraph({
  matchedKeywords = [],
  missingKeywords = []
}: SkillGapGraphProps) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Compile nodes and edges for our custom SVG layout
  const graphData = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // 1. Center Root Node
    const rootId = "root";
    nodes.push({ id: rootId, label: "Job Alignment", type: "root", x: 250, y: 200 });

    // 2. Category Nodes
    const categories = [
      { id: "cat_match", label: "Core Matches", x: 120, y: 120 },
      { id: "cat_gaps", label: "Priority Gaps", x: 380, y: 280 },
    ];

    categories.forEach(cat => {
      nodes.push({ id: cat.id, label: cat.label, type: "category", x: cat.x, y: cat.y });
      edges.push({ source: rootId, target: cat.id });
    });

    // 3. Skill Nodes
    // Take up to 6 matched and 6 missing keywords to avoid over-crowding the SVG canvas
    const maxSkills = 5;
    const displayMatches = matchedKeywords.slice(0, maxSkills);
    const displayGaps = missingKeywords.slice(0, maxSkills);

    // Radiate matched keywords around the Core Matches category
    displayMatches.forEach((skill, idx) => {
      const skillId = `match_${idx}`;
      const angle = (idx / displayMatches.length) * 2 * Math.PI - Math.PI / 4;
      const radius = 70;
      const x = Math.round(categories[0].x + radius * Math.cos(angle));
      const y = Math.round(categories[0].y + radius * Math.sin(angle));

      nodes.push({
        id: skillId,
        label: skill,
        type: "skill",
        status: "matched",
        x,
        y,
        category: "Core Matches"
      });
      edges.push({ source: categories[0].id, target: skillId });
    });

    // Radiate missing keywords around the Priority Gaps category
    displayGaps.forEach((skill, idx) => {
      const skillId = `gap_${idx}`;
      const angle = (idx / displayGaps.length) * 2 * Math.PI + Math.PI / 2;
      const radius = 70;
      const x = Math.round(categories[1].x + radius * Math.cos(angle));
      const y = Math.round(categories[1].y + radius * Math.sin(angle));

      nodes.push({
        id: skillId,
        label: skill,
        type: "skill",
        status: "missing",
        x,
        y,
        category: "Priority Gaps"
      });
      edges.push({ source: categories[1].id, target: skillId });
    });

    return { nodes, edges };
  }, [matchedKeywords, missingKeywords]);

  // Handle clicking a node
  const handleNodeClick = (node: Node) => {
    if (node.type === "skill") {
      setSelectedNode(node);
    } else {
      setSelectedNode(null);
    }
  };

  // Generate learning tip recommendation
  const studyRecommendation = useMemo(() => {
    if (!selectedNode) return null;
    const isGap = selectedNode.status === "missing";
    
    if (isGap) {
      return {
        concept: `Mastering ${selectedNode.label} System Design`,
        action: `Integrate ${selectedNode.label} into your projects. Research standard connection-pooling and failover clustering models.`,
        challenge: `Build a 10-line setup of ${selectedNode.label} utilizing Docker to test local execution latencies.`
      };
    } else {
      return {
        concept: `${selectedNode.label} Advanced Engineering`,
        action: `You already match this requirement! Be sure to emphasize performance scaling and multi-threading models on interviews.`,
        challenge: `Prepare to explain how you structured ${selectedNode.label} state trees or architecture at Infosys.`
      };
    }
  }, [selectedNode]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* Network Graph Frame - Densely Packed */}
      <GlassCard className="p-4 lg:col-span-3 flex flex-col items-center bg-background/25 border-border/40 min-h-[400px]">
        <div className="w-full flex items-center justify-between border-b border-border/40 pb-3 mb-4">
          <div className="space-y-0.5">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              Alignment Knowledge Graph
            </h4>
            <p className="text-[10px] text-slate-400">
              Interactive 2D topological mapping of resume competencies and role targets. Click skill nodes!
            </p>
          </div>
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center gap-1 animate-pulse">
            <Sparkles className="w-2.5 h-2.5" />
            Topological
          </span>
        </div>

        {/* SVG Network Canvas */}
        <div className="relative w-full overflow-x-auto flex justify-center py-2 select-none">
          <svg
            width="500"
            height="400"
            className="overflow-visible"
            viewBox="0 0 500 400"
          >
            {/* Draw Edges */}
            {graphData.edges.map((edge, idx) => {
              const src = graphData.nodes.find(n => n.id === edge.source);
              const tgt = graphData.nodes.find(n => n.id === edge.target);
              if (!src || !tgt) return null;

              const isGap = tgt.status === "missing";
              return (
                <line
                  key={idx}
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={isGap ? "rgba(239, 68, 68, 0.15)" : tgt.type === "root" ? "rgba(168, 85, 247, 0.2)" : "rgba(16, 185, 129, 0.15)"}
                  strokeWidth={tgt.type === "category" ? "2" : "1.2"}
                  strokeDasharray={isGap ? "3,3" : "none"}
                />
              );
            })}

            {/* Draw Nodes */}
            {graphData.nodes.map(node => {
              const isSelected = selectedNode?.id === node.id;
              
              if (node.type === "root") {
                return (
                  <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                    <circle r="22" className="fill-purple-950 stroke-purple-500" strokeWidth="2" />
                    <text
                      textAnchor="middle"
                      dy="4"
                      className="text-[9px] font-bold fill-white uppercase tracking-wider font-sans pointer-events-none"
                    >
                      Target
                    </text>
                  </g>
                );
              }

              if (node.type === "category") {
                const isGapCat = node.id === "cat_gaps";
                return (
                  <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                    <rect
                      x="-45"
                      y="-12"
                      width="90"
                      height="24"
                      rx="6"
                      className={`${
                        isGapCat 
                          ? "fill-red-950/60 stroke-red-500/40" 
                          : "fill-emerald-950/60 stroke-emerald-500/40"
                      }`}
                      strokeWidth="1.5"
                    />
                    <text
                      textAnchor="middle"
                      dy="4"
                      className={`text-[9px] font-bold font-sans pointer-events-none uppercase ${
                        isGapCat ? "fill-red-400" : "fill-emerald-400"
                      }`}
                    >
                      {node.label}
                    </text>
                  </g>
                );
              }

              // Skill Node
              const isGap = node.status === "missing";
              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  className="cursor-pointer group"
                  onClick={() => handleNodeClick(node)}
                >
                  <circle
                    r="8"
                    className={`transition-all duration-300 ${
                      isGap
                        ? isSelected 
                          ? "fill-red-950 stroke-red-400 stroke-[3px]" 
                          : "fill-red-900/40 stroke-red-500/60 hover:stroke-red-400 hover:fill-red-950"
                        : isSelected 
                        ? "fill-emerald-950 stroke-emerald-400 stroke-[3px]" 
                        : "fill-emerald-900/40 stroke-emerald-500/60 hover:stroke-emerald-400 hover:fill-emerald-950"
                    }`}
                    strokeWidth="1.5"
                  />
                  <text
                    textAnchor="middle"
                    y="18"
                    className={`text-[8.5px] font-semibold font-sans transition-all pointer-events-none select-none ${
                      isGap 
                        ? "fill-red-300/80 group-hover:fill-red-300 font-bold" 
                        : "fill-emerald-300/80 group-hover:fill-emerald-300 font-bold"
                    } ${isSelected ? "underline text-white font-extrabold" : ""}`}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </GlassCard>

      {/* Dynamic Detail Card / Recommendation Sidebar */}
      <GlassCard className="p-4 lg:col-span-2 bg-background/25 border-border/40 flex flex-col justify-between min-h-[400px]">
        {selectedNode && studyRecommendation ? (
          <div className="space-y-5 h-full flex flex-col justify-between">
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-center gap-2 pb-3 border-b border-border/40">
                {selectedNode.status === "missing" ? (
                  <AlertTriangle className="w-5 h-5 text-red-400 animate-bounce" />
                ) : (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                )}
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider font-bold text-slate-400">
                    {selectedNode.category} Node
                  </span>
                  <h4 className="text-sm font-extrabold text-white leading-none">
                    {selectedNode.label}
                  </h4>
                </div>
              </div>

              {/* Action Plan */}
              <div className="space-y-3.5 mt-2">
                <div className="space-y-1">
                  <span className="text-[9px] font-bold uppercase tracking-widest text-purple-400 flex items-center gap-1">
                    <BookOpen className="w-3.5 h-3.5" />
                    Interactive Study Blueprint
                  </span>
                  <p className="text-[11px] font-semibold text-slate-200 leading-relaxed bg-background/40 p-2.5 rounded-lg border border-border/50">
                    {studyRecommendation.concept}
                  </p>
                </div>

                <div className="space-y-1">
                  <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">
                    Hiring Manager Expectation
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed pl-1.5 border-l-2 border-slate-500">
                    {studyRecommendation.action}
                  </p>
                </div>
              </div>
            </div>

            {/* AI Coding Prompt Challenge */}
            <div className="bg-purple-950/15 p-3.5 rounded-xl border border-purple-500/20 space-y-2 mt-auto">
              <span className="text-[9px] font-extrabold text-purple-400 uppercase tracking-widest flex items-center gap-1 animate-pulse">
                <Sparkles className="w-3 h-3" />
                AI Sandbox Mini-Challenge
              </span>
              <p className="text-[10px] text-purple-200 leading-relaxed font-mono">
                {studyRecommendation.challenge}
              </p>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 my-auto">
            <div className="bg-purple-500/10 p-3 rounded-full border border-purple-500/20 text-purple-400">
              <HelpCircle className="w-8 h-8" />
            </div>
            <div className="space-y-1 max-w-[200px]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Explore Skills
              </h4>
              <p className="text-[10px] text-slate-400 leading-normal">
                Click any of the satellite skill nodes in the graph to retrieve an instant study blueprint and coding challenge gap filler.
              </p>
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
