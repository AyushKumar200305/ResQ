import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Compass,
  FileCheck,
  HelpCircle,
  MapPin,
  RefreshCw,
  Route as RouteIcon,
  ShieldAlert,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import { api } from "../api/client";
import { NetworkGraph } from "../components/graph/NetworkGraph";
import { useApp } from "../context/AppContext";

export const RoutesAndSheltersPage: React.FC = () => {
  const { network, reliefOverview, isReliefLoading, refreshRelief, refreshNetwork, addNotification } = useApp();

  const routes = reliefOverview?.routes || [];
  const affectedAreas = network?.nodes.filter((n) => n.node_type === "affected_area") || [];
  const shelters = network?.nodes.filter((n) => n.node_type === "shelter") || [];

  // Default selection: A1 and S1
  const [selectedSource, setSelectedSource] = useState<string>("A1");
  const [selectedShelter, setSelectedShelter] = useState<string>("S1");
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  // Find matching route recommendation
  const currentRecommendation = useMemo(() => {
    return routes.find(
      (r) => r.source_id === selectedSource && r.shelter_id === selectedShelter && r.is_primary
    );
  }, [routes, selectedSource, selectedShelter]);

  const alternativeRecommendation = useMemo(() => {
    return routes.find(
      (r) => r.source_id === selectedSource && r.shelter_id === selectedShelter && !r.is_primary
    );
  }, [routes, selectedSource, selectedShelter]);

  const primaryRoadIds = currentRecommendation?.road_ids || [];
  const altRoadIds = alternativeRecommendation?.road_ids || [];

  // Handler for scout verification of road condition
  const handleVerifyRoad = async (roadId: string, newStatus: string) => {
    try {
      setIsVerifying(true);
      await api.verifyRoadStatus({
        road_id: roadId,
        new_status: newStatus,
        hazard_risk_score: newStatus === "verified_clear" ? 0.05 : 0.8,
        verification_notes: `Field scout inspected ${roadId}; marked ${newStatus.replace(/_/g, " ")}.`,
      });
      await Promise.all([refreshNetwork(), refreshRelief()]);
      addNotification("success", `Corridor ${roadId} updated to ${newStatus.replace(/_/g, " ")}.`);
    } catch (err: any) {
      addNotification("error", `Failed to update road status: ${err.message}`);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 shrink-0 mt-0.5 shadow-xs">
            <Compass className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Evacuation Routes &amp; Shelters Map</h1>
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                SHORTEST-PATH DIJKSTRA
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Real-time corridor mapping: recommended primary paths, alternative detours, closed or flood-damaged segments, and shelter destinations.
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            refreshNetwork();
            refreshRelief();
          }}
          disabled={isReliefLoading}
          className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-2 transition-all shrink-0 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isReliefLoading ? "animate-spin text-blue-600" : "text-slate-500"}`} />
          <span>Refresh Map</span>
        </button>
      </div>

      {/* Map Legend */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
        <div className="flex items-center gap-2 font-bold text-slate-700 uppercase tracking-wider text-[11px]">
          <MapPin className="w-4 h-4 text-blue-600" />
          <span>Map Legend:</span>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-[11px]">
          {/* Affected Area */}
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-600 border border-red-700" />
            <span className="text-slate-700 font-medium">Affected Area</span>
          </div>

          {/* Junction */}
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-blue-600 border border-blue-700" />
            <span className="text-slate-700 font-medium">Junction</span>
          </div>

          {/* Shelter */}
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-600 border border-emerald-700" />
            <span className="text-slate-700 font-medium">Shelter</span>
          </div>

          <div className="h-4 w-px bg-slate-200 hidden sm:block" />

          {/* Recommended Route */}
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-1.5 bg-emerald-600 rounded-full" />
            <span className="text-emerald-800 font-bold">Recommended Primary</span>
          </div>

          {/* Alternative Route */}
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-1.5 bg-blue-500 border-b border-dashed border-blue-600 rounded-full" />
            <span className="text-blue-700 font-bold">Alternative Detour</span>
          </div>

          {/* Hazard Avoidance */}
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-1.5 bg-red-600 rounded-full" />
            <span className="text-red-700 font-bold">Hazard Avoid</span>
          </div>

          {/* Unverified */}
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-1.5 bg-amber-500 border-b border-dashed border-amber-600 rounded-full" />
            <span className="text-amber-800 font-bold">Scout Required</span>
          </div>

          {/* Closed / Damaged */}
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-1.5 bg-slate-400 border-b border-dashed border-slate-500 rounded-full" />
            <span className="text-slate-600 font-bold">Closed / Damaged</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Interactive Canvas & Route Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Interactive Graph Canvas */}
        <div className="lg:col-span-2 space-y-3">
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
            <NetworkGraph
              heightClass="h-[560px]"
              primaryRouteRoads={primaryRoadIds}
              alternativeRouteRoads={altRoadIds}
            />
          </div>

          <div className="p-3.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-500 flex items-center justify-between shadow-xs">
            <span>Click and drag nodes to inspect topology. Use mouse wheel to zoom.</span>
            <span className="font-mono text-[11px] font-bold text-blue-700">
              Active Corridor: {selectedSource} &rarr; {selectedShelter}
            </span>
          </div>
        </div>

        {/* Right Col: Route Selector & Explanation */}
        <div className="space-y-4">
          {/* Corridor Selection Box */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Sliders className="w-4 h-4 text-blue-600" />
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Select Evacuation Corridor</h2>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                  Origin (Affected Area):
                </label>
                <select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                >
                  {affectedAreas.map((a) => (
                    <option key={a.node_id} value={a.node_id}>
                      {a.name} ({a.node_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                  Destination (Shelter):
                </label>
                <select
                  value={selectedShelter}
                  onChange={(e) => setSelectedShelter(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                >
                  {shelters.map((s) => (
                    <option key={s.node_id} value={s.node_id}>
                      {s.name} ({s.node_id})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Primary Route Card */}
          {currentRecommendation ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <RouteIcon className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Recommended Primary Path</h3>
                </div>
                <span
                  className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                    currentRecommendation.operational_advisory === "RECOMMENDED"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : currentRecommendation.operational_advisory === "UNVERIFIED_SCOUT_REQUIRED"
                      ? "bg-amber-50 text-amber-800 border-amber-200"
                      : "bg-red-50 text-red-700 border-red-200"
                  }`}
                >
                  {currentRecommendation.operational_advisory.replace(/_/g, " ")}
                </span>
              </div>

              {/* Waypoint Path Sequence */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-[10px] font-semibold text-slate-500 mb-1.5 uppercase tracking-wide">Turn-by-turn Waypoints:</div>
                <div className="flex items-center gap-1.5 flex-wrap font-mono text-xs">
                  {currentRecommendation.node_path.map((node, i) => (
                    <React.Fragment key={node}>
                      <span className="px-2 py-0.5 rounded bg-white text-slate-900 border border-slate-200 font-bold shadow-xs">
                        {node}
                      </span>
                      {i < currentRecommendation.node_path.length - 1 && (
                        <span className="text-slate-400 font-bold">&rarr;</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Distance</span>
                  <span className="font-bold text-slate-900">{currentRecommendation.total_distance_km} km</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Transit Time</span>
                  <span className="font-bold text-slate-900">{currentRecommendation.total_travel_time_min} min</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Chokepoint</span>
                  <span className="font-bold text-blue-700">{currentRecommendation.bottleneck_capacity.toLocaleString()} p/h</span>
                </div>
              </div>

              {/* Why is this route recommended? */}
              <div className="p-3.5 rounded-xl bg-blue-50/60 border border-blue-100 text-xs space-y-1">
                <div className="flex items-center gap-1.5 text-blue-700 font-bold text-[11px]">
                  <HelpCircle className="w-3.5 h-3.5" />
                  <span>Why this corridor?</span>
                </div>
                <p className="text-slate-700 leading-relaxed">{currentRecommendation.recommendation_notes}</p>
              </div>

              {/* Unverified Scout Action (if unverified roads exist on this route) */}
              {currentRecommendation.has_unverified_roads && (
                <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 text-xs space-y-2.5">
                  <div className="flex items-center gap-1.5 text-amber-900 font-bold text-[11px]">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                    <span>Scout Verification Required</span>
                  </div>
                  <p className="text-slate-700 text-[11px]">
                    Unconfirmed reports on road segment:{" "}
                    <strong className="text-slate-900">{currentRecommendation.unverified_road_ids.join(", ")}</strong>.
                  </p>
                  <button
                    onClick={() => handleVerifyRoad(currentRecommendation.unverified_road_ids[0], "verified_clear")}
                    disabled={isVerifying}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-xs"
                  >
                    <FileCheck className="w-3.5 h-3.5" />
                    <span>Confirm Verified Clear (Field Scout)</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-6 bg-white border border-slate-200 rounded-2xl text-center text-xs text-slate-500 shadow-xs">
              No direct path found between {selectedSource} and {selectedShelter}.
            </div>
          )}

          {/* Alternative Route Card (if available) */}
          {alternativeRecommendation && (
            <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-3 shadow-xs">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-1.5 text-xs font-bold text-blue-700 uppercase tracking-wider">
                  <RouteIcon className="w-3.5 h-3.5" />
                  <span>Alternative Detour</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500 font-medium">
                  +{((alternativeRecommendation.total_distance_km - (currentRecommendation?.total_distance_km || 0))).toFixed(1)} km
                </span>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap font-mono text-xs text-slate-700">
                {alternativeRecommendation.node_path.map((node, i) => (
                  <React.Fragment key={node}>
                    <span className="px-2 py-0.5 rounded bg-slate-50 text-slate-800 border border-slate-200 text-[11px] font-bold">
                      {node}
                    </span>
                    {i < alternativeRecommendation.node_path.length - 1 && (
                      <span className="text-slate-400 font-bold">&rarr;</span>
                    )}
                  </React.Fragment>
                ))}
              </div>

              <p className="text-[11px] text-slate-600 leading-snug">
                {alternativeRecommendation.recommendation_notes}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};