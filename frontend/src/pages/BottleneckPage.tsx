import React, { useMemo } from "react";
import { useApp } from "../context/AppContext";
import { TermTooltip } from "../components/common/TermTooltip";
import {
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  ShieldAlert,
  TrendingUp,
  Zap,
} from "lucide-react";

export const BottleneckPage: React.FC = () => {
  const { network, dinicResult, minCutResult, runDinicAnalysis, isSolving } = useApp();

  const sNodes = minCutResult?.reachable_node_ids || [];
  const tNodes = minCutResult?.unreachable_node_ids || [];
  const cutCapacity = minCutResult?.total_cut_capacity ?? 0;
  const maxFlow = dinicResult?.max_flow ?? 0;
  const roadBottlenecks = minCutResult?.road_bottlenecks || [];

  // Cut road details joined with network roads
  const cutRoads = useMemo(() => {
    if (!network || !minCutResult) return [];
    return roadBottlenecks.map((rb) => {
      const road = network.roads.find((r) => r.road_id === rb.edge_id);
      return {
        ...rb,
        name: road?.name || rb.edge_id,
        distance: road?.distance || 0,
      };
    });
  }, [network, minCutResult, roadBottlenecks]);

  // Max-Flow Min-Cut Theorem Check
  const theoremHolds = maxFlow > 0 && maxFlow === cutCapacity;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-600" />
            Bottleneck Analysis & Min-Cut Partition (S* - T*)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Rigorous DAA validation of the <TermTooltip termKey="minimum-cut">Max-Flow Min-Cut Theorem</TermTooltip> (|f*| = c(S*, T*)) and evacuation <TermTooltip termKey="bottleneck">chokepoint identification</TermTooltip>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => runDinicAnalysis()}
            disabled={isSolving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${isSolving ? "animate-spin" : ""}`} />
            <span>{isSolving ? "Computing Cut..." : "Recalculate Min-Cut"}</span>
          </button>
        </div>
      </div>

      {/* Max-Flow Min-Cut Verification Banner */}
      <div
        className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs ${
          theoremHolds
            ? "bg-emerald-50/70 border-emerald-200 text-emerald-950"
            : "bg-rose-50/70 border-rose-200 text-rose-950"
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-xl ${
              theoremHolds ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
            }`}
          >
            {theoremHolds ? <CheckCircle2 className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              {theoremHolds
                ? "Max-Flow Min-Cut Theorem Mathematically Verified"
                : "Awaiting Solution or Cut Verification"}
            </h3>
            <p className="text-xs text-slate-600 mt-0.5 font-mono">
              Maximum Flow |f*| = {maxFlow.toLocaleString()} p/h &nbsp;==&nbsp; Minimum Cut Capacity c(S*, T*) ={" "}
              {cutCapacity.toLocaleString()} p/h
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-slate-400 block text-[10px] font-sans">Partition Size</span>
            <span className="text-slate-800 font-bold">
              |S*| = {sNodes.length} &nbsp;|&nbsp; |T*| = {tNodes.length}
            </span>
          </div>
          <div className="bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-slate-400 block text-[10px] font-sans">Cut Road Edges</span>
            <span className="text-rose-600 font-bold">{cutRoads.length} chokepoints</span>
          </div>
        </div>
      </div>

      {/* Residual Partition Explanation & Node Sets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* S* Reachable Set */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold text-sky-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
              <span>Reachable Set S* ({sNodes.length} nodes)</span>
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">Residual Path from Source</span>
          </div>
          <p className="text-[11px] text-slate-500 mb-3 leading-relaxed">
            Nodes reachable from the Super-Source S* via positive <TermTooltip termKey="residual-capacity">residual capacity</TermTooltip> edges (c_f(u, v) &gt; 0) after flow augmentation finishes.
          </p>

          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto p-2 bg-slate-50/70 rounded-lg border border-slate-200">
            {sNodes.map((nodeId) => {
              const node = network?.nodes.find((n) => n.node_id === nodeId);
              return (
                <span
                  key={nodeId}
                  className="px-2 py-1 rounded-md bg-white border border-slate-200 text-xs font-mono text-slate-800 shadow-2xs"
                  title={node?.name || nodeId}
                >
                  {nodeId}
                  {node && <span className="text-[10px] text-slate-400 ml-1">({node.node_type[0].toUpperCase()})</span>}
                </span>
              );
            })}
          </div>
        </div>

        {/* T* Unreachable Set */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold text-rose-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
              <span>Unreachable Set T* ({tNodes.length} nodes)</span>
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">Safe / Sink Partition</span>
          </div>
          <p className="text-[11px] text-slate-500 mb-3 leading-relaxed">
            Nodes disconnected from S* in the residual network. Any edge spanning S* into T* is saturated (f(e) = c(e)) and forms the bottleneck.
          </p>

          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto p-2 bg-slate-50/70 rounded-lg border border-slate-200">
            {tNodes.map((nodeId) => {
              const node = network?.nodes.find((n) => n.node_id === nodeId);
              return (
                <span
                  key={nodeId}
                  className="px-2 py-1 rounded-md bg-white border border-slate-200 text-xs font-mono text-slate-800 shadow-2xs"
                  title={node?.name || nodeId}
                >
                  {nodeId}
                  {node && <span className="text-[10px] text-slate-400 ml-1">({node.node_type[0].toUpperCase()})</span>}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* Critical Bottleneck Corridors (Min-Cut Edges) */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              Identified Network Bottleneck Corridors
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Road corridors strictly crossing from S* into T*. Widening any of these directly increases the maximum evacuation rate.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5 px-3">Bottleneck Road</th>
                <th className="py-2.5 px-3">Cut Traversal (S* → T*)</th>
                <th className="py-2.5 px-3 text-right">Road Capacity</th>
                <th className="py-2.5 px-3 text-right">Assigned Flow</th>
                <th className="py-2.5 px-3 text-right">Saturation Ratio</th>
                <th className="py-2.5 px-4">Intervention Priority</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {cutRoads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500 font-sans">
                    No physical road cuts identified (flow may be bounded solely by shelter intake capacity).
                  </td>
                </tr>
              ) : (
                cutRoads.map((cr, idx) => (
                  <tr key={cr.edge_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-sans">
                      <span className="font-bold text-slate-900 block">{cr.name}</span>
                      <span className="text-[10px] text-slate-400 font-mono font-normal">{cr.edge_id}</span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-rose-600">
                      {cr.source_id} <span className="text-slate-400">→</span> {cr.target_id}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700 font-bold">
                      {cr.original_capacity} <span className="text-[10px] text-slate-400 font-normal">p/h</span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-sky-600 font-bold">
                      {cr.flow} <span className="text-[10px] text-slate-400 font-normal">p/h</span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-amber-600 font-bold">
                      100.0% (SATURATED)
                    </td>
                    <td className="py-2.5 px-4 font-sans">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                        CRITICAL RANK #{idx + 1}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* DAA Sensitivity & Engineering Decision Insight */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          Civil Defense Recommendation: Sensitivity Analysis & Expansion ROI
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-600 mt-3">
          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <h4 className="font-bold text-sky-700 mb-1 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-sky-600" />
              1. High ROI Interventions
            </h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Adding lanes or contra-flow clearance to <strong className="text-slate-900 font-semibold">cut roads ({cutRoads.map(c => c.edge_id).join(", ")})</strong> directly enlarges the cut capacity and increases overall evacuee life-saving rate.
            </p>
          </div>

          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <h4 className="font-bold text-rose-700 mb-1 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              2. Zero ROI Interventions
            </h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Expanding non-cut roads has <strong className="text-slate-900 font-semibold">zero effect</strong> on max evacuation flow because they are not the active limiting constraints. Expanding them wastes emergency resources.
            </p>
          </div>

          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <h4 className="font-bold text-emerald-700 mb-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              3. Shelter Bottleneck Check
            </h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              If all roads leading into a shelter have residual headroom but the shelter itself is full, the bottleneck shifts to shelter intake capacity rather than transportation infrastructure.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
