import React, { useMemo } from "react";
import { useApp } from "../context/AppContext";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  BarChart3,
  CheckCircle2,
  PieChart as PieIcon,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

export const AnalyticsPage: React.FC = () => {
  const { network, dinicResult, minCutResult } = useApp();

  // 1. Shelter-wise utilization
  const shelterChartData = useMemo(() => {
    if (!network || !dinicResult) return [];

    const shelters = network.nodes.filter((n) => n.node_type === "shelter");
    return shelters.map((s) => {
      // Find intake flow from dinic shelter intakes
      const intake = dinicResult.shelter_intakes.find((si) => si.node_id === s.node_id);
      const incomingFlow = intake?.assigned_flow ?? 0;
      const capacity = s.shelter_capacity ?? 0;
      const utilization = capacity > 0 ? (incomingFlow / capacity) * 100 : 0;

      return {
        id: s.node_id,
        name: s.name,
        capacity,
        intakeFlow: incomingFlow,
        utilizationPct: Number(utilization.toFixed(1)),
        isFull: incomingFlow >= capacity,
      };
    });
  }, [network, dinicResult]);

  // 2. People evacuated vs remaining
  const evacueePieData = useMemo(() => {
    if (!network || !dinicResult) return [];

    const totalPopulation = network.total_population;
    const maxFlowRate = dinicResult.max_flow;
    const remaining = Math.max(0, totalPopulation - maxFlowRate);

    return [
      { name: "Cleared / Flow Rate (1 hr)", value: maxFlowRate, color: "#10b981" },
      { name: "Awaiting Next Wave", value: remaining, color: "#f43f5e" },
    ];
  }, [network, dinicResult]);

  // 3. Road-wise capacity utilization buckets
  const roadUtilizationBuckets = useMemo(() => {
    if (!network || !dinicResult) return [];

    const buckets = {
      "0% Idle": 0,
      "1-50% Light": 0,
      "51-99% Moderate": 0,
      "100% Saturated": 0,
    };

    dinicResult.road_flows.forEach((rf) => {
      const util = rf.utilization_ratio * 100;

      if (util === 0) buckets["0% Idle"]++;
      else if (util <= 50) buckets["1-50% Light"]++;
      else if (util < 100) buckets["51-99% Moderate"]++;
      else buckets["100% Saturated"]++;
    });

    return Object.entries(buckets).map(([bucket, count]) => ({
      bucket,
      count,
    }));
  }, [network, dinicResult]);

  // 4. Bottleneck cut roads capacities
  const bottleneckData = useMemo(() => {
    if (!network || !minCutResult) return [];
    return minCutResult.road_bottlenecks.map((rb) => {
      const road = network.roads.find((r) => r.road_id === rb.edge_id);
      return {
        roadId: rb.edge_id,
        name: road?.name || rb.edge_id,
        capacity: rb.original_capacity,
        flow: rb.flow,
      };
    });
  }, [network, minCutResult]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-sky-400" />
            Advanced Analytics & Evacuation Fleet Diagnostics
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Systematic telemetry across safe shelter absorption, arterial road saturation, and bottleneck capacities.
          </p>
        </div>
      </div>

      {/* Grid of Analytical Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Shelter Intake Allocation vs Capacity */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Shelter Intake Flow vs Max Capacity (people)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluates which disaster shelters are receiving optimal evacuee influx.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={shelterChartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="id" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    fontSize: "12px",
                    color: "#f8fafc",
                  }}
                  formatter={(val: any, name: any) => [`${val.toLocaleString()} people`, name]}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Bar dataKey="intakeFlow" name="Assigned Evac Flow" fill="#10b981" radius={[3, 3, 0, 0]} />
                <Bar dataKey="capacity" name="Shelter Total Capacity" fill="#334155" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Immediate Hour Flow vs Total Hazard Population */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 mb-1">
              <PieIcon className="w-4 h-4 text-sky-400" />
              Evacuation Clearance Ratio (First Wave Dispatch)
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Proportion of total hazard zone population moved during the initial peak hour.
            </p>
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={evacueePieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {evacueePieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    fontSize: "12px",
                    color: "#f8fafc",
                  }}
                  formatter={(val: any) => [`${val.toLocaleString()} people`, ""]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="flex justify-around text-xs font-mono pt-2 border-t border-slate-800">
            {evacueePieData.map((entry) => (
              <div key={entry.name} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }}></span>
                <span className="text-slate-300">
                  {entry.name}: <strong>{entry.value.toLocaleString()}</strong>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Chart 3: Road Corridor Utilization Distribution */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-400" />
                Road Capacity Utilization Distribution
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Frequency count of road segments across utilization tiers.
              </p>
            </div>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={roadUtilizationBuckets} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="bucket" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    fontSize: "12px",
                    color: "#f8fafc",
                  }}
                  formatter={(val: any) => [`${val} road segments`, "Count"]}
                />
                <Bar dataKey="count" name="Roads in Bucket" fill="#38bdf8" radius={[3, 3, 0, 0]}>
                  {roadUtilizationBuckets.map((_, i) => (
                    <Cell
                      key={`c-${i}`}
                      fill={i === 3 ? "#f59e0b" : i === 0 ? "#475569" : "#38bdf8"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Min-Cut Bottleneck Road Capacities */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                Critical Bottleneck Capacities (Cut Edges)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Roadways strictly spanning the (S*, T*) cut that bound the total evacuation rate.
              </p>
            </div>
          </div>

          <div className="h-60 w-full">
            {bottleneckData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={bottleneckData}
                  layout="vertical"
                  margin={{ top: 10, right: 20, left: 40, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="roadId" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "12px",
                      color: "#f8fafc",
                    }}
                    formatter={(val: any, name: any) => [`${val} p/h`, name]}
                  />
                  <Bar dataKey="capacity" name="Bottleneck Capacity" fill="#f43f5e" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                No physical road bottleneck edges found in cut.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
