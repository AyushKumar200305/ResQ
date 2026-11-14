import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "@xyflow/react";

export const CustomRoadEdge: React.FC<EdgeProps> = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const flow = Number(data?.flow ?? 0);
  const capacity = Number(data?.capacity ?? 0);
  const isMinCut = Boolean(data?.isMinCut);
  const isSaturated = Boolean(data?.isSaturated);
  const isActive = data?.isActive !== false;
  const isPrimaryRoute = Boolean(data?.isPrimaryRoute);
  const isAltRoute = Boolean(data?.isAltRoute);
  const isHazardAvoid = Boolean(data?.isHazardAvoid);
  const isUnverified = Boolean(data?.isUnverified);

  // Color mapping based on route recommendation, hazard, saturation, and bottleneck status
  let strokeColor = "#94a3b8"; // default idle slate
  let badgeBg = "bg-white text-slate-700 border-slate-200 shadow-xs";
  let strokeWidth = 1.5;
  let strokeDasharray: string | undefined = undefined;

  if (!isActive) {
    strokeColor = "#ef4444";
    strokeWidth = 2.5;
    strokeDasharray = "5 5";
    badgeBg = "bg-red-50 text-red-700 border-red-200 font-bold shadow-xs";
  } else if (isPrimaryRoute) {
    strokeColor = "#059669"; // emerald primary route
    strokeWidth = 4.0;
    badgeBg = "bg-emerald-50 text-emerald-800 border-emerald-300 font-bold shadow-xs";
  } else if (isAltRoute) {
    strokeColor = "#0284c7"; // sky alternative route
    strokeWidth = 3.0;
    strokeDasharray = "6 4";
    badgeBg = "bg-blue-50 text-blue-800 border-blue-300 font-bold shadow-xs";
  } else if (isHazardAvoid) {
    strokeColor = "#e11d48"; // rose hazard road
    strokeWidth = 3.0;
    badgeBg = "bg-rose-50 text-rose-800 border-rose-300 font-bold shadow-xs";
  } else if (isUnverified) {
    strokeColor = "#d97706"; // amber unverified report
    strokeWidth = 3.0;
    strokeDasharray = "5 3";
    badgeBg = "bg-amber-50 text-amber-800 border-amber-300 font-bold shadow-xs";
  } else if (isMinCut) {
    strokeColor = "#dc2626"; // red minimum cut
    strokeWidth = 3.5;
    badgeBg = "bg-red-50 text-red-800 border-red-300 font-bold shadow-xs";
  } else if (isSaturated) {
    strokeColor = "#d97706"; // amber saturated
    strokeWidth = 2.5;
    badgeBg = "bg-amber-50 text-amber-800 border-amber-300 font-bold shadow-xs";
  } else if (flow > 0) {
    strokeColor = "#2563eb"; // active flow blue
    strokeWidth = 2.5;
    badgeBg = "bg-blue-50 text-blue-800 border-blue-200 font-semibold shadow-xs";
  }

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: strokeColor,
          strokeWidth,
          strokeDasharray,
          transition: "stroke 0.3s ease, stroke-width 0.3s ease",
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className={`px-2 py-0.5 rounded-full text-[10px] font-mono border flex items-center gap-1 select-none ${badgeBg}`}
        >
          {data?.hasAnalysis ? (
            <span>
              {flow.toLocaleString()}/{capacity.toLocaleString()}
            </span>
          ) : (
            <span>Cap: {capacity.toLocaleString()}</span>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
};
