import React from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  Database,
  Flame,
  GitCompare,
  GitPullRequest,
  Layers,
  MapPin,
  PencilRuler,
  PlayCircle,
  Radio,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  Truck,
  Users,
  Zap,
} from "lucide-react";
import { useApp } from "../context/AppContext";

export const LandingPage: React.FC = () => {
  const { setActivePage, login, openLexicon } = useApp();

  const handleEnterResQ = () => {
    // Instant entry as guest
    login("Emergency Operations Guest", "commander", "CMD-GUEST");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col justify-between selection:bg-blue-500 selection:text-white font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur sticky top-0 z-40 px-6 sm:px-10 py-4 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-xs">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-slate-900 tracking-tight">ResQ</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                v2.0 Operations
              </span>
            </div>
            <p className="text-[11px] text-slate-500 hidden sm:block font-medium">
              Disaster Evacuation Planning &amp; Relief Management System
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={openLexicon}
            className="text-xs text-slate-600 hover:text-slate-900 font-medium transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-100 flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-600" />
            <span className="hidden md:inline">Reference Guide</span>
          </button>
          <button
            onClick={() => setActivePage("login")}
            className="text-xs bg-white hover:bg-slate-50 text-slate-700 font-medium px-3.5 py-1.5 rounded-lg border border-slate-200 shadow-xs transition-colors"
          >
            Operator Login
          </button>
          <button
            onClick={handleEnterResQ}
            className="text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-1.5 rounded-lg flex items-center gap-1.5 shadow-xs transition-all"
          >
            <span>Enter ResQ Console</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Main Hero Section */}
      <main className="max-w-6xl mx-auto px-6 py-14 flex-1 flex flex-col items-center text-center">
        {/* Operations Ribbon */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold mb-6 shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
          <span>Intelligent Evacuation Routing &amp; Humanitarian Relief Distribution</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight max-w-4xl leading-tight">
          Disaster Evacuation Planning &amp;{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-700 via-sky-600 to-teal-600">
            Relief Management System
          </span>
        </h1>

        <p className="mt-6 text-base sm:text-lg text-slate-600 max-w-3xl leading-relaxed">
          An enterprise emergency-management decision support platform combining algorithmic{" "}
          <strong className="text-slate-900">Maximum Flow Optimization</strong>,{" "}
          <strong className="text-slate-900">Dijkstra Shortest Paths</strong>, and{" "}
          <strong className="text-slate-900">Sphere Standards Camp Supply Allocation</strong> to
          prioritize vulnerable populations, route evacuees around flooded corridors, and fairly distribute limited relief supplies.
        </p>

        {/* Prominent Enter ResQ Button & Action Group */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={handleEnterResQ}
            className="px-8 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-base flex items-center gap-2.5 shadow-md shadow-blue-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <span>Enter Operations Console</span>
            <ArrowRight className="w-5 h-5" />
          </button>

          <button
            onClick={() => setActivePage("login")}
            className="px-6 py-3.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm border border-slate-200 shadow-xs flex items-center gap-2 transition-all"
          >
            <span>Operator Access</span>
          </button>
        </div>

        {/* Live Metrics Strip */}
        <div className="mt-12 w-full grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Algorithm</div>
            <div className="text-base font-bold text-slate-900 mt-1">Dinic Max-Flow</div>
            <div className="text-[10px] text-blue-700 font-mono font-medium mt-0.5">O(V² &middot; E) worst-case</div>
          </div>
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Bottleneck Engine</div>
            <div className="text-base font-bold text-slate-900 mt-1">Exact Min-Cut</div>
            <div className="text-[10px] text-emerald-700 font-mono font-medium mt-0.5">Residual BFS O(V + E)</div>
          </div>
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Demo Grid</div>
            <div className="text-base font-bold text-slate-900 mt-1">5 Zones &bull; 4 Shelters</div>
            <div className="text-[10px] text-amber-700 font-mono font-medium mt-0.5">4,350 evacuees/hour</div>
          </div>
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Disruption Lab</div>
            <div className="text-base font-bold text-slate-900 mt-1">5 What-If Tests</div>
            <div className="text-[10px] text-purple-700 font-mono font-medium mt-0.5">Zero base data mutation</div>
          </div>
        </div>

        {/* Comprehensive Project Explanations */}
        <div className="mt-16 w-full space-y-10 text-left">
          {/* Section 1: What ResQ Does & Why It Is Useful */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                <Compass className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-900">What the Project Does</h2>
              <p className="text-xs text-slate-600 leading-relaxed">
                ResQ models disaster-impacted urban regions as directed, capacity-constrained networks.
                It augments the network with a virtual Super-Source ($S^*$) connecting to affected population centers
                and a virtual Super-Sink ($T^*$) receiving flow into safe shelters. It then computes the globally optimal
                distribution of evacuees across available corridors and shelters.
              </p>
              <ul className="text-xs text-slate-600 space-y-1.5 pt-1">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <span>Enforces corridor capacities and intermediate junction flow conservation</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <span>Calculates exact maximum civilian throughput using Dinic's Algorithm</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <span>Generates turn-by-turn route decomposition and wave clearance timelines</span>
                </li>
              </ul>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center border border-amber-200">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Why It Is Useful in Disasters</h2>
              <p className="text-xs text-slate-600 leading-relaxed">
                During urban floods, earthquakes, or industrial hazmat leaks, naive routing (such as sending
                everyone along the shortest distance road) creates severe traffic jams and leaves vulnerable civilians
                stranded. ResQ prevents deceptive greedy traps and provides civil defense commanders with mathematical proof
                of optimal evacuation capacity.
              </p>
              <ul className="text-xs text-slate-600 space-y-1.5 pt-1">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>Avoids greedy suboptimal traps that strand thousands in hazard sectors</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>Pinpoints exact bridge and shelter bottlenecks limiting total evacuation</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>Validates infrastructure upgrade return-on-investment before construction</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Section 2: What Maximum-Flow Analysis Means */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-200">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  What Maximum-Flow Analysis Means
                </h2>
                <p className="text-xs text-slate-500">
                  Mathematical foundation: Ford-Fulkerson principle &amp; the Max-Flow Min-Cut Theorem
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed max-w-4xl">
              <strong>Maximum-Flow Analysis</strong> determines the absolute highest rate of evacuees that can safely
              travel from hazard zones to safe shelters per unit time without violating two inviolable physical constraints:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-blue-700 block mb-1">1. Capacity Constraint:</span>
                <p className="text-[11px] text-slate-600 leading-relaxed font-mono">
                  0 &le; f(u, v) &le; c(u, v) for all road corridors (u, v) in E. Traffic flow cannot exceed road width or bridge throughput.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-blue-700 block mb-1">2. Flow Conservation:</span>
                <p className="text-[11px] text-slate-600 leading-relaxed font-mono">
                  &sum; f(v, u) = &sum; f(u, w) for every transit junction u. No evacuees can vanish or accumulate indefinitely at intersections.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-950 leading-relaxed">
              <strong className="text-emerald-800">The Max-Flow Min-Cut Theorem: </strong>
              The maximum amount of flow passing from source to sink is strictly equal to the total capacity of the
              edges in the <em>minimum cut</em> ($|f^*| = c(S^*, T^*)$). This guarantees that widening any corridor
              outside the minimum cut will have exactly <strong>zero effect</strong> on total evacuation rate until cut bottlenecks are resolved.
            </div>
          </div>
        </div>

        {/* Bottom Prominent Enter ResQ Section */}
        <div className="mt-16 p-8 rounded-2xl bg-blue-50/70 border border-blue-200 w-full flex flex-col sm:flex-row items-center justify-between gap-6 shadow-xs">
          <div className="text-left">
            <h3 className="text-lg font-bold text-slate-900">Ready for Emergency Operations?</h3>
            <p className="text-xs text-slate-600 mt-1 max-w-xl">
              Launch into the active console with the official 5-hazard, 4-shelter demonstration network preloaded.
            </p>
          </div>
          <button
            onClick={handleEnterResQ}
            className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm flex items-center gap-2 shadow-xs shrink-0 transition-all"
          >
            <span>Enter ResQ Console</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 px-6 sm:px-10 py-6 text-center text-xs text-slate-500 bg-white shadow-xs">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="font-medium">
            ResQ Disaster Evacuation Planning &amp; Relief Management System
          </span>
          <div className="flex items-center gap-4 text-slate-500">
            <button onClick={openLexicon} className="hover:text-slate-800 transition-colors font-medium">
              Reference Guide
            </button>
            <button onClick={() => setActivePage("login")} className="hover:text-slate-800 transition-colors font-medium">
              Operator Access
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};
