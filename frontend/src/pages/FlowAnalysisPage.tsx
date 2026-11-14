import React, { useState, useMemo } from "react";
import { useApp } from "../context/AppContext";
import { TermTooltip } from "../components/common/TermTooltip";
import {
  Activity,
  Filter,
  Route,
  Search,
  Zap,
  Clock,
} from "lucide-react";
import type { EvacuationRoute } from "../types/api";

export const FlowAnalysisPage: React.FC = () => {
  const { network, analysis, dinicResult, minCutResult, runDinicAnalysis, isSolving } = useApp();

  const [searchQuery, setSearchQuery] = useState("");
  const [filterState, setFilterState] = useState<"ALL" | "SATURATED" | "MINCUT" | "ACTIVE" | "IDLE">("ALL");
  const [sortField, setSortField] = useState<"utilization" | "flow" | "capacity">("utilization");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState<EvacuationRoute | null>(null);

  const minCutRoadIds = useMemo(() => {
    return new Set(minCutResult?.road_bottlenecks.map((rb) => rb.edge_id) || []);
  }, [minCutResult]);

  // Road details list
  const roadFlows = useMemo(() => {
    if (!network || !dinicResult) return [];

    return network.roads.map((road) => {
      const flowDetail = dinicResult.road_flows.find((rf) => rf.road_id === road.road_id);
      const flow = flowDetail?.flow ?? 0;
      const nominalCap = road.capacity;
      const utilization = nominalCap > 0 ? (flow / nominalCap) * 100 : 0;
      const isSaturated = flowDetail?.is_saturated ?? (nominalCap > 0 && flow >= nominalCap);
      const isMinCut = minCutRoadIds.has(road.road_id);
      const travelTimeMinutes = road.travel_time_min;

      return {
        ...road,
        flow,
        utilization,
        isSaturated,
        isMinCut,
        residualCapacity: Math.max(0, nominalCap - flow),
        travelTimeMinutes,
      };
    });
  }, [network, dinicResult, minCutRoadIds]);

  // Filtered & sorted roads
  const filteredRoads = useMemo(() => {
    return roadFlows
      .filter((r) => {
        const matchesSearch =
          r.road_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.source_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.target_id.toLowerCase().includes(searchQuery.toLowerCase());

        if (!matchesSearch) return false;

        if (filterState === "SATURATED") return r.isSaturated;
        if (filterState === "MINCUT") return r.isMinCut;
        if (filterState === "ACTIVE") return r.flow > 0;
        if (filterState === "IDLE") return r.flow === 0;
        return true;
      })
      .sort((a, b) => {
        let diff = 0;
        if (sortField === "utilization") diff = a.utilization - b.utilization;
        else if (sortField === "flow") diff = a.flow - b.flow;
        else if (sortField === "capacity") diff = a.capacity - b.capacity;
        return sortAsc ? diff : -diff;
      });
  }, [roadFlows, searchQuery, filterState, sortField, sortAsc]);

  // Overall statistics
  const totalCorridors = roadFlows.length;
  const saturatedCount = roadFlows.filter((r) => r.isSaturated).length;
  const activeCount = roadFlows.filter((r) => r.flow > 0).length;
  const avgUtilization =
    totalCorridors > 0
      ? roadFlows.reduce((acc, r) => acc + r.utilization, 0) / totalCorridors
      : 0;

  const routes = analysis?.routes || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-sky-600" />
            Corridor Flow Distribution & Route Decomposition
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Exhaustive telemetry of road capacities, active evacuee throughput, saturation ratios, and decomposed routes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => runDinicAnalysis()}
            disabled={isSolving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${isSolving ? "animate-spin" : ""}`} />
            <span>{isSolving ? "Recomputing..." : "Recalculate Flow"}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Total Corridors</span>
          <span className="text-2xl font-mono font-bold text-slate-900">{totalCorridors}</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">{activeCount} carrying active flow</span>
        </div>

        <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Saturated Arterials</span>
          <span className="text-2xl font-mono font-bold text-amber-600">{saturatedCount}</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Operating at 100% capacity</span>
        </div>

        <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Avg Network Utilization</span>
          <span className="text-2xl font-mono font-bold text-sky-600">{avgUtilization.toFixed(1)}%</span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Weighted across all roads</span>
        </div>

        <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Simple Evac Routes</span>
          <span className="text-2xl font-mono font-bold text-emerald-600">
            {routes.length}
          </span>
          <span className="text-[11px] text-slate-500 block mt-0.5">Decomposed path flows</span>
        </div>
      </div>

      {/* Search, Filter & Control Toolbar */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-3 px-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search road ID, name, corridor..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none text-slate-800 placeholder-slate-400 focus:outline-none w-48 text-xs"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="text-slate-400 hover:text-slate-600">
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filterState}
              onChange={(e) => setFilterState(e.target.value as any)}
              className="bg-transparent border-none text-slate-700 focus:outline-none text-xs cursor-pointer"
            >
              <option value="ALL">All Corridors ({roadFlows.length})</option>
              <option value="SATURATED">Saturated Only ({saturatedCount})</option>
              <option value="MINCUT">Min-Cut Bottlenecks Only</option>
              <option value="ACTIVE">Active Flow Only ({activeCount})</option>
              <option value="IDLE">Zero Flow</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-600">
          <span className="font-medium text-slate-500">Sort by:</span>
          <button
            onClick={() => {
              if (sortField === "utilization") setSortAsc(!sortAsc);
              else {
                setSortField("utilization");
                setSortAsc(false);
              }
            }}
            className={`px-2.5 py-1 rounded-lg border transition-all ${
              sortField === "utilization"
                ? "border-sky-500 bg-sky-50 text-sky-700 font-semibold"
                : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Utilization {sortField === "utilization" ? (sortAsc ? "↑" : "↓") : ""}
          </button>
          <button
            onClick={() => {
              if (sortField === "flow") setSortAsc(!sortAsc);
              else {
                setSortField("flow");
                setSortAsc(false);
              }
            }}
            className={`px-2.5 py-1 rounded-lg border transition-all ${
              sortField === "flow"
                ? "border-sky-500 bg-sky-50 text-sky-700 font-semibold"
                : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Flow {sortField === "flow" ? (sortAsc ? "↑" : "↓") : ""}
          </button>
          <button
            onClick={() => {
              if (sortField === "capacity") setSortAsc(!sortAsc);
              else {
                setSortField("capacity");
                setSortAsc(false);
              }
            }}
            className={`px-2.5 py-1 rounded-lg border transition-all ${
              sortField === "capacity"
                ? "border-sky-500 bg-sky-50 text-sky-700 font-semibold"
                : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
            }`}
          >
            Capacity {sortField === "capacity" ? (sortAsc ? "↑" : "↓") : ""}
          </button>
        </div>
      </div>

      {/* Main Road Corridor Flow Table */}
      <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-3.5">Road ID / Name</th>
                <th className="py-3 px-3">Corridor</th>
                <th className="py-3 px-3 text-right">Distance & Transit</th>
                <th className="py-3 px-3 text-right">Nominal Capacity</th>
                <th className="py-3 px-3 text-right">
                  <TermTooltip termKey="maximum-flow">Assigned Flow</TermTooltip>
                </th>
                <th className="py-3 px-3 text-right">
                  <TermTooltip termKey="residual-capacity">Residual Room</TermTooltip>
                </th>
                <th className="py-3 px-4">Utilization</th>
                <th className="py-3 px-3 text-center">
                  <TermTooltip termKey="bottleneck">Status</TermTooltip>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRoads.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No corridors match your search criteria.
                  </td>
                </tr>
              ) : (
                filteredRoads.map((road) => (
                  <tr key={road.road_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3.5">
                      <div className="font-semibold text-slate-900">{road.name}</div>
                      <div className="font-mono text-[10px] text-slate-400">{road.road_id}</div>
                    </td>

                    <td className="py-2.5 px-3 font-mono font-medium text-slate-700">
                      <span className="text-slate-600">{road.source_id}</span>
                      <span className="text-sky-600 mx-1 font-bold">→</span>
                      <span className="text-slate-600">{road.target_id}</span>
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                      <div>{road.distance} km</div>
                      <div className="text-[10px] text-slate-400">
                        ~{road.travelTimeMinutes.toFixed(1)} mins
                      </div>
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-700">
                      {road.capacity} <span className="text-[10px] text-slate-400">p/h</span>
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono font-bold text-sky-600">
                      {road.flow} <span className="text-[10px] text-slate-400">p/h</span>
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                      {road.residualCapacity} <span className="text-[10px] text-slate-400">p/h</span>
                    </td>

                    <td className="py-2.5 px-4 min-w-[140px]">
                      <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                        <span className="text-slate-600 font-semibold">{road.utilization.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200">
                        <div
                          className={`h-full ${
                            road.isSaturated
                              ? "bg-amber-500"
                              : road.utilization > 75
                              ? "bg-sky-500"
                              : road.utilization > 0
                              ? "bg-emerald-500"
                              : "bg-transparent"
                          }`}
                          style={{ width: `${Math.min(100, road.utilization)}%` }}
                        ></div>
                      </div>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      {road.isMinCut ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 shadow-2xs">
                          MIN-CUT
                        </span>
                      ) : road.isSaturated ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                          SATURATED
                        </span>
                      ) : road.flow > 0 ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                          IDLE
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Decomposed Evacuation Routes Section */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Route className="w-4 h-4 text-emerald-600" />
              Decomposed Evacuation Routes
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Flow decomposition converts total network flow into explicit origin-to-shelter evacuation paths for emergency vehicles.
            </p>
          </div>
        </div>

        {routes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {routes.map((route, idx) => (
              <div
                key={route.route_index || idx}
                onClick={() => setSelectedRoute(route)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                  selectedRoute?.route_index === route.route_index
                    ? "bg-sky-50/70 border-sky-400 shadow-xs ring-1 ring-sky-300"
                    : "bg-slate-50/50 border-slate-200 hover:border-slate-300 hover:bg-white"
                }`}
              >
                <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-2">
                  <span className="font-mono text-xs font-bold text-slate-800">
                    Route #{route.route_index + 1}: {route.source_name || route.source_id} → {route.shelter_name || route.shelter_id}
                  </span>
                  <span className="font-mono text-xs font-bold text-emerald-600">
                    +{route.flow.toLocaleString()} p/h
                  </span>
                </div>

                <div className="text-xs font-mono text-slate-600 mb-2 flex items-center flex-wrap gap-1">
                  {route.node_path.map((n, i) => (
                    <React.Fragment key={i}>
                      <span className="text-slate-700 bg-white px-1.5 py-0.5 rounded border border-slate-200 shadow-2xs">
                        {n}
                      </span>
                      {i < route.node_path.length - 1 && <span className="text-sky-600 font-bold">→</span>}
                    </React.Fragment>
                  ))}
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-400" />
                    ~{route.total_travel_time_min.toFixed(1)} mins transit ({route.total_distance.toFixed(1)} km)
                  </span>
                  {route.bottleneck_road_id && (
                    <span className="text-amber-700 font-semibold text-[10px] font-mono bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                      Limiting: {route.bottleneck_road_id}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 text-xs">
            No decomposed evacuation routes available. Run Dinic Max-Flow to decompose active paths.
          </div>
        )}
      </div>
    </div>
  );
};
