import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../api/client";
import type { ScenarioEvaluationData } from "../types/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  GitCompare,
  Layers,
  Play,
  Sliders,
} from "lucide-react";

export const ScenarioLabPage: React.FC = () => {
  const { network, addNotification } = useApp();

  const [scenariosList, setScenariosList] = useState<ScenarioEvaluationData[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioEvaluationData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Custom scenario configuration
  const [customName, setCustomName] = useState("Custom Emergency Test");
  const [customMode, setCustomMode] = useState<"road_closure" | "reduced_shelter" | "increased_shelter">("road_closure");
  const [customRoadToClose, setCustomRoadToClose] = useState<string>("");
  const [customShelterToAdjust, setCustomShelterToAdjust] = useState<string>("");
  const [customShelterCapacity, setCustomShelterCapacity] = useState<number>(500);

  // Load all standard scenarios
  const handleRunAllScenarios = async () => {
    setIsLoading(true);
    try {
      const data = await api.runAllScenarios();
      setScenariosList(data.scenarios);
      if (data.scenarios.length > 0) {
        setSelectedScenario(data.scenarios[0]);
      }
      addNotification("success", "5 standard disaster scenarios calculated and compared.");
    } catch (err: any) {
      addNotification("error", `Scenario simulation failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Run on mount if no comparison data
  useEffect(() => {
    handleRunAllScenarios();
  }, [network]);

  // Set default custom selections
  useEffect(() => {
    if (network) {
      if (network.roads.length > 0 && !customRoadToClose) {
        setCustomRoadToClose(network.roads[0].road_id);
      }
      const shelterNodes = network.nodes.filter((n) => n.node_type === "shelter");
      if (shelterNodes.length > 0 && !customShelterToAdjust) {
        setCustomShelterToAdjust(shelterNodes[0].node_id);
        setCustomShelterCapacity(shelterNodes[0].shelter_capacity || 500);
      }
    }
  }, [network, customRoadToClose, customShelterToAdjust]);

  // Handle custom scenario execution
  const handleRunCustom = async () => {
    if (!customName.trim()) {
      addNotification("warning", "Enter a scenario name.");
      return;
    }
    setIsLoading(true);
    try {
      let result: ScenarioEvaluationData;
      if (customMode === "road_closure") {
        if (!customRoadToClose) {
          addNotification("warning", "Select a road to close.");
          setIsLoading(false);
          return;
        }
        result = await api.runRoadClosureScenario(customRoadToClose, customName);
      } else if (customMode === "reduced_shelter") {
        result = await api.runReducedShelterScenario(customShelterToAdjust, customShelterCapacity, customName);
      } else {
        result = await api.runIncreasedShelterScenario(customShelterToAdjust, customShelterCapacity, customName);
      }

      setScenariosList((prev) => [...prev, result]);
      setSelectedScenario(result);
      addNotification("success", `Custom scenario "${customName}" executed successfully.`);
    } catch (err: any) {
      addNotification("error", `Failed to run custom scenario: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Chart data
  const chartData = scenariosList.map((sc) => ({
    name: sc.scenario_name.replace("Scenario ", "S"),
    fullName: sc.scenario_name,
    maxFlow: sc.max_flow,
    delta: sc.baseline_delta,
    pctDelta: sc.baseline_delta_pct,
  }));

  const baselineFlow = scenariosList.length > 0 ? scenariosList[0].max_flow : 2250;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-sky-600" />
            Scenario Lab & What-If Disaster Stress Testing
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Simulate roadway closures, shelter flooding, and structural failures to assess evacuation resilience and bottleneck shifts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRunAllScenarios}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>{isLoading ? "Simulating..." : "Run 5 Standard Scenarios"}</span>
          </button>
        </div>
      </div>

      {/* Scenario Comparison Chart & Delta Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recharts Bar Chart (2/3 width) */}
        <div className="lg:col-span-2 bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <GitCompare className="w-4 h-4 text-sky-600" />
                Maximum Flow Comparison by Scenario (people / hr)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Baseline ({baselineFlow.toLocaleString()} p/h) vs degraded road & shelter states.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#e2e8f0",
                    borderRadius: "8px",
                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    fontSize: "12px",
                    color: "#0f172a",
                  }}
                  formatter={(value: any, _: any, item: any) => [
                    `${value.toLocaleString()} p/h (${item.payload.pctDelta >= 0 ? "+" : ""}${item.payload.pctDelta.toFixed(1)}%)`,
                    "Max Evac Flow",
                  ]}
                  labelFormatter={(name) => {
                    const found = chartData.find((d) => d.name === name);
                    return found ? found.fullName : name;
                  }}
                />
                <Bar dataKey="maxFlow" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => {
                    let color = "#0284c7"; // sky-600
                    if (entry.delta < 0) color = "#e11d48"; // rose-600 for drops
                    if (entry.delta > 0) color = "#059669"; // emerald-600 for gains
                    if (index === 0) color = "#2563eb"; // blue-600 for baseline
                    return <Cell key={`cell-${index}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Custom What-If Scenario Builder (1/3 width) */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 mb-1">
              <Sliders className="w-4 h-4 text-emerald-600" />
              Custom What-If Injection
            </h3>
            <p className="text-xs text-slate-500 mb-3">
              Apply specific road closures or shelter reductions in an isolated graph clone.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1">Scenario Label:</label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-sky-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1">Action Type:</label>
                <select
                  value={customMode}
                  onChange={(e) => setCustomMode(e.target.value as any)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-sky-500 focus:bg-white cursor-pointer"
                >
                  <option value="road_closure">Close Road Corridor</option>
                  <option value="reduced_shelter">Reduce Shelter Capacity</option>
                  <option value="increased_shelter">Expand Shelter Capacity</option>
                </select>
              </div>

              {customMode === "road_closure" ? (
                <div>
                  <label className="text-[11px] font-semibold text-slate-600 block mb-1">Select Road Corridor:</label>
                  <select
                    value={customRoadToClose}
                    onChange={(e) => setCustomRoadToClose(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-sky-500 font-mono focus:bg-white cursor-pointer"
                  >
                    {network &&
                      network.roads.map((r) => (
                        <option key={r.road_id} value={r.road_id}>
                          {r.road_id} ({r.name} — cap {r.capacity})
                        </option>
                      ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label className="text-[11px] font-semibold text-slate-600 block mb-1">Shelter & New Capacity:</label>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={customShelterToAdjust}
                      onChange={(e) => setCustomShelterToAdjust(e.target.value)}
                      className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-sky-500 font-mono focus:bg-white cursor-pointer"
                    >
                      {network &&
                        network.nodes
                          .filter((n) => n.node_type === "shelter")
                          .map((s) => (
                            <option key={s.node_id} value={s.node_id}>
                              {s.node_id} ({s.name})
                            </option>
                          ))}
                    </select>

                    <input
                      type="number"
                      min="0"
                      step="50"
                      placeholder="Capacity"
                      value={customShelterCapacity}
                      onChange={(e) => setCustomShelterCapacity(Number(e.target.value))}
                      className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs text-slate-800 font-mono focus:outline-none focus:border-sky-500 focus:bg-white"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={handleRunCustom}
            disabled={isLoading}
            className="w-full mt-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Execute Custom Simulation</span>
          </button>
        </div>
      </div>

      {/* Scenario Comparison Data Table */}
      <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-600" />
            Standard Disaster Scenarios Summary Matrix
          </h3>
          <span className="text-xs text-slate-500 font-mono">
            Baseline: {baselineFlow.toLocaleString()} p/h
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-3.5">Scenario Name</th>
                <th className="py-3 px-3">Description / Conditions</th>
                <th className="py-3 px-3 text-right">Max Flow</th>
                <th className="py-3 px-3 text-right">Flow Delta (Δ)</th>
                <th className="py-3 px-3 text-right">% Change</th>
                <th className="py-3 px-3 text-center">Bottlenecks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {scenariosList.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                    No scenarios calculated. Click "Run 5 Standard Scenarios" above.
                  </td>
                </tr>
              ) : (
                scenariosList.map((sc, idx) => {
                  const isBaseline = idx === 0;
                  const isNegative = sc.baseline_delta < 0;
                  const isPositive = sc.baseline_delta > 0;

                  return (
                    <tr
                      key={sc.scenario_name + idx}
                      onClick={() => setSelectedScenario(sc)}
                      className={`hover:bg-slate-50/70 cursor-pointer transition-colors ${
                        selectedScenario?.scenario_name === sc.scenario_name ? "bg-sky-50/70 font-semibold" : ""
                      }`}
                    >
                      <td className="py-3 px-3.5 font-sans">
                        <span className="font-bold text-slate-900 block">{sc.scenario_name}</span>
                        {isBaseline && (
                          <span className="text-[10px] text-sky-700 bg-sky-50 px-1.5 py-0.2 rounded font-mono font-medium border border-sky-200">
                            [REFERENCE BASELINE]
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-3 font-sans text-slate-600 max-w-xs truncate" title={sc.description}>
                        {sc.description}
                      </td>

                      <td className="py-3 px-3 text-right font-bold text-slate-800">
                        {sc.max_flow.toLocaleString()} <span className="text-[10px] text-slate-400 font-normal">p/h</span>
                      </td>

                      <td className="py-3 px-3 text-right">
                        {isBaseline ? (
                          <span className="text-slate-400">0</span>
                        ) : isNegative ? (
                          <span className="text-rose-600 font-bold flex items-center justify-end gap-1">
                            <ArrowDownRight className="w-3.5 h-3.5" />
                            {sc.baseline_delta.toLocaleString()}
                          </span>
                        ) : isPositive ? (
                          <span className="text-emerald-600 font-bold flex items-center justify-end gap-1">
                            <ArrowUpRight className="w-3.5 h-3.5" />
                            +{sc.baseline_delta.toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-right">
                        {isBaseline ? (
                          <span className="text-slate-400">0.0%</span>
                        ) : (
                          <span
                            className={`font-bold ${
                              isNegative ? "text-rose-600" : isPositive ? "text-emerald-600" : "text-slate-400"
                            }`}
                          >
                            {isPositive ? "+" : ""}
                            {sc.baseline_delta_pct.toFixed(1)}%
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-center font-sans">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 border border-slate-200 text-slate-700">
                          {sc.bottleneck_roads_count} cuts
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
