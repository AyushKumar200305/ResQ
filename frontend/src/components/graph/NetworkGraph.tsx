import React, { useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useApp } from "../../context/AppContext";
import type { RoadFlowDetail } from "../../types/api";
import { CustomRoadEdge } from "./CustomEdge";
import {
  AffectedAreaNode,
  JunctionNode,
  ShelterNode,
} from "./CustomNodes";

const nodeTypes = {
  affected_area: AffectedAreaNode,
  junction: JunctionNode,
  shelter: ShelterNode,
};

const edgeTypes = {
  customRoad: CustomRoadEdge,
};

export const NetworkGraph: React.FC<{
  interactive?: boolean;
  heightClass?: string;
  primaryRouteRoads?: string[];
  alternativeRouteRoads?: string[];
  onNodeClick?: (nodeId: string) => void;
  onRoadClick?: (roadId: string) => void;
}> = ({
  interactive = true,
  heightClass = "h-[600px]",
  primaryRouteRoads = [],
  alternativeRouteRoads = [],
  onNodeClick,
  onRoadClick,
}) => {
  const { network, analysis } = useApp();
  const [selectedEntity, setSelectedEntity] = useState<
    | { type: "node"; id: string; data: any }
    | { type: "road"; id: string; data: any }
    | null
  >(null);

  const primarySet = useMemo(() => new Set(primaryRouteRoads), [primaryRouteRoads]);
  const altSet = useMemo(() => new Set(alternativeRouteRoads), [alternativeRouteRoads]);

  // Map network nodes to React Flow nodes with scaled coordinates
  const flowNodes: Node[] = useMemo(() => {
    if (!network) return [];

    return network.nodes.map((n, idx) => {
      // Scale coordinates from normalized domain coordinates to pixel canvas
      let posX = n.x != null ? n.x * 125 + 60 : (idx % 4) * 220 + 80;
      let posY = n.y != null ? -n.y * 95 + 320 : Math.floor(idx / 4) * 160 + 80;

      return {
        id: n.node_id,
        type: n.node_type,
        position: { x: posX, y: posY },
        data: { ...n },
      };
    });
  }, [network]);

  // Map network roads to React Flow edges with flow and min-cut telemetry
  const flowEdges: Edge[] = useMemo(() => {
    if (!network) return [];

    const flowMap = new Map<string, RoadFlowDetail>();
    if (analysis) {
      analysis.dinic.road_flows.forEach((rf) => flowMap.set(rf.road_id, rf));
    }

    const minCutRoads = new Set(
      analysis?.min_cut.road_bottlenecks.map((b) => b.edge_id) || []
    );

    return network.roads.map((r) => {
      const rf = flowMap.get(r.road_id);
      const isMinCut = minCutRoads.has(r.road_id);
      const flow = rf ? rf.flow : 0;
      const isSaturated = rf ? rf.is_saturated : false;

      const meta = r.metadata || {};
      const safetyStatus = meta.safety_status || (r.is_active ? "verified_clear" : "closed_damaged");
      const isHazardAvoid = safetyStatus === "hazard_avoid";
      const isUnverified = safetyStatus === "unverified_report";
      const isPrimaryRoute = primarySet.has(r.road_id);
      const isAltRoute = altSet.has(r.road_id);

      return {
        id: r.road_id,
        source: r.source_id,
        target: r.target_id,
        type: "customRoad",
        animated: flow > 0 || isPrimaryRoute,
        data: {
          road_id: r.road_id,
          name: r.name,
          capacity: r.capacity,
          flow,
          isMinCut,
          isSaturated,
          isActive: r.is_active && safetyStatus !== "closed_damaged",
          isPrimaryRoute,
          isAltRoute,
          isHazardAvoid,
          isUnverified,
          hasAnalysis: Boolean(analysis),
        },
      };
    });
  }, [network, analysis, primarySet, altSet]);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedEntity({ type: "node", id: node.id, data: node.data });
    if (onNodeClick) onNodeClick(node.id);
  };

  const handleEdgeClick = (_: React.MouseEvent, edge: Edge) => {
    setSelectedEntity({ type: "road", id: edge.id, data: edge.data });
    if (onRoadClick) onRoadClick(edge.id);
  };

  return (
    <div className={`relative w-full ${heightClass} bg-slate-50/70 border border-slate-200 rounded-2xl overflow-hidden`}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        fitView
        nodesDraggable={interactive}
        nodesConnectable={false}
        elementsSelectable={interactive}
        minZoom={0.2}
        maxZoom={2.5}
      >
        <Background color="#cbd5e1" gap={20} size={1} />
        {interactive && (
          <>
            <Controls className="react-flow__controls m-4" />
            <MiniMap
              className="react-flow__minimap m-4 hidden sm:block !bg-white/90 !border !border-slate-200 !rounded-xl !shadow-xs"
              nodeColor={(n) => {
                if (n.type === "affected_area") return "#ef4444";
                if (n.type === "shelter") return "#10b981";
                return "#3b82f6";
              }}
            />
          </>
        )}
      </ReactFlow>

      {/* Floating Inspector overlay for selected element */}
      {selectedEntity && (
        <div className="absolute top-4 right-4 bg-white/95 backdrop-blur border border-slate-200 rounded-2xl p-4 text-xs w-68 shadow-card z-10 text-slate-800">
          <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
            <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px]">
              {selectedEntity.type === "node" ? "Vertex Telemetry" : "Corridor Telemetry"}
            </span>
            <button
              onClick={() => setSelectedEntity(null)}
              className="text-slate-400 hover:text-slate-700 font-bold"
            >
              ✕
            </button>
          </div>
          <div className="mt-2.5 space-y-1.5 font-mono">
            <div className="flex justify-between">
              <span className="text-slate-500 font-medium font-sans">ID:</span>
              <span className="text-slate-900 font-bold">{selectedEntity.id}</span>
            </div>
            {selectedEntity.type === "node" ? (
              <>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium font-sans">Type:</span>
                  <span className="text-blue-700 font-bold uppercase text-[10px]">
                    {selectedEntity.data.node_type}
                  </span>
                </div>
                {selectedEntity.data.population > 0 && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium font-sans">Population:</span>
                    <span className="text-red-600 font-bold">
                      {selectedEntity.data.population.toLocaleString()}
                    </span>
                  </div>
                )}
                {selectedEntity.data.shelter_capacity > 0 && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium font-sans">Capacity:</span>
                    <span className="text-emerald-700 font-bold">
                      {selectedEntity.data.shelter_capacity.toLocaleString()}
                    </span>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium font-sans">Capacity:</span>
                  <span className="text-slate-900 font-bold">
                    {selectedEntity.data.capacity?.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium font-sans">Active Flow:</span>
                  <span className="text-blue-700 font-bold">
                    {selectedEntity.data.flow?.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-medium font-sans">Min-Cut Bottleneck:</span>
                  <span
                    className={
                      selectedEntity.data.isMinCut
                        ? "text-red-600 font-bold"
                        : "text-slate-400"
                    }
                  >
                    {selectedEntity.data.isMinCut ? "YES (CRITICAL)" : "No"}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
