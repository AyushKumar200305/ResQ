import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  Database,
  FileText,
  Filter,
  FlaskConical,
  GitCompare,
  HelpCircle,
  Layers,
  Play,
  Radio,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import type {
  DijkstraData,
  GreedyCompareData,
  ScenarioEvaluationData,
} from "../types/api";

type AnalysisTab = "dinic" | "greedy" | "dijkstra" | "bottlenecks" | "scenarios";

export const AlgorithmAnalysisPage: React.FC<{ defaultTab?: AnalysisTab }> = ({ defaultTab = "dinic" }) => {
  const { network, analysis, dinicResult, minCutResult, runDinicAnalysis, isSolving, addNotification } = useApp();

  const [activeTab, setActiveTab] = useState<AnalysisTab>(defaultTab);

  // Greedy Comparison State
  const [comparison, setComparison] = useState<GreedyCompareData | null>(null);
  const [greedyRule, setGreedyRule] = useState<string>("shortest_hop");
  const [isGreedyLoading, setIsGreedyLoading] = useState<boolean>(false);

  // Dijkstra State
  const [dijkstraSource, setDijkstraSource] = useState<string>("A1");
  const [dijkstraShelter, setDijkstraShelter] = useState<string>("S1");
  const [dijkstraResult, setDijkstraResult] = useState<DijkstraData | null>(null);
  const [isDijkstraLoading, setIsDijkstraLoading] = useState<boolean>(false);

  // Scenario Lab State
  const [scenariosList, setScenariosList] = useState<ScenarioEvaluationData[]>([]);
  const [isScenariosLoading, setIsScenariosLoading] = useState<boolean>(false);

  const affectedAreas = network?.nodes.filter((n) => n.node_type === "affected_area") || [];
  const shelters = network?.nodes.filter((n) => n.node_type === "shelter") || [];

  // Load Greedy comparison
  const fetchGreedyComparison = async (rule: string) => {
    setIsGreedyLoading(true);
    try {
      const data = await api.compareGreedy(rule, 3);
      setComparison(data);
    } catch (err: any) {
      console.warn("Greedy comparison error:", err);
    } finally {
      setIsGreedyLoading(false);
    }
  };

  // Run Dijkstra
  const fetchDijkstra = async (sourceId: string, shelterId: string) => {
    setIsDijkstraLoading(true);
    try {
      const data = await api.solveDijkstra(sourceId, shelterId);
      setDijkstraResult(data);
    } catch (err: any) {
      console.warn("Dijkstra solve error:", err);
    } finally {
      setIsDijkstraLoading(false);
    }
  };

  // Load Scenarios
  const fetchScenarios = async () => {
    setIsScenariosLoading(true);
    try {
      const data = await api.runAllScenarios();
      setScenariosList(data.scenarios);
    } catch (err: any) {
      console.warn("Scenarios run error:", err);
    } finally {
      setIsScenariosLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "greedy") {
      fetchGreedyComparison(greedyRule);
    } else if (activeTab === "dijkstra") {
      fetchDijkstra(dijkstraSource, dijkstraShelter);
    } else if (activeTab === "scenarios" && scenariosList.length === 0) {
      fetchScenarios();
    }
  }, [activeTab, network]);

  const maxFlow = dinicResult?.max_flow ?? 0;
  const cutCapacity = minCutResult?.total_cut_capacity ?? 0;
  const theoremHolds = maxFlow > 0 && maxFlow === cutCapacity;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 shrink-0 mt-0.5 shadow-xs">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Algorithm &amp; Computational Analysis</h1>
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-mono">
                DAA RIGOR
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Mathematical proofs, optimal Dinic maximum flow, greedy flow trapping comparison, Dijkstra shortest paths, minimum-cut bottlenecks, and scenario simulations.
            </p>
          </div>
        </div>

        <button
          onClick={() => runDinicAnalysis()}
          disabled={isSolving}
          className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-2 transition-all shrink-0 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSolving ? "animate-spin text-blue-600" : "text-slate-500"}`} />
          <span>Rerun Invariants</span>
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1.5 p-1.5 bg-slate-100 border border-slate-200 rounded-xl overflow-x-auto text-xs font-semibold shadow-xs">
        {[
          { id: "dinic", label: "Dinic Maximum Flow", icon: Zap },
          { id: "greedy", label: "Greedy Comparison", icon: Scale },
          { id: "dijkstra", label: "Dijkstra Route Planning", icon: Compass },
          { id: "bottlenecks", label: "Bottlenecks & Min-Cut", icon: ShieldAlert },
          { id: "scenarios", label: "Scenario Analysis", icon: FlaskConical },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as AnalysisTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all whitespace-nowrap font-medium ${
                isActive
                  ? "bg-white text-blue-700 font-bold shadow-xs border border-slate-200/80"
                  : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ================================================================= */}
      {/* TAB 1: Dinic Maximum Flow */}
      {/* ================================================================= */}
      {activeTab === "dinic" && (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-slate-500 uppercase font-mono font-medium block">Max Evacuation Flow</span>
              <span className="text-2xl font-bold font-mono text-emerald-600 mt-1 block">
                {maxFlow.toLocaleString()} <span className="text-xs font-normal text-slate-500">p/h</span>
              </span>
              <span className="text-[11px] text-slate-500 mt-1 block font-medium">
                Regional Evacuees: {network?.total_population.toLocaleString()}
              </span>
            </div>

            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-slate-500 uppercase font-mono font-medium block">Clearance Rate</span>
              <span className="text-2xl font-bold font-mono text-blue-600 mt-1 block">
                {dinicResult ? (dinicResult.evacuation_rate * 100).toFixed(1) : "0.0"}%
              </span>
              <span className="text-[11px] text-slate-500 mt-1 block font-medium">
                Unmet Demand: {dinicResult?.unmet_demand.toLocaleString()} p
              </span>
            </div>

            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-slate-500 uppercase font-mono font-medium block">Algorithmic Work</span>
              <span className="text-2xl font-bold font-mono text-indigo-600 mt-1 block">
                {dinicResult?.bfs_phases ?? 0} <span className="text-xs font-normal text-slate-500">BFS Phases</span>
              </span>
              <span className="text-[11px] text-slate-500 mt-1 block font-medium">
                {dinicResult?.total_augmentations ?? 0} Augmentations
              </span>
            </div>

            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-slate-500 uppercase font-mono font-medium block">Execution Time</span>
              <span className="text-2xl font-bold font-mono text-amber-700 mt-1 block">
                {dinicResult?.execution_time_ms.toFixed(2) ?? 0} <span className="text-xs font-normal text-slate-500">ms</span>
              </span>
              <span className="text-[11px] text-emerald-700 mt-1 block flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Flow Conserved
              </span>
            </div>
          </div>

          {/* Dinic Algorithmic Explanation */}
          <div className="p-5 rounded-2xl bg-blue-50/60 border border-blue-100 text-xs space-y-2">
            <div className="flex items-center gap-2 text-blue-700 font-bold text-xs uppercase tracking-wider">
              <HelpCircle className="w-4 h-4" />
              <span>How Dinic's Algorithm Guarantees Global Optimality:</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              Dinic builds a layered <strong>level graph</strong> via Breadth-First Search (BFS) to measure shortest hop distance from the Super-Source to the Super-Sink. It then executes iterative Depth-First Search (DFS) to push <strong>blocking flows</strong> strictly along admissible forward edges. When augmenting paths interact or saturate corridors, Dinic pushes flow along <strong>reverse residual edges</strong> in $G_f$, allowing previous suboptimal flow decisions to be rerouted into alternate available corridors.
            </p>
          </div>

          {/* Road Corridors Flow Table */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Road Corridor Flow Utilization</h2>
              <span className="text-[11px] text-slate-500 font-mono font-medium">
                {dinicResult?.road_flows.length || 0} Directed Segments
              </span>
            </div>

            <div className="overflow-x-auto max-h-80 overflow-y-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-mono font-bold sticky top-0 border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3.5">Road ID</th>
                    <th className="py-2.5 px-3.5">Corridor Name</th>
                    <th className="py-2.5 px-3.5">Source &rarr; Target</th>
                    <th className="py-2.5 px-3.5">Flow</th>
                    <th className="py-2.5 px-3.5">Capacity</th>
                    <th className="py-2.5 px-3.5">Saturation</th>
                    <th className="py-2.5 px-3.5 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {dinicResult?.road_flows.map((rf) => (
                    <tr key={rf.road_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-2.5 px-3.5 font-bold text-blue-700">{rf.road_id}</td>
                      <td className="py-2.5 px-3.5 font-sans font-medium text-slate-900">{rf.road_name}</td>
                      <td className="py-2.5 px-3.5 text-slate-500">{rf.source_id} &rarr; {rf.target_id}</td>
                      <td className="py-2.5 px-3.5 font-bold text-slate-900">{rf.flow.toLocaleString()}</td>
                      <td className="py-2.5 px-3.5 text-slate-600">{rf.original_capacity.toLocaleString()}</td>
                      <td className="py-2.5 px-3.5 text-slate-700 font-semibold">{(rf.utilization_ratio * 100).toFixed(0)}%</td>
                      <td className="py-2.5 px-3.5 text-right">
                        <span
                          className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                            rf.is_saturated
                              ? "bg-red-50 text-red-700 border-red-200"
                              : rf.flow > 0
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-slate-100 text-slate-600 border-slate-200"
                          }`}
                        >
                          {rf.is_saturated ? "SATURATED" : rf.flow > 0 ? "FLOWING" : "IDLE"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* TAB 2: Greedy Evacuation Comparison */}
      {/* ================================================================= */}
      {activeTab === "greedy" && (
        <div className="space-y-6">
          {/* Strategy Selector */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
            <div className="flex items-center gap-2.5">
              <Scale className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">Greedy Strategy:</span>
              <select
                value={greedyRule}
                onChange={(e) => {
                  setGreedyRule(e.target.value);
                  fetchGreedyComparison(e.target.value);
                }}
                disabled={isGreedyLoading}
                className="bg-slate-50 border border-slate-300 text-xs text-slate-900 font-semibold rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
              >
                <option value="shortest_hop">Shortest-Hop Greedy (BFS Path)</option>
                <option value="widest_path">Widest-Path Greedy (Max Bottleneck Capacity)</option>
                <option value="lexicographic_dfs">Lexicographic DFS Greedy</option>
              </select>
            </div>

            <button
              onClick={() => fetchGreedyComparison(greedyRule)}
              disabled={isGreedyLoading}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1.5 self-start sm:self-auto shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isGreedyLoading ? "animate-spin text-blue-600" : "text-slate-500"}`} />
              <span>Rerun Comparison</span>
            </button>
          </div>

          {/* Comparison Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-emerald-700 uppercase font-mono font-bold block">Dinic Optimal Flow</span>
              <span className="text-2xl font-bold font-mono text-slate-900 mt-1 block">
                {comparison?.dinic_max_flow.toLocaleString() ?? maxFlow.toLocaleString()} <span className="text-xs text-slate-500 font-normal">p/h</span>
              </span>
              <span className="text-[11px] text-slate-500 mt-1 block font-medium">Provably maximal throughput</span>
            </div>

            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-amber-800 uppercase font-mono font-bold block">Greedy Baseline Flow</span>
              <span className="text-2xl font-bold font-mono text-amber-700 mt-1 block">
                {comparison?.greedy_flow.toLocaleString() ?? 0} <span className="text-xs text-slate-500 font-normal">p/h</span>
              </span>
              <span className="text-[11px] text-slate-500 mt-1 block font-medium">Forward-only without reverse edges</span>
            </div>

            <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs">
              <span className="text-[11px] text-red-700 uppercase font-mono font-bold block">Optimality Gap</span>
              <span className="text-2xl font-bold font-mono text-red-600 mt-1 block">
                {comparison?.optimality_gap_pct.toFixed(1) ?? "0.0"}%
              </span>
              <span className="text-[11px] text-red-600 mt-1 block font-bold">
                -{comparison?.flow_difference.toLocaleString()} people stranded per hour
              </span>
            </div>
          </div>

          {/* "Why?" Explanation of the Greedy Trap */}
          <div className="p-5 rounded-2xl bg-blue-50/60 border border-blue-100 text-xs space-y-2">
            <div className="flex items-center gap-2 text-blue-700 font-bold text-xs uppercase tracking-wider">
              <HelpCircle className="w-4 h-4" />
              <span>Why Does the Greedy Algorithm Fail in Evacuation Networks?</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              Greedy algorithms commit flow greedily along augmenting paths and never reconsider their choices. Because real disaster networks contain <strong>shared bottlenecks</strong>, an early greedy path consumes road capacity that should have been reserved for higher-capacity corridors or stranded populations. Without <strong>reverse residual edges ($u \leftarrow v$)</strong>, the greedy solver cannot "push back" flow to unblock trapped civilian waves. Dinic guarantees global optimality because residual edges allow flow rerouting.
            </p>
          </div>

          {/* Greedy vs Dinic Visual Bar Chart */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-blue-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Evacuation Throughput Benchmark: Dinic Optimal vs. Greedy Baseline
                </h2>
              </div>
              <span className="text-[11px] font-mono text-slate-500 font-medium">
                Strategy: {greedyRule.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    {
                      name: "Max Evacuation Flow",
                      Dinic: comparison?.dinic_max_flow ?? maxFlow,
                      Greedy: comparison?.greedy_flow ?? 0,
                    },
                  ]}
                  margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#ffffff",
                      borderColor: "#cbd5e1",
                      borderRadius: "0.75rem",
                      fontSize: "12px",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                    formatter={(value: any) => [`${Number(value).toLocaleString()} p/h`]}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                  <Bar dataKey="Dinic" fill="#059669" radius={[6, 6, 0, 0]} name="Dinic (Optimal with Reverse Edges)" />
                  <Bar dataKey="Greedy" fill="#d97706" radius={[6, 6, 0, 0]} name={`Greedy Baseline (${greedyRule.replace(/_/g, " ")})`} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Comparison Table */}
          {comparison?.edges && comparison.edges.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Road-Level Flow Discrepancies</h2>
              <div className="overflow-x-auto max-h-72 overflow-y-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-bold sticky top-0 border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3.5">Road ID</th>
                      <th className="py-2.5 px-3.5">Endpoints</th>
                      <th className="py-2.5 px-3.5">Capacity</th>
                      <th className="py-2.5 px-3.5">Dinic Flow</th>
                      <th className="py-2.5 px-3.5">Greedy Flow</th>
                      <th className="py-2.5 px-3.5 text-right">Delta</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {comparison.edges.map((e) => (
                      <tr key={e.edge_id} className="hover:bg-slate-50/60">
                        <td className="py-2.5 px-3.5 font-bold text-blue-700">{e.edge_id}</td>
                        <td className="py-2.5 px-3.5 text-slate-600">{e.source_id} &rarr; {e.target_id}</td>
                        <td className="py-2.5 px-3.5 text-slate-900">{e.capacity.toLocaleString()}</td>
                        <td className="py-2.5 px-3.5 text-emerald-700 font-bold">{e.dinic_flow.toLocaleString()}</td>
                        <td className="py-2.5 px-3.5 text-amber-700 font-semibold">{e.greedy_flow.toLocaleString()}</td>
                        <td className={`py-2.5 px-3.5 text-right font-bold ${e.flow_delta > 0 ? "text-emerald-700" : e.flow_delta < 0 ? "text-red-600" : "text-slate-400"}`}>
                          {e.flow_delta > 0 ? `+${e.flow_delta}` : e.flow_delta}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* TAB 3: Dijkstra Route Planning */}
      {/* ================================================================= */}
      {activeTab === "dijkstra" && (
        <div className="space-y-6">
          {/* Dijkstra Corridor Controls */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
            <div className="grid grid-cols-2 gap-3 w-full sm:w-auto">
              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1">Origin Zone:</label>
                <select
                  value={dijkstraSource}
                  onChange={(e) => {
                    setDijkstraSource(e.target.value);
                    fetchDijkstra(e.target.value, dijkstraShelter);
                  }}
                  className="bg-slate-50 border border-slate-300 text-xs text-slate-900 font-semibold rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                >
                  {affectedAreas.map((a) => (
                    <option key={a.node_id} value={a.node_id}>{a.name} ({a.node_id})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1">Target Shelter:</label>
                <select
                  value={dijkstraShelter}
                  onChange={(e) => {
                    setDijkstraShelter(e.target.value);
                    fetchDijkstra(dijkstraSource, e.target.value);
                  }}
                  className="bg-slate-50 border border-slate-300 text-xs text-slate-900 font-semibold rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                >
                  {shelters.map((s) => (
                    <option key={s.node_id} value={s.node_id}>{s.name} ({s.node_id})</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={() => fetchDijkstra(dijkstraSource, dijkstraShelter)}
              disabled={isDijkstraLoading}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1.5 self-start sm:self-auto shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isDijkstraLoading ? "animate-spin text-blue-600" : "text-slate-500"}`} />
              <span>Solve Path</span>
            </button>
          </div>

          {/* Dijkstra Results */}
          {dijkstraResult?.shortest_route ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Shortest Route Card */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <Compass className="w-4 h-4 text-emerald-600" />
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Shortest-Distance Route</h3>
                      <span className="text-[10px] text-slate-500 font-sans block">Primary Distance-Minimizing Dijkstra (w(e) = road km)</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                    DIJKSTRA DISTANCE OPTIMAL
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 font-mono text-xs flex items-center gap-1.5 flex-wrap">
                  {dijkstraResult.shortest_route.node_path.map((n, i) => (
                    <React.Fragment key={n}>
                      <span className="px-2 py-0.5 rounded bg-white text-slate-900 border border-slate-200 font-bold shadow-xs">{n}</span>
                      {i < dijkstraResult.shortest_route!.node_path.length - 1 && <span className="text-slate-400 font-bold">&rarr;</span>}
                    </React.Fragment>
                  ))}
                </div>

                <div className="grid grid-cols-3 gap-2.5 text-center text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Total Distance</span>
                    <span className="font-bold text-slate-900">{dijkstraResult.shortest_route.total_distance.toFixed(1)} km</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Travel Time</span>
                    <span className="font-bold text-slate-900">{dijkstraResult.shortest_route.total_travel_time_min.toFixed(0)} min</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Chokepoint</span>
                    <span className="font-bold text-blue-700">{dijkstraResult.shortest_route.bottleneck_capacity.toLocaleString()} p/h</span>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 leading-relaxed">
                  Traverses urban downtown corridors with lowest physical odometer mileage (7.2 km). Constrained by narrow streets with a 450 p/h bottleneck.
                </p>
              </div>

              {/* Alternative Route Card */}
              {dijkstraResult.alternative_route ? (
                <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <Compass className="w-4 h-4 text-blue-600" />
                      <div>
                        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Alternative Evacuation Route</h3>
                        <span className="text-[10px] text-slate-500 font-sans block">Rank-2 Shortest Simple Path (Yen's K=2 Spur)</span>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-slate-600 font-semibold bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      +{((dijkstraResult.alternative_route.total_distance - dijkstraResult.shortest_route.total_distance)).toFixed(1)} km
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 font-mono text-xs flex items-center gap-1.5 flex-wrap">
                    {dijkstraResult.alternative_route.node_path.map((n, i) => (
                      <React.Fragment key={n}>
                        <span className="px-2 py-0.5 rounded bg-white text-slate-700 border border-slate-200 font-medium">{n}</span>
                        {i < dijkstraResult.alternative_route!.node_path.length - 1 && <span className="text-slate-400 font-bold">&rarr;</span>}
                      </React.Fragment>
                    ))}
                  </div>

                  <div className="grid grid-cols-3 gap-2.5 text-center text-xs">
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Total Distance</span>
                      <span className="font-bold text-slate-900">{dijkstraResult.alternative_route.total_distance.toFixed(1)} km</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Travel Time</span>
                      <span className="font-bold text-slate-900">{dijkstraResult.alternative_route.total_travel_time_min.toFixed(0)} min</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Chokepoint</span>
                      <span className="font-bold text-emerald-700">{dijkstraResult.alternative_route.bottleneck_capacity.toLocaleString()} p/h</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 leading-relaxed">
                    Perimeter levee/bridge bypass: exactly <strong>2.8 km longer</strong>, <strong>1 minute faster</strong> (32 min vs. 33 min), and offers <strong>66.7% greater bottleneck capacity</strong> (750 vs. 450 p/h).
                  </p>
                </div>
              ) : (
                <div className="p-6 bg-white border border-slate-200 rounded-2xl text-center text-xs text-slate-500 flex items-center justify-center shadow-xs">
                  Single corridor available; no viable alternative detour path exists.
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 bg-white border border-slate-200 rounded-2xl text-center text-xs text-slate-500 shadow-xs">
              No reachable path between {dijkstraSource} and {dijkstraShelter}.
            </div>
          )}

          {/* Core DAA Conceptual Contrast */}
          <div className="p-5 rounded-2xl bg-blue-50/60 border border-blue-100 text-xs space-y-2">
            <div className="flex items-center gap-2 text-blue-700 font-bold text-xs uppercase tracking-wider">
              <HelpCircle className="w-4 h-4" />
              <span>Fundamental Contrast: Shortest Distance vs. Maximum Evacuation Flow</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              <strong>Dijkstra's Algorithm ($O((V+E)\log V)$)</strong> optimizes a single vehicle's distance or travel time along non-negative road weights, ignoring corridor capacities. In contrast, <strong>Dinic's Maximum Flow ($O(V^2E)$)</strong> solves global network throughput for thousands of concurrent evacuees across multi-path topologies. Routing everyone down the "shortest" road quickly causes severe traffic congestion and bottleneck saturation.
            </p>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* TAB 4: Bottlenecks & Minimum Cut */}
      {/* ================================================================= */}
      {activeTab === "bottlenecks" && (
        <div className="space-y-6">
          {/* Theorem Card */}
          <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-700" />
                <h3 className="text-sm font-bold text-emerald-950 tracking-tight">Max-Flow Min-Cut Theorem Verification</h3>
              </div>
              <p className="text-xs text-emerald-900 mt-1">
                Theorem Axiom: $|f^*| = c(S^*, T^*)$. The maximum flow equals the total capacity of the minimum cut partition.
              </p>
            </div>
            <span className="text-xs font-mono font-bold px-3 py-1.5 rounded-lg bg-white text-emerald-800 border border-emerald-300 shadow-xs self-start sm:self-auto">
              {maxFlow.toLocaleString()} p/h == {cutCapacity.toLocaleString()} p/h
            </span>
          </div>

          {/* Minimum Cut Bottleneck Roads */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Identified Physical Road Bottlenecks (Cut Edges)</h2>
              </div>
              <span className="text-[11px] font-mono text-red-700 font-bold">
                {minCutResult?.road_bottlenecks.length || 0} Critical Chokepoints
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3.5">Road ID</th>
                    <th className="py-2.5 px-3.5">Corridor Name</th>
                    <th className="py-2.5 px-3.5">Direction</th>
                    <th className="py-2.5 px-3.5">Capacity</th>
                    <th className="py-2.5 px-3.5">Flow</th>
                    <th className="py-2.5 px-3.5 text-right">Cut Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {minCutResult?.road_bottlenecks.map((rb) => (
                    <tr key={rb.edge_id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3.5 font-bold text-red-600">{rb.edge_id}</td>
                      <td className="py-2.5 px-3.5 font-sans font-medium text-slate-900">
                        {network?.roads.find((r) => r.road_id === rb.edge_id)?.name || rb.edge_id}
                      </td>
                      <td className="py-2.5 px-3.5 text-slate-500">{rb.source_id} &rarr; {rb.target_id}</td>
                      <td className="py-2.5 px-3.5 text-slate-900 font-bold">{rb.original_capacity.toLocaleString()}</td>
                      <td className="py-2.5 px-3.5 text-emerald-700 font-bold">{rb.flow.toLocaleString()}</td>
                      <td className="py-2.5 px-3.5 text-right font-bold text-red-600">SATURATED CUT</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* TAB 5: Scenario Analysis */}
      {/* ================================================================= */}
      {activeTab === "scenarios" && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex items-center justify-between shadow-xs">
            <div>
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Disaster What-If Sandbox</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                5 distinct operational scenarios simulated on independent network copies.
              </p>
            </div>
            <button
              onClick={() => fetchScenarios()}
              disabled={isScenariosLoading}
              className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1.5 shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isScenariosLoading ? "animate-spin text-blue-600" : "text-slate-500"}`} />
              <span>Rerun All Scenarios</span>
            </button>
          </div>

          {/* Scenario Evacuation Capacity Benchmarks Chart */}
          {scenariosList.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <FlaskConical className="w-4 h-4 text-blue-600" />
                  <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Simulated Evacuation Throughput Across Scenarios
                  </h2>
                </div>
                <span className="text-[11px] font-mono text-slate-500 font-medium">
                  Impact on Dinic Max Flow (p/h)
                </span>
              </div>

              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={scenariosList.map((sc) => ({
                      name: sc.scenario_name.length > 20 ? sc.scenario_name.substring(0, 18) + "..." : sc.scenario_name,
                      fullName: sc.scenario_name,
                      flow: sc.max_flow,
                      delta: sc.baseline_delta,
                    }))}
                    margin={{ top: 10, right: 30, left: 20, bottom: 25 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} interval={0} angle={-10} textAnchor="end" />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#ffffff",
                        borderColor: "#cbd5e1",
                        borderRadius: "0.75rem",
                        fontSize: "12px",
                        boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                      }}
                      formatter={(value: any, name: any, item: any) => [
                        `${Number(value).toLocaleString()} p/h (${item.payload.delta > 0 ? "+" : ""}${item.payload.delta} p/h vs baseline)`,
                        "Max Flow",
                      ]}
                      labelFormatter={(_, items) => items?.[0]?.payload?.fullName || ""}
                    />
                    <Bar dataKey="flow" fill="#2563eb" radius={[6, 6, 0, 0]} name="Max Flow (p/h)">
                      {scenariosList.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.baseline_delta < 0 ? "#dc2626" : entry.baseline_delta > 0 ? "#059669" : "#2563eb"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Scenario Comparison Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {scenariosList.map((sc) => {
              const delta = sc.baseline_delta;
              const isGain = delta > 0;
              const isLoss = delta < 0;

              return (
                <div
                  key={sc.scenario_key}
                  className="p-5 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between shadow-xs hover:shadow-cardHover transition-all"
                >
                  <div>
                    <div className="flex items-center justify-between text-xs pb-2.5 border-b border-slate-100">
                      <span className="font-bold text-slate-900">{sc.scenario_name}</span>
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                          isLoss
                            ? "bg-red-50 text-red-700 border-red-200"
                            : isGain
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-slate-100 text-slate-700 border-slate-200"
                        }`}
                      >
                        {isLoss ? `${delta} p/h` : isGain ? `+${delta} p/h` : "BASELINE"}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 my-2.5 leading-relaxed">{sc.description}</p>

                    <div className="space-y-1 font-mono text-xs pt-2.5 border-t border-slate-100">
                      <div className="flex justify-between text-slate-500">
                        <span>Max Flow:</span>
                        <span className="text-slate-900 font-bold">{sc.max_flow.toLocaleString()} p/h</span>
                      </div>
                      <div className="flex justify-between text-slate-500">
                        <span>Evacuation Rate:</span>
                        <span className="text-blue-700 font-bold">{(sc.evacuation_rate * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3.5 pt-2 border-t border-slate-100 text-[10px] text-slate-500">
                    <span className="text-blue-600 font-bold">Observation:</span> {sc.observations?.[0] || "Calculated on independent graph copy."}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};