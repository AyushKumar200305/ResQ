import React, { useState } from "react";
import { ChevronRight, FileDown, Home, RefreshCw } from "lucide-react";
import { api } from "../../api/client";
import { useApp } from "../../context/AppContext";

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  landing: {
    title: "Mission Introduction",
    subtitle: "Emergency disaster evacuation optimization platform",
  },
  login: {
    title: "Incident Command Access",
    subtitle: "Authentication & operational role assignment",
  },
  overview: {
    title: "Situation Overview",
    subtitle: "Critical zones, immediate actions, route warnings, and resource status",
  },
  priorities: {
    title: "Evacuation Priorities",
    subtitle: "Ranked triage assessment with transparent risk justification",
  },
  routes: {
    title: "Routes & Shelters",
    subtitle: "Interactive corridor map, primary & alternative paths, and hazard warnings",
  },
  resources: {
    title: "Camp Resources",
    subtitle: "Shelter intake, humanitarian supply demand, and fair-share allocation",
  },
  builder: {
    title: "Network Builder",
    subtitle: "Interactive graph topology builder, capacities & JSON import/export",
  },
  simulation: {
    title: "Live Simulation",
    subtitle: "Step-by-step augmenting path playback & multi-hour wave clearance",
  },
  flow: {
    title: "Flow Analysis",
    subtitle: "Road corridor utilization, residual capacities, and flow decomposition",
  },
  bottlenecks: {
    title: "Bottleneck Analysis",
    subtitle: "Max-Flow Min-Cut theorem verification & critical chokepoints",
  },
  scenarios: {
    title: "Scenario Lab",
    subtitle: "What-If disaster failure injection across independent network copies",
  },
  compare: {
    title: "Algorithm Comparison",
    subtitle: "Dinic O(V²E) optimal flow vs. greedy heuristics (Shortest-Hop, Widest-Path, DFS)",
  },
  dijkstra: {
    title: "Shortest Path (Dijkstra)",
    subtitle: "Point-to-point non-negative distance routing & alternative detours",
  },
  algorithms: {
    title: "Algorithm & Computational Analysis",
    subtitle: "Consolidated DAA analysis suite: Dinic, Greedy, Dijkstra, Min-Cut, Scenarios",
  },
  reports: {
    title: "Reports & Situation Briefings",
    subtitle: "Publication-quality PDF, JSON, and CSV audits with formal DAA proofs",
  },
  about: {
    title: "About ResQ Platform",
    subtitle: "Asymptotic complexity proofs, team details, and academic references",
  },
};

export const Breadcrumb: React.FC = () => {
  const { activePage, setActivePage, network, refreshNetwork, isLoading, addNotification } = useApp();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadPdf = async () => {
    setIsDownloading(true);
    try {
      await api.downloadFile("/api/reports/pdf", `ResQ-Situation-Report-${network?.network_id || "Live"}.pdf`);
      addNotification("success", "Official Situation PDF Report generated and downloaded successfully.");
    } catch (err: any) {
      addNotification("error", `Failed to generate PDF: ${err.message}`);
    } finally {
      setIsDownloading(false);
    }
  };

  const meta = PAGE_META[activePage] || {
    title: "Operations Console",
    subtitle: "Emergency evacuation decision support",
  };

  return (
    <div className="bg-white border-b border-slate-200 px-6 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
      <div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
          <button
            onClick={() => setActivePage("overview")}
            className="flex items-center gap-1 hover:text-slate-800 transition-colors font-medium"
          >
            <Home className="w-3.5 h-3.5" />
            <span>ResQ</span>
          </button>
          <ChevronRight className="w-3 h-3 text-slate-400" />
          <span className="text-slate-700 font-semibold">{meta.title}</span>
          {network && (
            <>
              <ChevronRight className="w-3 h-3 text-slate-400" />
              <span className="text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded font-mono text-[11px]">
                {network.network_id}
              </span>
            </>
          )}
        </div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          {meta.title}
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">{meta.subtitle}</p>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={handleDownloadPdf}
          disabled={isDownloading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-xs transition-colors"
          title="Download Official Situation Report (PDF)"
        >
          <FileDown className={`w-3.5 h-3.5 text-blue-600 ${isDownloading ? "animate-bounce" : ""}`} />
          <span className="hidden sm:inline">Export PDF</span>
        </button>

        <button
          onClick={refreshNetwork}
          disabled={isLoading}
          className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg shadow-xs transition-colors"
          title="Refresh network state"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>
    </div>
  );
};
