import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../api/client";
import type { BenchmarkData, GreedyCompareData } from "../types/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Award,
  Cpu,
  Flame,
  Play,
  RotateCcw,
  Scale,
  Sparkles,
  TrendingUp,
} from "lucide-react";

export const AlgorithmComparisonPage: React.FC = () => {
  const { network, switchPreset, addNotification } = useApp();

  const [comparison, setComparison] = useState<GreedyCompareData | null>(null);
  const [greedyStrategy, setGreedyStrategy] = useState<string>("shortest_hop");
  const [benchmarkSuite, setBenchmarkSuite] = useState<BenchmarkData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isBenchmarking, setIsBenchmarking] = useState(false);

  // Fetch head-to-head comparison on active network
  const loadComparison = async () => {
    setIsLoading(true);
    try {
      const res = await api.compareGreedy(greedyStrategy, 3);
      setComparison(res);
    } catch (err: any) {
      addNotification("error", `Algorithm comparison failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadComparison();
  }, [network, greedyStrategy]);

  // Run multi-scale benchmark suite
  const handleRunBenchmark = async () => {
    setIsBenchmarking(true);
    try {
      const suite = await api.runBenchmark(greedyStrategy, 3);
      setBenchmarkSuite(suite);
      addNotification("success", "Benchmark suite completed across synthetic graph scales.");
    } catch (err: any) {
      addNotification("error", `Benchmark failed: ${err.message}`);
    } finally {
      setIsBenchmarking(false);
    }
  };

  // Switch to the classic Greedy Trap preset
  const handleLoadGreedyTrap = async () => {
    await switchPreset("greedy_trap");
    addNotification(
      "warning",
      "Loaded Classic Greedy Trap Counterexample. Watch how Greedy gets stuck while Dinic achieves full flow!"
    );
  };

  const chartData = benchmarkSuite?.tiers.map((t) => ({
    name: t.tier_name,
    vertices: t.vertices,
    edges: t.edges,
    dinicMs: Number(t.dinic_time_ms.toFixed(3)),
    greedyMs: Number(t.greedy_time_ms.toFixed(3)),
    speedup: t.speedup_ratio,
  })) || [];

  const isDinicSuperior = comparison ? comparison.dinic_max_flow > comparison.greedy_flow : false;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Scale className="w-5 h-5 text-sky-600" />
            Algorithm Comparison: Dinic (O(V² E)) vs Greedy Baseline
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Empirical runtime benchmarks, reverse edge augmentation proof, and mathematical optimality verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleLoadGreedyTrap}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold border border-rose-200 shadow-2xs transition-colors"
          >
            <Flame className="w-3.5 h-3.5 text-rose-600" />
            <span>Load Greedy Trap Proof Network</span>
          </button>
        </div>
      </div>

      {/* Head-to-Head Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dinic Algorithm Card */}
        <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-xs relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-sky-600 text-white text-[10px] font-bold px-3 py-1 rounded-bl-lg">
            OPTIMAL GUARANTEE
          </div>

          <div className="flex items-center gap-2 mb-3">
            <Award className="w-5 h-5 text-sky-600" />
            <div>
              <h3 className="text-base font-bold text-slate-900">Dinic's Maximum Flow Algorithm</h3>
              <span className="text-xs font-mono font-semibold text-sky-700">Time Complexity: O(V² E)</span>
            </div>
          </div>

          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            Constructs layered level graphs via BFS, pushes multiple blocking flows simultaneously via DFS with dead-end pruning, and maintains dynamic residual reverse edges for corrective rerouting.
          </p>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Total Evacuation Flow</span>
              <span className="text-xl font-bold text-sky-700">
                {comparison?.dinic_max_flow.toLocaleString() ?? "—"} <span className="text-xs font-normal">p/h</span>
              </span>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Execution Time</span>
              <span className="text-xl font-bold text-emerald-700">
                {comparison?.dinic_time_ms.toFixed(3) ?? "—"} <span className="text-xs font-normal">ms</span>
              </span>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Optimality Gap</span>
              <span className="text-base font-bold text-emerald-700">
                0.0% (GLOBAL OPTIMUM)
              </span>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Reverse Edges Used?</span>
              <span className="text-base font-bold text-emerald-700">
                YES (Dynamic Rerouting)
              </span>
            </div>
          </div>
        </div>

        {/* Greedy Baseline Card */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-slate-100 text-slate-600 text-[10px] font-bold px-3 py-1 rounded-bl-lg border-b border-l border-slate-200">
            HEURISTIC ONLY
          </div>

          <div className="flex items-center gap-2 mb-3">
            <Cpu className="w-5 h-5 text-amber-500" />
            <div>
              <h3 className="text-base font-bold text-slate-900">Greedy Baseline Heuristic</h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs font-mono font-medium text-amber-700">Strategy:</span>
                <select
                  value={greedyStrategy}
                  onChange={(e) => setGreedyStrategy(e.target.value)}
                  className="bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded px-2 py-0.5 focus:outline-none focus:bg-white"
                >
                  <option value="shortest_hop">Shortest Hop BFS</option>
                  <option value="widest_bottleneck">Widest Bottleneck</option>
                  <option value="lexicographic_dfs">Lexicographic DFS</option>
                </select>
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            Greedily selects augmenting paths without creating reverse residual edges. Once capacity is committed, flow cannot be pushed backward, often getting trapped in local sub-optima.
          </p>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Total Evacuation Flow</span>
              <span className="text-xl font-bold text-amber-700">
                {comparison?.greedy_flow.toLocaleString() ?? "—"} <span className="text-xs font-normal">p/h</span>
              </span>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Execution Time</span>
              <span className="text-xl font-bold text-slate-800">
                {comparison?.greedy_time_ms.toFixed(3) ?? "—"} <span className="text-xs font-normal">ms</span>
              </span>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Optimality Gap (Loss)</span>
              <span className={`text-base font-bold ${isDinicSuperior ? "text-rose-600" : "text-slate-700"}`}>
                {comparison?.optimality_gap_pct.toFixed(1) ?? "0.0"}%
              </span>
              <span className="text-[9px] text-slate-400 block font-mono">
                (Dinic - Greedy) / Dinic
              </span>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200">
              <span className="text-[11px] text-slate-500 block font-sans">Reverse Edges Used?</span>
              <span className="text-base font-bold text-rose-600">
                NO (Trapped)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Optimality Gap & DAA Viva Takeaway */}
      {comparison && (
        <div
          className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs ${
            isDinicSuperior
              ? "bg-rose-50/70 border-rose-200 text-rose-950"
              : "bg-white border-slate-200 text-slate-800"
          }`}
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white border border-slate-200 shadow-2xs text-sky-600">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900">
                {isDinicSuperior
                  ? `Dinic Outperforms Greedy by +${comparison.flow_difference.toLocaleString()} people/hour (+${(comparison.greedy_flow > 0 ? ((comparison.flow_difference / comparison.greedy_flow) * 100).toFixed(1) : "0.0")}% Throughput Advantage)!`
                  : "Both algorithms achieved equivalent flow on this network topology."}
              </h4>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {isDinicSuperior ? (
                  <>
                    <strong className="text-slate-900 font-semibold">Mathematical Distinction for Evaluation:</strong>{" "}
                    The <span className="font-semibold text-rose-700">Relative Optimality Gap</span> is{" "}
                    <code className="bg-white px-1 py-0.5 rounded border border-slate-200 text-rose-700">
                      (Dinic - Greedy) / Dinic = {comparison.optimality_gap_pct.toFixed(1)}%
                    </code>{" "}
                    (measuring the fraction of potential evacuation ceiling lost by Greedy). Concurrently, Dinic delivers a{" "}
                    <span className="font-semibold text-emerald-700">Throughput Advantage</span> of{" "}
                    <code className="bg-white px-1 py-0.5 rounded border border-slate-200 text-emerald-700">
                      (Dinic - Greedy) / Greedy = +{((comparison.flow_difference / comparison.greedy_flow) * 100).toFixed(1)}%
                    </code>{" "}
                    over the trapped heuristic.
                  </>
                ) : (
                  "On simpler networks without bottleneck cross-edges, Greedy may happen to find an optimal flow, but provides no formal guarantees."
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadComparison}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-200 shadow-2xs flex items-center gap-1.5"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Rerun Active Comparison</span>
            </button>
          </div>
        </div>
      )}

      {/* Live Empirical Benchmark Suite */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-sky-600" />
              Empirical Scalability Suite Across Network Tiers
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Measured via Python's high-precision <code>time.perf_counter()</code> on synthetic bipartite topologies.
            </p>
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={isBenchmarking}
            className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isBenchmarking ? "animate-spin" : ""}`} />
            <span>{isBenchmarking ? "Benchmarking Hardware..." : "Run Live Scaling Benchmark"}</span>
          </button>
        </div>

        {benchmarkSuite ? (
          <div className="space-y-4">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} label={{ value: 'Time (ms)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#ffffff",
                      borderColor: "#e2e8f0",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                      fontSize: "12px",
                      color: "#0f172a",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                  <Line
                    type="monotone"
                    dataKey="dinicMs"
                    name="Dinic Runtime (ms)"
                    stroke="#0284c7"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="greedyMs"
                    name="Greedy Runtime (ms)"
                    stroke="#d97706"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Graph Scale</th>
                    <th className="py-2.5 px-3 text-right">Vertices |V|</th>
                    <th className="py-2.5 px-3 text-right">Edges |E|</th>
                    <th className="py-2.5 px-3 text-right">Dinic Time</th>
                    <th className="py-2.5 px-3 text-right">Greedy Time</th>
                    <th className="py-2.5 px-3 text-right">Dinic Max Flow</th>
                    <th className="py-2.5 px-3 text-right">Greedy Max Flow</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {benchmarkSuite.tiers.map((run, i) => (
                    <tr key={i} className="hover:bg-slate-50/70">
                      <td className="py-2 px-3 text-slate-900 font-sans font-medium">{run.tier_name}</td>
                      <td className="py-2 px-3 text-right text-slate-700">{run.vertices}</td>
                      <td className="py-2 px-3 text-right text-slate-500">{run.edges}</td>
                      <td className="py-2 px-3 text-right text-sky-700 font-bold">
                        {run.dinic_time_ms.toFixed(3)} ms
                      </td>
                      <td className="py-2 px-3 text-right text-amber-700 font-bold">
                        {run.greedy_time_ms.toFixed(3)} ms
                      </td>
                      <td className="py-2 px-3 text-right text-emerald-700 font-bold">
                        {run.dinic_max_flow.toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-right text-slate-700">
                        {run.greedy_flow.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 text-xs">
            Click "Run Live Scaling Benchmark" to execute performance tests on your machine.
          </div>
        )}
      </div>
    </div>
  );
};
