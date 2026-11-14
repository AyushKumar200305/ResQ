import React, { useState } from "react";
import { HelpCircle, Info } from "lucide-react";

export const DAA_GLOSSARY: Record<
  string,
  { term: string; simple: string; technical?: string }
> = {
  "maximum-flow": {
    term: "Maximum Flow",
    simple:
      "The highest number of evacuees that can safely reach emergency shelters per hour through the network.",
    technical:
      "The value |f*| maximizing total outflow from super-source S* to super-sink T* subject to capacity and conservation constraints.",
  },
  "residual-capacity": {
    term: "Residual Capacity",
    simple:
      "The remaining unused capacity of a road after sending evacuation traffic. When residual capacity drops to zero, the road is full (saturated).",
    technical:
      "cf(u, v) = c(u, v) - f(u, v) for forward edges, and cf(v, u) = f(u, v) for reverse edges.",
  },
  "minimum-cut": {
    term: "Minimum Cut",
    simple:
      "The critical set of bottleneck roads and shelter limits separating hazard areas from safe shelters with the smallest total capacity.",
    technical:
      "A partition (S, T) of vertices with S* in S and T* in T minimizing c(S, T). By the Max-Flow Min-Cut Theorem, c(S, T) = |f*|.",
  },
  bottleneck: {
    term: "Bottleneck",
    simple:
      "A road or shelter that restricts the entire evacuation. Widening non-bottleneck roads will not help until bottlenecks are upgraded.",
    technical:
      "An edge (u, v) in the residual graph's minimum cut where cf(u, v) = 0 and u is reachable from S* while v is not.",
  },
  "reverse-edge": {
    term: "Reverse Residual Edge",
    simple:
      "A mechanism that allows the algorithm to redirect traffic if a better overall evacuation route is discovered later.",
    technical:
      "Enables Dinic to push flow backwards, effectively cancelling earlier suboptimal assignments without backtracking.",
  },
  "level-graph": {
    term: "BFS Level Graph",
    simple:
      "A layered map organizing junctions by their distance from hazard zones, ensuring evacuees only move forward via shortest paths.",
    technical:
      "A subgraph containing only edges (u, v) where level[v] = level[u] + 1 in the residual graph BFS tree.",
  },
  "blocking-flow": {
    term: "Blocking Flow",
    simple:
      "A state where every path from hazard areas to shelters is blocked by at least one completely saturated road.",
    technical:
      "A flow in the level graph such that no directed S*-T* path with positive residual capacity remains.",
  },
};

interface TermTooltipProps {
  termKey: keyof typeof DAA_GLOSSARY;
  children?: React.ReactNode;
  showIcon?: boolean;
}

export const TermTooltip: React.FC<TermTooltipProps> = ({
  termKey,
  children,
  showIcon = true,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const data = DAA_GLOSSARY[termKey] || {
    term: termKey,
    simple: "Algorithmic term used in evacuation optimization.",
  };

  return (
    <span
      className="relative inline-flex items-center gap-1 group cursor-help"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onClick={() => setIsVisible(!isVisible)}
    >
      <span className="border-b border-dotted border-slate-400 group-hover:border-sky-400 transition-colors">
        {children || data.term}
      </span>
      {showIcon && (
        <HelpCircle className="w-3 h-3 text-slate-500 group-hover:text-sky-400 transition-colors shrink-0" />
      )}

      {isVisible && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3.5 bg-white border border-slate-200 rounded-xl shadow-card text-left z-50 pointer-events-none animate-in fade-in duration-150">
          <div className="flex items-center gap-1.5 text-xs font-bold text-blue-700 mb-1">
            <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span>{data.term}</span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            {data.simple}
          </p>
          {data.technical && (
            <div className="mt-1.5 pt-1.5 border-t border-slate-100 text-[10px] text-slate-500 font-mono">
              DAA: {data.technical}
            </div>
          )}
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-slate-200" />
        </div>
      )}
    </span>
  );
};
