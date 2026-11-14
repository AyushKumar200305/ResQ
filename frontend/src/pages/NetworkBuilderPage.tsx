import React, { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import type { NodeType } from "../types/api";

export const NetworkBuilderPage: React.FC = () => {
  const { network, refreshNetwork, notify, loadDemo, isLoading } = useApp();

  // Node Form State
  const [nodeId, setNodeId] = useState("");
  const [nodeName, setNodeName] = useState("");
  const [nodeType, setNodeType] = useState<NodeType>("affected_area");
  const [population, setPopulation] = useState(500);
  const [shelterCap, setShelterCap] = useState(500);

  // Road Form State
  const [roadId, setRoadId] = useState("");
  const [roadName, setRoadName] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [capacity, setCapacity] = useState(500);
  const [distance, setDistance] = useState(2.5);

  // Validation State
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [isValidated, setIsValidated] = useState(false);

  const handleAddNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nodeId || !nodeName) {
      notify("error", "Node ID and Name are required.");
      return;
    }
    try {
      await api.addNode({
        node_id: nodeId.trim(),
        name: nodeName.trim(),
        node_type: nodeType,
        population: nodeType === "affected_area" ? Number(population) : 0,
        shelter_capacity: nodeType === "shelter" ? Number(shelterCap) : 0,
      });
      notify("success", `Added vertex '${nodeId}' successfully.`);
      setNodeId("");
      setNodeName("");
      refreshNetwork();
    } catch (err: unknown) {
      notify("error", err instanceof Error ? err.message : "Failed to add node.");
    }
  };

  const handleDeleteNode = async (id: string) => {
    if (!window.confirm(`Delete vertex '${id}' and all incident roads?`)) return;
    try {
      await api.deleteNode(id, true);
      notify("info", `Deleted vertex '${id}'.`);
      refreshNetwork();
    } catch (err: unknown) {
      notify("error", err instanceof Error ? err.message : "Failed to delete node.");
    }
  };

  const handleAddRoad = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roadId || !sourceId || !targetId) {
      notify("error", "Road ID, Source Node, and Target Node are required.");
      return;
    }
    if (sourceId === targetId) {
      notify("error", "Road cannot be a self-loop (source and target must be distinct).");
      return;
    }
    try {
      await api.addRoad({
        road_id: roadId.trim(),
        name: roadName.trim() || `Corridor ${sourceId}->${targetId}`,
        source_id: sourceId,
        target_id: targetId,
        capacity: Number(capacity),
        distance: Number(distance),
        is_active: true,
      });
      notify("success", `Added corridor '${roadId}' (${sourceId} -> ${targetId}).`);
      setRoadId("");
      setRoadName("");
      refreshNetwork();
    } catch (err: unknown) {
      notify("error", err instanceof Error ? err.message : "Failed to add road.");
    }
  };

  const handleDeleteRoad = async (id: string) => {
    if (!window.confirm(`Delete road corridor '${id}'?`)) return;
    try {
      await api.deleteRoad(id);
      notify("info", `Deleted road corridor '${id}'.`);
      refreshNetwork();
    } catch (err: unknown) {
      notify("error", err instanceof Error ? err.message : "Failed to delete road.");
    }
  };

  const handleValidate = async () => {
    try {
      const rep = await api.validateNetwork();
      setValidationErrors(rep.errors);
      setValidationWarnings(rep.warnings);
      setIsValidated(true);
      if (rep.is_valid) {
        notify("success", "Topological sanity check passed! Network ready for evacuation.");
      } else {
        notify("warning", `Validation found ${rep.errors.length} error(s).`);
      }
    } catch (err: unknown) {
      notify("error", err instanceof Error ? err.message : "Validation failed.");
    }
  };

  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const parsed = JSON.parse(evt.target?.result as string);
        await api.createNetwork(parsed);
        notify("success", `Successfully imported network: ${parsed.name || "Custom"}`);
        refreshNetwork();
      } catch (err: unknown) {
        notify("error", "Malformed network JSON file.");
      }
    };
    reader.readAsText(file);
  };

  const nodesList = network?.nodes || [];
  const roadsList = network?.roads || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Network Topology Builder</h1>
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              GRAPH EDITOR
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Modify the directed evacuation graph: configure source demand, transit junctions, and shelter capacities.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleValidate}
            className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Validate Graph</span>
          </button>

          <label className="px-3.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 flex items-center gap-1.5 cursor-pointer shadow-xs transition-colors">
            <Upload className="w-3.5 h-3.5 text-blue-600" />
            <span>Import JSON</span>
            <input type="file" accept=".json" onChange={handleImportJson} className="hidden" />
          </label>

          <a
            href={api.exportJsonUrl}
            download
            className="px-3.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-blue-600" />
            <span>Export JSON</span>
          </a>

          <button
            onClick={loadDemo}
            className="px-3.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            <span>Reset Demo</span>
          </button>
        </div>
      </div>

      {/* Validation Feedback Banner */}
      {isValidated && (
        <div
          className={`p-4 rounded-xl border text-xs shadow-xs ${
            validationErrors.length === 0
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-red-50 border-red-200 text-red-900"
          }`}
        >
          <div className="flex items-center gap-2 font-bold mb-1">
            {validationErrors.length === 0 ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Topology Sanity Audit Passed</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-red-600" />
                <span>Topology Errors Found ({validationErrors.length})</span>
              </>
            )}
          </div>
          {validationErrors.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5 mt-2 font-mono text-[11px] text-red-700">
              {validationErrors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          )}
          {validationWarnings.length > 0 && (
            <div className="mt-2 text-amber-800">
              <span className="font-semibold">Warnings:</span>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                {validationWarnings.map((warn, idx) => (
                  <li key={idx}>{warn}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Forms Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Node Creation Form */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Plus className="w-4 h-4 text-blue-600" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Add Vertex (Node)</h3>
          </div>

          <form onSubmit={handleAddNode} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Node Identifier
                </label>
                <input
                  type="text"
                  value={nodeId}
                  onChange={(e) => setNodeId(e.target.value)}
                  placeholder="e.g. A4, J6, S4"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Vertex Type
                </label>
                <select
                  value={nodeType}
                  onChange={(e) => setNodeType(e.target.value as NodeType)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                >
                  <option value="affected_area">Affected Area (Source)</option>
                  <option value="junction">Intermediate Junction</option>
                  <option value="shelter">Safe Shelter (Sink)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                Vertex Name / Location
              </label>
              <input
                type="text"
                value={nodeName}
                onChange={(e) => setNodeName(e.target.value)}
                placeholder="e.g. South Hill District"
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                required
              />
            </div>

            {nodeType === "affected_area" && (
              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Evacuee Population
                </label>
                <input
                  type="number"
                  min="1"
                  value={population}
                  onChange={(e) => setPopulation(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  required
                />
              </div>
            )}

            {nodeType === "shelter" && (
              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Shelter Bed Capacity
                </label>
                <input
                  type="number"
                  min="1"
                  value={shelterCap}
                  onChange={(e) => setShelterCap(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  required
                />
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-xs transition-colors"
            >
              Register Vertex
            </button>
          </form>
        </div>

        {/* Road Creation Form */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Plus className="w-4 h-4 text-emerald-600" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Add Directed Road Corridor</h3>
          </div>

          <form onSubmit={handleAddRoad} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Road Identifier
                </label>
                <input
                  type="text"
                  value={roadId}
                  onChange={(e) => setRoadId(e.target.value)}
                  placeholder="e.g. R_A1_J1"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Corridor Name
                </label>
                <input
                  type="text"
                  value={roadName}
                  onChange={(e) => setRoadName(e.target.value)}
                  placeholder="e.g. North Levee Road"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  From (Source Vertex)
                </label>
                <select
                  value={sourceId}
                  onChange={(e) => setSourceId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs font-mono"
                  required
                >
                  <option value="">Select origin...</option>
                  {nodesList.map((n) => (
                    <option key={n.node_id} value={n.node_id}>
                      {n.node_id} ({n.name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  To (Target Vertex)
                </label>
                <select
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs font-mono"
                  required
                >
                  <option value="">Select destination...</option>
                  {nodesList.map((n) => (
                    <option key={n.node_id} value={n.node_id}>
                      {n.node_id} ({n.name})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Capacity (people/hour)
                </label>
                <input
                  type="number"
                  min="1"
                  value={capacity}
                  onChange={(e) => setCapacity(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1 text-[11px]">
                  Distance (km)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={distance}
                  onChange={(e) => setDistance(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-xs transition-colors"
            >
              Connect Road Corridor
            </button>
          </form>
        </div>
      </div>

      {/* Nodes & Roads Inventory Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Nodes Inventory */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Vertices Inventory ({nodesList.length})
            </h2>
          </div>

          <div className="overflow-x-auto max-h-[360px] border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-mono font-bold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">Name</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Value</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {nodesList.map((n) => (
                  <tr key={n.node_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-2 px-3 font-bold text-blue-700">{n.node_id}</td>
                    <td className="py-2 px-3 font-sans truncate max-w-[120px] text-slate-800 font-medium">
                      {n.name}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`text-[9px] px-2 py-0.5 rounded-full border font-bold uppercase ${
                          n.node_type === "affected_area"
                            ? "bg-red-50 text-red-700 border-red-200"
                            : n.node_type === "shelter"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                        }`}
                      >
                        {n.node_type.replace("_", " ")}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-700 font-medium">
                      {n.node_type === "affected_area"
                        ? `${n.population.toLocaleString()} pop`
                        : n.node_type === "shelter"
                        ? `${n.shelter_capacity.toLocaleString()} cap`
                        : "-"}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => handleDeleteNode(n.node_id)}
                        className="p-1 hover:bg-red-50 rounded-lg text-slate-400 hover:text-red-600 transition-colors"
                        title="Delete node"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Roads Inventory */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Road Corridors Inventory ({roadsList.length})
            </h2>
          </div>

          <div className="overflow-x-auto max-h-[360px] border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-mono font-bold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">Corridor</th>
                  <th className="py-2.5 px-3">Capacity</th>
                  <th className="py-2.5 px-3">Distance</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {roadsList.map((r) => (
                  <tr key={r.road_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-2 px-3 font-bold text-blue-700">{r.road_id}</td>
                    <td className="py-2 px-3 text-slate-600">
                      {r.source_id} &rarr; {r.target_id}
                    </td>
                    <td className="py-2 px-3 text-emerald-700 font-bold">
                      {r.capacity.toLocaleString()} /hr
                    </td>
                    <td className="py-2 px-3 text-slate-600">{r.distance} km</td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => handleDeleteRoad(r.road_id)}
                        className="p-1 hover:bg-red-50 rounded-lg text-slate-400 hover:text-red-600 transition-colors"
                        title="Delete road"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
