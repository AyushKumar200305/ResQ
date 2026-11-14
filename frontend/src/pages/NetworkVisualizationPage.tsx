import React, { useState, useMemo, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { NetworkGraph } from "../components/graph/NetworkGraph";
import {
  Compass,
  Filter,
  Layers,
  MapPin,
  Search,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import type { NodeData, RoadData, RoadFlowDetail } from "../types/api";

export const NetworkVisualizationPage: React.FC = () => {
  const {
    network,
    dinicResult,
    minCutResult,
    dijkstraResult,
    setDijkstraResult,
    isSolving,
    runDinicAnalysis,
    addNotification,
  } = useApp();

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedRoadId, setSelectedRoadId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"ALL" | "affected_area" | "junction" | "shelter">("ALL");

  // Dijkstra shortest path UI state
  const [dijkstraSource, setDijkstraSource] = useState<string>("");
  const [dijkstraTarget, setDijkstraTarget] = useState<string>("");
  const [isFindingRoute, setIsFindingRoute] = useState(false);

  // Auto-populate Dijkstra source/target if empty
  const affectedAreas = useMemo(
    () => (network ? network.nodes.filter((n) => n.node_type === "affected_area") : []),
    [network]
  );
  const shelters = useMemo(
    () => (network ? network.nodes.filter((n) => n.node_type === "shelter") : []),
    [network]
  );

  useEffect(() => {
    if (affectedAreas.length > 0 && !dijkstraSource) {
      setDijkstraSource(affectedAreas[0].node_id);
    }
    if (shelters.length > 0 && !dijkstraTarget) {
      setDijkstraTarget(shelters[0].node_id);
    }
  }, [affectedAreas, shelters, dijkstraSource, dijkstraTarget]);

  // Handle Dijkstra search
  const handleFindShortestPath = async () => {
    if (!dijkstraSource || !dijkstraTarget) {
      addNotification("warning", "Select both an origin area and target shelter.");
      return;
    }
    setIsFindingRoute(true);
    try {
      const res = await api.solveDijkstra(dijkstraSource, dijkstraTarget);
      setDijkstraResult(res);
      if (res.shortest_route) {
        addNotification(
          "success",
          `Shortest path found: ${res.shortest_route.total_distance.toFixed(1)} km across ${
            res.shortest_route.node_path.length - 1
          } hops.`
        );
      } else {
        addNotification("warning", "No path found between selected nodes.");
      }
    } catch (err: any) {
      addNotification("error", `Shortest route computation failed: ${err.message}`);
    } finally {
      setIsFindingRoute(false);
    }
  };

  const handleClearRoute = () => {
    setDijkstraResult(null);
  };

  // Node telemetry
  const activeNode: NodeData | null = useMemo(() => {
    if (!selectedNodeId || !network) return null;
    return network.nodes.find((n) => n.node_id === selectedNodeId) || null;
  }, [selectedNodeId, network]);

  const activeRoad: RoadData | null = useMemo(() => {
    if (!selectedRoadId || !network) return null;
    return network.roads.find((r) => r.road_id === selectedRoadId) || null;
  }, [selectedRoadId, network]);

  const activeRoadFlow: RoadFlowDetail | null = useMemo(() => {
    if (!selectedRoadId || !dinicResult) return null;
    return dinicResult.road_flows.find((rf) => rf.road_id === selectedRoadId) || null;
  }, [selectedRoadId, dinicResult]);

  return (
    <div className="space-y-4">
      {/* Top Controls & Status Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 px-4 flex flex-wrap items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950/70 border border-slate-800 px-3 py-1.5 rounded-md text-xs">
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Locate node ID / name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none text-slate-200 placeholder-slate-500 focus:outline-none w-36 sm:w-48 text-xs"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="text-slate-500 hover:text-slate-300 text-xs">
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 bg-slate-950/70 border border-slate-800 px-2.5 py-1.5 rounded-md text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              className="bg-transparent border-none text-slate-300 focus:outline-none text-xs cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900 text-slate-200">All Nodes</option>
              <option value="affected_area" className="bg-slate-900 text-rose-300">Affected Areas</option>
              <option value="junction" className="bg-slate-900 text-sky-300">Junctions</option>
              <option value="shelter" className="bg-slate-900 text-emerald-300">Shelters</option>
            </select>
          </div>
        </div>

        {/* Action Triggers */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => runDinicAnalysis()}
            disabled={isSolving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium shadow-sm transition-all disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${isSolving ? "animate-spin" : ""}`} />
            <span>{isSolving ? "Computing Flow..." : "Run Dinic Max-Flow"}</span>
          </button>
        </div>
      </div>

      {/* Main Graph Canvas and Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Graph Canvas Column (3/4 width) */}
        <div className="lg:col-span-3 flex flex-col gap-3">
          <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden shadow-inner h-[620px] relative">
            <NetworkGraph
              onNodeClick={(id) => {
                setSelectedNodeId(id);
                setSelectedRoadId(null);
              }}
              onRoadClick={(id) => {
                setSelectedRoadId(id);
                setSelectedNodeId(null);
              }}
            />
          </div>

          {/* Educational Legend Footer */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-xs flex flex-wrap items-center justify-between gap-4 text-slate-400">
            <div className="flex items-center gap-4 flex-wrap">
              <span className="font-semibold text-slate-300">Topology Legend:</span>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 ring-2 ring-rose-500/30"></span>
                <span className="text-slate-300">Affected Area (Source)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500 ring-2 ring-sky-500/30"></span>
                <span className="text-slate-300">Transit Junction</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-500/30"></span>
                <span className="text-slate-300">Safe Shelter (Sink)</span>
              </div>
            </div>

            <div className="flex items-center gap-4 flex-wrap">
              <span className="font-semibold text-slate-300">Road States:</span>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-sky-400 inline-block"></span>
                <span>Active Flow</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-amber-400 inline-block"></span>
                <span>Saturated (100%)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-rose-500 inline-block shadow-[0_0_6px_#f43f5e]"></span>
                <span className="text-rose-400 font-medium">Min-Cut Bottleneck</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-slate-600 border border-dashed border-slate-400 inline-block"></span>
                <span>Zero Flow / Closed</span>
              </div>
            </div>
          </div>
        </div>

        {/* Telemetry Inspector Column (1/4 width) */}
        <div className="flex flex-col gap-3">
          {/* Node/Road Inspector Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col flex-1 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center justify-between">
              <span>Element Telemetry</span>
              {(selectedNodeId || selectedRoadId) && (
                <button
                  onClick={() => {
                    setSelectedNodeId(null);
                    setSelectedRoadId(null);
                  }}
                  className="text-[11px] text-slate-500 hover:text-slate-300"
                >
                  Clear Selection
                </button>
              )}
            </h3>

            {activeNode ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div>
                    <h4 className="text-sm font-bold text-slate-100">{activeNode.name}</h4>
                    <span className="text-xs font-mono text-slate-400">{activeNode.node_id}</span>
                  </div>
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      activeNode.node_type === "affected_area"
                        ? "bg-rose-950/80 text-rose-400 border border-rose-800"
                        : activeNode.node_type === "shelter"
                        ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                        : "bg-sky-950/80 text-sky-400 border border-sky-800"
                    }`}
                  >
                    {activeNode.node_type.replace("_", " ")}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Grid Coordinates</span>
                    <span className="text-slate-200 font-mono font-medium">
                      ({activeNode.x?.toFixed(1) ?? 0}, {activeNode.y?.toFixed(1) ?? 0})
                    </span>
                  </div>

                  {activeNode.node_type === "affected_area" && (
                    <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                      <span className="text-slate-500 block text-[11px]">Population</span>
                      <span className="text-rose-400 font-mono font-bold">
                        {activeNode.population?.toLocaleString()} evacuees
                      </span>
                    </div>
                  )}

                  {activeNode.node_type === "shelter" && (
                    <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                      <span className="text-slate-500 block text-[11px]">Shelter Capacity</span>
                      <span className="text-emerald-400 font-mono font-bold">
                        {activeNode.shelter_capacity?.toLocaleString()} evacuees
                      </span>
                    </div>
                  )}
                </div>

                {/* Connected Roads */}
                {network && (
                  <div className="mt-2">
                    <span className="text-xs font-medium text-slate-400 block mb-1.5">Connected Corridors</span>
                    <div className="space-y-1 max-h-36 overflow-y-auto pr-1 text-xs font-mono">
                      {network.roads
                        .filter((r) => r.source_id === activeNode.node_id || r.target_id === activeNode.node_id)
                        .map((r) => {
                          const rf = dinicResult?.road_flows.find((f) => f.road_id === r.road_id);
                          const flow = rf?.flow ?? 0;
                          return (
                            <div
                              key={r.road_id}
                              onClick={() => {
                                setSelectedRoadId(r.road_id);
                                setSelectedNodeId(null);
                              }}
                              className="p-1.5 rounded bg-slate-950/40 hover:bg-slate-800 border border-slate-800 flex items-center justify-between cursor-pointer"
                            >
                              <span className="text-slate-300">
                                {r.source_id} → {r.target_id}
                              </span>
                              <span className="text-sky-400 font-bold">
                                {flow}/{r.capacity}
                              </span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}
              </div>
            ) : activeRoad ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div>
                    <h4 className="text-sm font-bold text-slate-100">{activeRoad.name}</h4>
                    <span className="text-xs font-mono text-slate-400">{activeRoad.road_id}</span>
                  </div>
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      activeRoadFlow?.is_saturated
                        ? "bg-amber-950/80 text-amber-400 border border-amber-800"
                        : "bg-sky-950/80 text-sky-400 border border-sky-800"
                    }`}
                  >
                    {activeRoadFlow?.is_saturated ? "SATURATED" : "AVAILABLE"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Roadway Corridor</span>
                    <span className="text-slate-200 font-mono font-medium">
                      {activeRoad.source_id} → {activeRoad.target_id}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Distance / Transit</span>
                    <span className="text-slate-200 font-mono font-medium">
                      {activeRoad.distance} km (~{activeRoad.travel_time_min.toFixed(1)}m)
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Nominal Capacity</span>
                    <span className="text-slate-200 font-mono font-bold">{activeRoad.capacity} p/h</span>
                  </div>
                  <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Active Evac Flow</span>
                    <span className="text-sky-400 font-mono font-bold">{activeRoadFlow?.flow ?? 0} p/h</span>
                  </div>
                </div>

                {activeRoadFlow && (
                  <div className="bg-slate-950/80 p-3 rounded border border-slate-800">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Corridor Utilization</span>
                      <span className="font-mono font-bold text-sky-300">
                        {(activeRoadFlow.utilization_ratio * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full ${
                          activeRoadFlow.is_saturated
                            ? "bg-amber-500"
                            : activeRoadFlow.utilization_ratio > 0.75
                            ? "bg-sky-400"
                            : "bg-emerald-500"
                        }`}
                        style={{ width: `${Math.min(100, activeRoadFlow.utilization_ratio * 100)}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-500 mt-2">
                      <span>Residual Headroom:</span>
                      <span className="font-mono text-slate-300 font-medium">
                        {activeRoadFlow.remaining_capacity} p/h
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center text-slate-500">
                <MapPin className="w-8 h-8 text-slate-700 mb-2 stroke-1" />
                <p className="text-xs">Click any node or road on the canvas to inspect its capacity, flow, and incident metrics.</p>
              </div>
            )}
          </div>

          {/* Educational Dijkstra Shortest-Path Box */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" />
                <span>Shortest Path (Dijkstra)</span>
              </h4>
              {dijkstraResult && (
                <button onClick={handleClearRoute} className="text-[11px] text-slate-500 hover:text-slate-300">
                  Reset
                </button>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Computes single-vehicle minimum distance via binary min-heap (O((V+E) log V)).
            </p>

            <div className="space-y-2 mb-3">
              <div>
                <label className="text-[11px] text-slate-500 block mb-1">Origin Node:</label>
                <select
                  value={dijkstraSource}
                  onChange={(e) => setDijkstraSource(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  {affectedAreas.map((n) => (
                    <option key={n.node_id} value={n.node_id}>
                      {n.node_id} — {n.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] text-slate-500 block mb-1">Destination Shelter:</label>
                <select
                  value={dijkstraTarget}
                  onChange={(e) => setDijkstraTarget(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  {shelters.map((n) => (
                    <option key={n.node_id} value={n.node_id}>
                      {n.node_id} — {n.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleFindShortestPath}
              disabled={isFindingRoute || !dijkstraSource || !dijkstraTarget}
              className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-sky-500/30 rounded text-xs font-medium flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Compass className={`w-3.5 h-3.5 ${isFindingRoute ? "animate-spin" : ""}`} />
              <span>{isFindingRoute ? "Tracing Path..." : "Find Shortest Corridor"}</span>
            </button>

            {dijkstraResult?.shortest_route && (
              <div className="mt-3 p-2.5 bg-slate-950/80 rounded border border-sky-900/50 text-xs space-y-1.5">
                <div className="flex justify-between text-slate-300">
                  <span>Total Distance:</span>
                  <span className="font-mono font-bold text-sky-400">
                    {dijkstraResult.shortest_route.total_distance.toFixed(1)} km
                  </span>
                </div>
                <div className="flex justify-between text-slate-400 text-[11px]">
                  <span>Hops / Relaxes:</span>
                  <span className="font-mono">
                    {dijkstraResult.shortest_route.node_path.length - 1} hops ({dijkstraResult.relaxed_edges_count} relaxed)
                  </span>
                </div>
                <div className="pt-1 border-t border-slate-800 text-[11px] font-mono text-slate-300 truncate">
                  Path: {dijkstraResult.shortest_route.node_path.join(" → ")}
                </div>
                <p className="text-[10px] text-slate-500 italic mt-1">
                  Note: Dijkstra optimizes distance for 1 vehicle; Dinic optimizes network throughput for thousands.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
