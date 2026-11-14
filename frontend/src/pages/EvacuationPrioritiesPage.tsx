import React, { useState } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowDownNarrowWide,
  Clock,
  Filter,
  HelpCircle,
  RefreshCw,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useApp } from "../context/AppContext";

export const EvacuationPrioritiesPage: React.FC = () => {
  const { reliefOverview, isReliefLoading, refreshRelief } = useApp();
  const [tierFilter, setTierFilter] = useState<string>("all");

  const priorities = reliefOverview?.priorities || [];

  const filteredPriorities = priorities.filter((p) => {
    if (tierFilter === "all") return true;
    return p.priority_tier.toLowerCase() === tierFilter.toLowerCase();
  });

  return (
    <div className="space-y-6">
      {/* Top Briefing Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 shrink-0 mt-0.5 shadow-xs">
            <AlertOctagon className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Evacuation Triage Priorities</h1>
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                DYNAMIC TRIAGE
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Affected zones ranked systematically by imminent hazard severity, evacuation time window, vulnerable population ratio, and corridor bottlenecks.
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs shadow-xs">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-600 font-medium">Filter Tier:</span>
            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="bg-transparent text-slate-800 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="all">All Tiers ({priorities.length})</option>
              <option value="critical">Critical Only</option>
              <option value="high">High Only</option>
              <option value="moderate">Moderate Only</option>
              <option value="low">Low Only</option>
            </select>
          </div>

          <button
            onClick={() => refreshRelief()}
            disabled={isReliefLoading}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1.5 transition-all shrink-0 shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isReliefLoading ? "animate-spin text-blue-600" : "text-slate-500"}`} />
            <span>Recalculate</span>
          </button>
        </div>
      </div>

      {/* Priority Cards Feed */}
      <div className="space-y-4">
        {filteredPriorities.length > 0 ? (
          filteredPriorities.map((area) => {
            const isCritical = area.priority_tier === "Critical";
            const isHigh = area.priority_tier === "High";
            const isModerate = area.priority_tier === "Moderate";

            const badgeBg = isCritical
              ? "bg-red-50 text-red-700 border-red-200"
              : isHigh
              ? "bg-amber-50 text-amber-800 border-amber-200"
              : isModerate
              ? "bg-blue-50 text-blue-700 border-blue-200"
              : "bg-emerald-50 text-emerald-700 border-emerald-200";

            const borderCard = isCritical
              ? "border-red-200 hover:border-red-300"
              : isHigh
              ? "border-amber-200 hover:border-amber-300"
              : "border-slate-200 hover:border-slate-300";

            return (
              <div
                key={area.area_id}
                className={`p-6 rounded-2xl border bg-white transition-all shadow-xs hover:shadow-cardHover ${borderCard}`}
              >
                {/* Header row: Rank, Zone Name, Tier, Score */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3.5 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center font-bold font-mono text-sm text-slate-800 shrink-0">
                      #{area.dispatch_order}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-sm font-bold text-slate-900 tracking-tight">{area.area_name}</h2>
                        <span className="text-[11px] font-mono text-slate-500 font-medium">[{area.area_id}]</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5 font-medium">
                        Dispatch Rank: Wave {area.dispatch_order} of {priorities.length}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-bold px-3 py-1 rounded-full border ${badgeBg}`}>
                      {area.priority_tier.toUpperCase()} PRIORITY
                    </span>
                    <div className="text-right hidden sm:block">
                      <span className="text-[10px] text-slate-500 block uppercase font-medium">Composite Score</span>
                      <span className="text-xs font-mono font-bold text-blue-700">{area.priority_score.toFixed(1)} / 100</span>
                    </div>
                  </div>
                </div>

                {/* Metrics Breakdown Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-4 p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[11px]">Total Population:</span>
                    <span className="font-bold text-slate-900 text-sm">{area.population.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px]">Vulnerable Residents:</span>
                    <span className="font-bold text-red-600 text-sm">
                      {area.vulnerable_population.toLocaleString()} ({area.vulnerability_pct.toFixed(0)}%)
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px]">Impact Window:</span>
                    <span className="font-bold text-amber-700 text-sm flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 inline text-amber-600" />
                      {area.time_to_impact_hours.toFixed(1)} Hours
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px]">Outgoing Road Width:</span>
                    <span className="font-bold text-slate-900 text-sm">
                      {area.outgoing_capacity.toLocaleString()} p/h
                      {area.capacity_deficit > 0 && (
                        <span className="text-red-600 font-mono text-[10px] ml-1">
                          (-{area.capacity_deficit} bottleneck)
                        </span>
                      )}
                    </span>
                  </div>
                </div>

                {/* "Why?" Clear Explanation Card */}
                <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100 text-xs flex items-start gap-2.5">
                  <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="font-bold text-blue-900 block">Why is this area ranked this way?</span>
                    <p className="text-slate-700 leading-relaxed">{area.explanation}</p>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="p-8 rounded-2xl bg-white border border-slate-200 text-center text-xs text-slate-500 shadow-xs">
            No areas match the selected tier filter.
          </div>
        )}
      </div>
    </div>
  );
};