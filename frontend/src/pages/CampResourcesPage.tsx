import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  Clock,
  Droplet,
  HeartPulse,
  HelpCircle,
  Home,
  Info,
  PackageCheck,
  Pill,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Users,
  Utensils,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import type { ReliefAllocationData } from "../types/api";

export const CampResourcesPage: React.FC = () => {
  const { reliefOverview, isReliefLoading, refreshRelief, addNotification } = useApp();

  const [planningDays, setPlanningDays] = useState<number>(3.0);
  const [allocationData, setAllocationData] = useState<ReliefAllocationData | null>(
    reliefOverview?.resources || null
  );
  const [isComputing, setIsComputing] = useState<boolean>(false);

  // Sync with global overview when ready
  useEffect(() => {
    if (reliefOverview?.resources && planningDays === 3.0) {
      setAllocationData(reliefOverview.resources);
    }
  }, [reliefOverview, planningDays]);

  // Handle duration change
  const handleDurationChange = async (days: number) => {
    setPlanningDays(days);
    try {
      setIsComputing(true);
      const res = await api.getCampResources(days);
      setAllocationData(res);
      addNotification("info", `Recalculated camp requirements for ${days}-day planning horizon.`);
    } catch (err: any) {
      addNotification("error", `Failed to calculate resources: ${err.message}`);
    } finally {
      setIsComputing(false);
    }
  };

  const shelters = allocationData?.shelter_allocations || [];
  const depotInitial = allocationData?.central_depot_inventory || {};
  const depotAllocated = allocationData?.total_allocated || {};
  const depotRemaining = allocationData?.depot_remaining_inventory || {};
  const totalDemand = allocationData?.total_demand || {};
  const totalShortages = allocationData?.total_shortages || {};

  const resourceChartData = [
    { name: "Clean Water", demand: totalDemand.water_liters || 0, stock: depotInitial.water_liters || 0, allocated: depotAllocated.water_liters || 0, unit: "L" },
    { name: "Food Rations", demand: totalDemand.food_rations || 0, stock: depotInitial.food_rations || 0, allocated: depotAllocated.food_rations || 0, unit: "meals" },
    { name: "Trauma Kits", demand: totalDemand.medical_supplies || 0, stock: depotInitial.medical_supplies || 0, allocated: depotAllocated.medical_supplies || 0, unit: "kits" },
    { name: "Meds", demand: totalDemand.medicines || 0, stock: depotInitial.medicines || 0, allocated: depotAllocated.medicines || 0, unit: "doses" },
    { name: "Bedding", demand: totalDemand.blankets || 0, stock: depotInitial.blankets || 0, allocated: depotAllocated.blankets || 0, unit: "units" },
    { name: "Hygiene", demand: totalDemand.hygiene_kits || 0, stock: depotInitial.hygiene_kits || 0, allocated: depotAllocated.hygiene_kits || 0, unit: "packs" },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 shrink-0 mt-0.5 shadow-xs">
            <Boxes className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Camp Resources &amp; Supply Allocation</h1>
              <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                SPHERE HUMANITARIAN STANDARDS
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Shelter occupant intake forecasting, multi-resource gross demand calculation, and fair-share central depot distribution.
            </p>
          </div>
        </div>

        {/* Planning Duration Selector */}
        <div className="flex items-center gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-200 text-xs shadow-xs">
          <span className="text-slate-500 font-semibold px-2">Planning Window:</span>
          {[3, 5, 7].map((days) => (
            <button
              key={days}
              onClick={() => handleDurationChange(days)}
              disabled={isComputing}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all ${
                planningDays === days
                  ? "bg-amber-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
              }`}
            >
              {days} Days
            </button>
          ))}
        </div>
      </div>

      {/* Regional Warehouse Depot Status Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <PackageCheck className="w-4 h-4 text-blue-600" />
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Central Regional Depot &amp; Aggregate Demand ({planningDays}-Day Horizon)
              </h2>
            </div>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Configured Rates: Water (15 L/person/day), Food (3 meals/day), Trauma Kits (0.05 kits/person = 1 per 20 evacuees; 113 total for 2,250 evacuees), Meds (2 doses/day), Bedding (1/person), Hygiene (0.2/person).
            </p>
          </div>
          <span className="text-[11px] text-slate-500 font-mono font-medium">
            Total Evacuees Accommodated: <strong className="text-slate-900 font-bold">{allocationData?.total_population_served.toLocaleString() || 0}</strong>
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {[
            { key: "water_liters", label: "Clean Water", icon: Droplet, unit: "L" },
            { key: "food_rations", label: "Food Rations", icon: Utensils, unit: "meals" },
            { key: "medical_supplies", label: "Trauma Kits", icon: HeartPulse, unit: "kits" },
            { key: "medicines", label: "Essential Meds", icon: Pill, unit: "doses" },
            { key: "blankets", label: "Bedding / Blankets", icon: Home, unit: "units" },
            { key: "hygiene_kits", label: "Hygiene Packs", icon: Sparkles, unit: "packs" },
          ].map((res) => {
            const Icon = res.icon;
            const initial = depotInitial[res.key] || 0;
            const demand = totalDemand[res.key] || 0;
            const allocated = depotAllocated[res.key] || 0;
            const shortage = totalShortages[res.key] || 0;
            const isDeficit = shortage > 0;

            return (
              <div
                key={res.key}
                className={`p-3.5 rounded-xl border bg-slate-50/70 ${
                  isDeficit ? "border-amber-200" : "border-slate-200"
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs text-slate-900 font-bold mb-1.5">
                  <Icon className="w-3.5 h-3.5 text-blue-600" />
                  <span className="truncate">{res.label}</span>
                </div>
                <div className="text-[11px] space-y-1 font-mono font-medium">
                  <div className="flex justify-between text-slate-500">
                    <span>Demand:</span>
                    <span className="text-slate-900 font-bold">{demand.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>Depot Stock:</span>
                    <span className="text-blue-700 font-bold">{initial.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>Allocated:</span>
                    <span className="text-emerald-700 font-bold">{allocated.toLocaleString()}</span>
                  </div>
                  {isDeficit && (
                    <div className="flex justify-between text-red-600 font-bold pt-1.5 border-t border-amber-200">
                      <span>Deficit:</span>
                      <span>-{shortage.toLocaleString()} {res.unit}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Regional Supply Balance Chart */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Boxes className="w-4 h-4 text-amber-600" />
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Regional Supply Balance: Gross Demand vs. Central Depot Stock vs. Allocated
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-500 font-medium">
            {planningDays}-Day Humanitarian Planning Window
          </span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={resourceChartData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: "#ffffff", borderColor: "#cbd5e1", borderRadius: "0.75rem", fontSize: "12px", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                formatter={(value: any, name: any, item: any) => [`${Number(value).toLocaleString()} ${item.payload.unit}`, name]}
              />
              <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
              <Bar dataKey="demand" fill="#dc2626" radius={[4, 4, 0, 0]} name="Gross Demand" />
              <Bar dataKey="stock" fill="#2563eb" radius={[4, 4, 0, 0]} name="Depot Stock" />
              <Bar dataKey="allocated" fill="#059669" radius={[4, 4, 0, 0]} name="Allocated to Camps" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Individual Shelter Cards */}
      <div className="space-y-4">
        {shelters.map((shelter) => {
          return (
            <div
              key={shelter.shelter_id}
              className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4"
            >
              {/* Shelter Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3.5 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold shrink-0">
                    <Home className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-bold text-slate-900 tracking-tight">{shelter.shelter_name}</h2>
                      <span className="text-[11px] font-mono text-slate-500 font-medium">[{shelter.shelter_id}]</span>
                    </div>
                    <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                      Total Occupants Accommodated: <strong className="text-slate-900">{shelter.total_occupants_served.toLocaleString()} evacuees</strong>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-bold px-3 py-1 rounded-full border ${
                      shelter.critical_shortages_count > 0
                        ? "bg-amber-50 text-amber-800 border-amber-200"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200"
                    }`}
                  >
                    {shelter.critical_shortages_count > 0
                      ? `${shelter.critical_shortages_count} DEFICIT ALERTS`
                      : "ALL SUPPLIES SUFFICIENT"}
                  </span>
                  <div className="text-right hidden sm:block font-mono text-xs">
                    <span className="text-[10px] text-slate-500 block font-medium">Min Autonomy</span>
                    <span className="font-bold text-blue-700">{shelter.minimum_autonomy_days.toFixed(1)} Days</span>
                  </div>
                </div>
              </div>

              {/* Supply Requirements & Allocation Table */}
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-mono font-bold border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-3.5">Resource Item</th>
                      <th className="py-3 px-3.5">Local Stock</th>
                      <th className="py-3 px-3.5">Gross Demand</th>
                      <th className="py-3 px-3.5">Allocated from Depot</th>
                      <th className="py-3 px-3.5">Final Camp Stock</th>
                      <th className="py-3 px-3.5">Unmet Shortage</th>
                      <th className="py-3 px-3.5">Autonomy</th>
                      <th className="py-3 px-3.5 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {Object.entries(shelter.resources).map(([resKey, item]) => {
                      const isShort = item.shortage > 0;
                      return (
                        <tr key={resKey} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3 px-3.5 font-sans font-bold text-slate-900">
                            {item.resource_label}
                          </td>
                          <td className="py-3 px-3.5 text-slate-600">
                            {item.current_stock.toLocaleString()} {item.unit}
                          </td>
                          <td className="py-3 px-3.5 text-slate-900 font-bold">
                            {item.gross_demand.toLocaleString()} {item.unit}
                          </td>
                          <td className="py-3 px-3.5 text-emerald-700 font-bold">
                            +{item.allocated_stock.toLocaleString()} {item.unit}
                          </td>
                          <td className="py-3 px-3.5 text-blue-700 font-bold">
                            {item.final_stock.toLocaleString()} {item.unit}
                          </td>
                          <td className={`py-3 px-3.5 font-bold ${isShort ? "text-red-600" : "text-slate-400"}`}>
                            {isShort ? `-${item.shortage.toLocaleString()} ${item.unit}` : "0 (Fulfilled)"}
                          </td>
                          <td className="py-3 px-3.5 text-slate-700 font-medium">
                            {item.days_of_autonomy.toFixed(1)} Days
                          </td>
                          <td className="py-3 px-3.5 text-right">
                            <span
                              className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                                item.status === "SUFFICIENT"
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : item.status === "DEFICIT_WARNING"
                                  ? "bg-amber-50 text-amber-800 border-amber-200"
                                  : "bg-red-50 text-red-700 border-red-200"
                              }`}
                            >
                              {item.status.replace(/_/g, " ")}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* "Why?" Clear Explanation */}
              <div className="p-3.5 bg-blue-50/60 border border-blue-100 rounded-xl text-xs flex items-start gap-2.5">
                <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-bold text-blue-900 block text-[11px]">Why this allocation?</span>
                  <p className="text-slate-700 leading-relaxed text-xs">{shelter.explanation}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Algorithmic Clarification & Methodology Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-2 shadow-xs">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-900 uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Heuristic Transparency &amp; Algorithmic Independence</span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {allocationData?.allocation_heuristic_explanation}
        </p>
        <p className="text-[11px] text-slate-500 font-mono leading-relaxed pt-2 border-t border-slate-100">
          {allocationData?.algorithm_clarification}
        </p>
      </div>
    </div>
  );
};