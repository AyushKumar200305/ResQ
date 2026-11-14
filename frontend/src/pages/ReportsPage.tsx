import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../api/client";
import {
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
} from "lucide-react";

export const ReportsPage: React.FC = () => {
  const { network, dinicResult, minCutResult, addNotification } = useApp();
  const [isExporting, setIsExporting] = useState<string | null>(null);

  const handleDownload = async (type: "json" | "csv_roads" | "csv_scenarios" | "pdf") => {
    setIsExporting(type);
    try {
      if (type === "json") {
        await api.downloadFile("/api/reports/json", `resq-network-${network?.network_id || "config"}.json`);
        addNotification("success", "Network JSON configuration exported.");
      } else if (type === "csv_roads") {
        await api.downloadFile("/api/reports/csv/roads", "resq-flow-analysis.csv");
        addNotification("success", "Road flow telemetry exported as CSV.");
      } else if (type === "csv_scenarios") {
        await api.downloadFile("/api/reports/csv/scenarios", "resq-scenarios-comparison.csv");
        addNotification("success", "Scenario stress test comparison exported as CSV.");
      } else if (type === "pdf") {
        await api.downloadFile("/api/reports/pdf", "ResQ-Evacuation-Situation-Report.pdf");
        addNotification("success", "Professional PDF Situation Report downloaded successfully.");
      }
    } catch (err: any) {
      addNotification("error", `Export failed: ${err.message}`);
    } finally {
      setIsExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-600" />
            Report Generation & Operational Exports
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Export comprehensive disaster evacuation briefings in PDF, raw network JSON schemas, and analytical CSV formats.
          </p>
        </div>
      </div>

      {/* Export Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* PDF Executive Report Card */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-lg bg-rose-50 text-rose-600 border border-rose-200">
                <FileText className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                EXECUTIVE BRIEFING
              </span>
            </div>

            <h3 className="text-base font-bold text-slate-900">Disaster Evacuation Situation Report (PDF)</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4 leading-relaxed">
              Publication-grade formal report compiled via ReportLab. Includes executive summary, Dinic algorithmic metrics, Min-Cut bottleneck roster, and civil defense dispatch advisories.
            </p>

            <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200 text-xs font-mono space-y-1 mb-4 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Document Title:</span>
                <span className="font-semibold">ResQ Official Situation Report</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Network ID:</span>
                <span className="text-sky-700 font-bold">{network?.network_id || "metro-flood-baseline"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Format / Pages:</span>
                <span>Standard Letter / Multi-page</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("pdf")}
            disabled={isExporting !== null}
            className="w-full py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${isExporting === "pdf" ? "animate-bounce" : ""}`} />
            <span>{isExporting === "pdf" ? "Rendering PDF..." : "Download PDF Situation Report"}</span>
          </button>
        </div>

        {/* JSON Topology Data Card */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-lg bg-sky-50 text-sky-600 border border-sky-200">
                <FileCode className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200">
                RAW TOPOLOGY
              </span>
            </div>

            <h3 className="text-base font-bold text-slate-900">Network Topology Schema (JSON)</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4 leading-relaxed">
              Complete machine-readable JSON structure containing all nodes (coordinates, populations, shelter capacities) and directed road corridors (distances, speed limits, capacities).
            </p>

            <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200 text-xs font-mono space-y-1 mb-4 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Total Nodes:</span>
                <span className="font-semibold">{network ? Object.keys(network.nodes).length : 0} vertices</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Total Roads:</span>
                <span className="font-semibold">{network ? Object.keys(network.roads).length : 0} directed edges</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Schema Standard:</span>
                <span>ResQ Domain Schema v1.0</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("json")}
            disabled={isExporting !== null}
            className="w-full py-2 bg-slate-800 hover:bg-slate-900 text-white border border-slate-700 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${isExporting === "json" ? "animate-bounce" : ""}`} />
            <span>{isExporting === "json" ? "Packaging JSON..." : "Export Network JSON"}</span>
          </button>
        </div>

        {/* CSV Road Flow Telemetry Card */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                FLOW TELEMETRY
              </span>
            </div>

            <h3 className="text-base font-bold text-slate-900">Road Corridor Analysis (CSV)</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4 leading-relaxed">
              Spreadsheet of every road segment with nominal capacity, assigned flow, residual headroom, saturation flag, and min-cut status for GIS mapping.
            </p>

            <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200 text-xs font-mono space-y-1 mb-4 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Max Flow Recorded:</span>
                <span className="text-emerald-700 font-bold">{dinicResult?.max_flow.toLocaleString() ?? "—"} p/h</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Columns:</span>
                <span>road_id, u, v, cap, flow, util_pct, saturated, mincut</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("csv_roads")}
            disabled={isExporting !== null}
            className="w-full py-2 bg-slate-800 hover:bg-slate-900 text-white border border-slate-700 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${isExporting === "csv_roads" ? "animate-bounce" : ""}`} />
            <span>{isExporting === "csv_roads" ? "Exporting CSV..." : "Export Road Telemetry CSV"}</span>
          </button>
        </div>

        {/* CSV Scenario Comparison Card */}
        <div className="bg-white border border-slate-200/80 rounded-xl p-5 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-lg bg-amber-50 text-amber-600 border border-amber-200">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                SCENARIOS
              </span>
            </div>

            <h3 className="text-base font-bold text-slate-900">Scenario Comparison Matrix (CSV)</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4 leading-relaxed">
              Export table of standard and custom disaster scenarios with baseline flow deltas (Δ), percentage change, and shifting bottleneck edges.
            </p>

            <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200 text-xs font-mono space-y-1 mb-4 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Scenarios Captured:</span>
                <span>5 standard + custom tests</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Columns:</span>
                <span>scenario_name, max_flow, delta, pct_change, bottlenecks</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("csv_scenarios")}
            disabled={isExporting !== null}
            className="w-full py-2 bg-slate-800 hover:bg-slate-900 text-white border border-slate-700 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${isExporting === "csv_scenarios" ? "animate-bounce" : ""}`} />
            <span>{isExporting === "csv_scenarios" ? "Exporting CSV..." : "Export Scenarios CSV"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
