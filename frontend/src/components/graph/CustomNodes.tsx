import { Handle, Position } from "@xyflow/react";
import { Building2, Home, Navigation } from "lucide-react";

export const AffectedAreaNode = ({ data }: { data: any }) => {
  return (
    <div className="bg-white border-2 border-red-500 rounded-2xl p-3 min-w-[140px] shadow-sm hover:shadow-cardHover transition-all">
      <div className="flex items-center gap-2 mb-1.5">
        <div className="w-7 h-7 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-xs">
          <Home className="w-4 h-4" />
        </div>
        <div>
          <div className="text-[10px] font-bold text-red-700 uppercase tracking-wider">
            Affected Area
          </div>
          <div className="text-xs font-bold text-slate-900 truncate max-w-[100px]">
            {data.name || data.node_id}
          </div>
        </div>
      </div>
      <div className="bg-red-50/60 rounded-lg px-2.5 py-1 flex items-baseline justify-between border border-red-100">
        <span className="text-[10px] text-slate-500 font-medium">Pop:</span>
        <span className="text-xs font-bold text-red-700 font-mono">
          {Number(data.population || 0).toLocaleString()}
        </span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-red-600 border-2 border-white shadow-xs"
      />
    </div>
  );
};

export const JunctionNode = ({ data }: { data: any }) => {
  return (
    <div className="bg-white border border-slate-300 hover:border-blue-500 rounded-2xl p-2.5 min-w-[120px] shadow-xs hover:shadow-cardHover transition-all">
      <Handle
        type="target"
        position={Position.Left}
        className="w-2.5 h-2.5 bg-blue-600 border-2 border-white shadow-xs"
      />
      <div className="flex items-center gap-1.5 mb-1">
        <div className="w-6 h-6 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shadow-xs">
          <Navigation className="w-3.5 h-3.5" />
        </div>
        <div className="min-w-0">
          <div className="text-[9px] font-bold text-blue-700 uppercase">
            Junction
          </div>
          <div className="text-xs font-bold text-slate-900 truncate max-w-[90px]">
            {data.name || data.node_id}
          </div>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="w-2.5 h-2.5 bg-blue-600 border-2 border-white shadow-xs"
      />
    </div>
  );
};

export const ShelterNode = ({ data }: { data: any }) => {
  return (
    <div className="bg-white border-2 border-emerald-500 rounded-2xl p-3 min-w-[140px] shadow-sm hover:shadow-cardHover transition-all">
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-emerald-600 border-2 border-white shadow-xs"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shadow-xs">
          <Building2 className="w-4 h-4" />
        </div>
        <div>
          <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">
            Safe Shelter
          </div>
          <div className="text-xs font-bold text-slate-900 truncate max-w-[100px]">
            {data.name || data.node_id}
          </div>
        </div>
      </div>
      <div className="bg-emerald-50/60 rounded-lg px-2.5 py-1 flex items-baseline justify-between border border-emerald-100">
        <span className="text-[10px] text-slate-500 font-medium">Cap:</span>
        <span className="text-xs font-bold text-emerald-700 font-mono">
          {Number(data.shelter_capacity || 0).toLocaleString()}
        </span>
      </div>
    </div>
  );
};
