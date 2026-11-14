import React from "react";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Compass,
  FileText,
  HelpCircle,
  Home,
  Info,
  Radio,
  RefreshCw,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useApp } from "../context/AppContext";

export const OverviewPage: React.FC = () => {
  const { reliefOverview, isReliefLoading, refreshRelief, setActivePage } = useApp();

  if (isReliefLoading && !reliefOverview) {
    return (
      <div className="min-h-[500px] flex flex-col items-center justify-center p-8 text-center space-y-4 bg-white border border-slate-200 rounded-2xl shadow-xs">
        <div className="w-12 h-12 rounded-full border-4 border-slate-200 border-t-blue-600 animate-spin" />
        <h3 className="text-base font-semibold text-slate-900">Loading Disaster Situation Assessment...</h3>
        <p className="text-xs text-slate-500 max-w-md">
          Gathering real-time hazard severity, triage rankings, corridor safety reports, and camp inventories.
        </p>
      </div>
    );
  }

  const priorities = reliefOverview?.priorities || [];
  const routes = reliefOverview?.routes || [];
  const shelters = reliefOverview?.shelters || [];
  const resources = reliefOverview?.resources;

  // 1. Critical and High Affected Areas
  const criticalAreas = priorities.filter(
    (p) => p.priority_tier === "Critical" || p.priority_tier === "High"
  );

  // 2. Important Route Warnings (Hazard avoidance or unverified reports)
  const routeWarnings = routes.filter(
    (r) => r.has_hazard_roads || r.has_unverified_roads || r.operational_advisory !== "RECOMMENDED"
  );

  // 3. Major Resource Shortages across camps
  const criticalShortagesList: {
    shelterId: string;
    shelterName: string;
    resourceName: string;
    resourceLabel: string;
    unit: string;
    shortage: number;
    daysOfAutonomy: number;
  }[] = [];

  if (resources?.shelter_allocations) {
    for (const shl of resources.shelter_allocations) {
      for (const [key, item] of Object.entries(shl.resources)) {
        if (item.shortage > 0 || item.days_of_autonomy < 2.5) {
          criticalShortagesList.push({
            shelterId: shl.shelter_id,
            shelterName: shl.shelter_name,
            resourceName: key,
            resourceLabel: item.resource_label,
            unit: item.unit,
            shortage: item.shortage,
            daysOfAutonomy: item.days_of_autonomy,
          });
        }
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Executive Situation Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 shrink-0 mt-0.5 shadow-xs">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Disaster Situation Overview</h1>
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">
                ACTIVE EVACUATION
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Consolidated operational intelligence for regional emergency dispatch, safe routing, shelter intake, and relief logistics.
            </p>
          </div>
        </div>

        <button
          onClick={() => refreshRelief()}
          disabled={isReliefLoading}
          className="self-start md:self-auto px-4 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-2 transition-all shrink-0 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isReliefLoading ? "animate-spin text-blue-600" : "text-slate-500"}`} />
          <span>Refresh Situation</span>
        </button>
      </div>

      {/* Grid: Recommended Actions & Critical Areas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 1: Recommended Immediate Actions */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-blue-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Recommended Actions</h2>
              </div>
              <span className="text-[11px] text-slate-500 font-medium font-mono">
                {reliefOverview?.summary_advisories?.length || 0} Priority Directives
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {reliefOverview?.summary_advisories && reliefOverview.summary_advisories.length > 0 ? (
                reliefOverview.summary_advisories.map((advisory, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl border border-slate-200/90 bg-slate-50/60 flex items-start gap-3 hover:border-slate-300 transition-colors"
                  >
                    <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                      {idx + 1}
                    </div>
                    <div className="space-y-1 text-xs">
                      <p className="text-slate-800 font-medium leading-relaxed">{advisory}</p>
                      <div className="flex items-center gap-1.5 text-[11px] text-blue-600 font-medium">
                        <HelpCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>Why: Derived dynamically from live impact window, corridor flow bounds, and stock depletion rates.</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center">
                  No critical directives pending. All systems within standard operational thresholds.
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">Review prioritized zone clearance order</span>
            <button
              onClick={() => setActivePage("priorities")}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1.5 transition-colors"
            >
              <span>View Evacuation Priorities</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Section 2: Critical Affected Areas */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-red-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Critical Affected Areas</h2>
              </div>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200 font-semibold">
                {criticalAreas.length} Requiring Rapid Transit
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {criticalAreas.length > 0 ? (
                criticalAreas.map((area) => (
                  <div
                    key={area.area_id}
                    className="p-3.5 rounded-xl border border-red-100 bg-red-50/20 hover:border-red-200 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-xs">{area.area_name}</span>
                        <span className="text-[10px] font-mono font-medium text-slate-500">[{area.area_id}]</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          area.priority_tier === "Critical"
                            ? "bg-red-50 text-red-700 border-red-200"
                            : "bg-amber-50 text-amber-800 border-amber-200"
                        }`}
                      >
                        {area.priority_tier.toUpperCase()} PRIORITY
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2.5 border-t border-slate-200/60 text-[11px]">
                      <div>
                        <span className="text-slate-500 block text-[10px]">Population:</span>
                        <span className="font-bold text-slate-800">{area.population.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px]">Vulnerable:</span>
                        <span className="font-bold text-red-600">
                          {area.vulnerable_population.toLocaleString()} ({area.vulnerability_pct.toFixed(0)}%)
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px]">Impact Window:</span>
                        <span className="font-bold text-amber-700 flex items-center gap-1">
                          <Clock className="w-3 h-3 inline" />
                          {area.time_to_impact_hours.toFixed(1)}h
                        </span>
                      </div>
                    </div>

                    <div className="mt-2.5 pt-2 border-t border-slate-200/60 text-[11px] text-slate-700 flex items-start gap-1.5">
                      <strong className="text-blue-600 shrink-0 font-semibold">Why:</strong>
                      <span className="leading-snug">{area.explanation}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center">
                  No areas currently classified as Critical.
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">Full ranking with demographic & road capacity metrics</span>
            <button
              onClick={() => setActivePage("priorities")}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1.5 transition-colors"
            >
              <span>View All 5 Zones</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Route Warnings & Shelter Availability */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 3: Important Route Warnings */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Important Route Warnings</h2>
              </div>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                {routeWarnings.length} Road Warnings
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {routeWarnings.length > 0 ? (
                routeWarnings.slice(0, 3).map((route) => (
                  <div
                    key={route.route_id}
                    className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex flex-col gap-2 hover:border-slate-300 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-bold text-slate-900">
                        {route.source_name} &rarr; {route.shelter_name}
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          route.operational_advisory === "AVOID_HAZARD"
                            ? "bg-red-50 text-red-700 border-red-200"
                            : route.operational_advisory === "UNVERIFIED_SCOUT_REQUIRED"
                            ? "bg-amber-50 text-amber-800 border-amber-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                        }`}
                      >
                        {route.operational_advisory.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-600">
                      {route.recommendation_notes}
                    </div>

                    <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>Distance: {route.total_distance_km} km</span>
                      <span>Transit: {route.total_travel_time_min} min</span>
                      <span>Chokepoint: {route.bottleneck_capacity.toLocaleString()} p/h</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center">
                  All active corridors verified clear of obstructions and hazard risks.
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">Inspect road statuses and send scout confirmations</span>
            <button
              onClick={() => setActivePage("routes")}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1.5 transition-colors"
            >
              <span>Open Routes &amp; Shelters Map</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Section 4: Shelter Availability */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Home className="w-4 h-4 text-emerald-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Shelter Availability</h2>
              </div>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                {shelters.length} Facilities Active
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {shelters.map((s) => {
                const satPct = Math.min(100, Math.round((s.projected_total / s.total_capacity) * 100));
                return (
                  <div key={s.shelter_id} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 hover:border-slate-300 transition-colors">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900">{s.shelter_name}</span>
                        <span className="text-[10px] font-mono text-slate-500 font-medium">[{s.shelter_id}]</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          s.capacity_status === "AVAILABLE"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : s.capacity_status === "NEAR_CAPACITY"
                            ? "bg-amber-50 text-amber-800 border-amber-200"
                            : "bg-red-50 text-red-700 border-red-200"
                        }`}
                      >
                        {s.capacity_status.replace(/_/g, " ")}
                      </span>
                    </div>

                    {/* Capacity progress bar */}
                    <div className="mt-2 space-y-1">
                      <div className="flex justify-between text-[11px] text-slate-500 font-mono font-medium">
                        <span>Projected: {s.projected_total.toLocaleString()} / {s.total_capacity.toLocaleString()}</span>
                        <span>{satPct}% Committed</span>
                      </div>
                      <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            satPct >= 95 ? "bg-red-600" : satPct >= 75 ? "bg-amber-500" : "bg-emerald-600"
                          }`}
                          style={{ width: `${satPct}%` }}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2 border-t border-slate-200/60 text-[10px] text-slate-700">
                      <div>
                        <span className="text-slate-500 block">Current Occupants:</span>
                        <span className="font-bold text-slate-800">{s.current_occupancy.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Available Beds:</span>
                        <span className="font-bold text-emerald-600">{s.available_capacity.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Incoming Flow:</span>
                        <span className="font-bold text-blue-600">+{s.expected_incoming.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">Inspect supply allocations and demand forecasting</span>
            <button
              onClick={() => setActivePage("resources")}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1.5 transition-colors"
            >
              <span>View Camp Resources</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Section 5: Major Resource Shortages */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Boxes className="w-4 h-4 text-amber-600" />
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Major Resource Shortages &amp; Supply Gaps</h2>
          </div>
          <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
            Sphere Standards: 3-Day Autonomous Window
          </span>
        </div>

        <div className="mt-4">
          {criticalShortagesList.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {criticalShortagesList.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-amber-200/80 bg-amber-50/20 flex flex-col justify-between hover:border-amber-300 transition-colors"
                >
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-bold text-slate-900">{item.shelterName}</span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300">
                        {item.daysOfAutonomy.toFixed(1)} Days Left
                      </span>
                    </div>
                    <div className="text-xs text-slate-700 font-semibold">{item.resourceLabel}</div>
                    <div className="text-[11px] text-red-600 mt-1 font-mono font-bold">
                      Unmet Deficit: {item.shortage.toLocaleString()} {item.unit}
                    </div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-amber-200/60 text-[10px] text-slate-600">
                    <span className="text-blue-600 font-bold">Why:</span> Camp inflow exceeds regional depot stock. Proportional fair share deployed; resupply convoy required.
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200 text-center space-y-2">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto" />
              <p className="text-xs font-bold text-slate-800">All Camp Supplies Sufficient for 3-Day Plan</p>
              <p className="text-[11px] text-slate-500">
                Water, food, and medical stock meet or exceed Sphere humanitarian baseline consumption requirements.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};