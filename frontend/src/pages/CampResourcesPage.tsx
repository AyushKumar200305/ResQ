import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  Clock,
  Droplet,
  Edit3,
  HeartPulse,
  HelpCircle,
  Home,
  Info,
  PackageCheck,
  Pill,
  RefreshCw,
  RotateCcw,
  Save,
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
import type { ReliefAllocationData, ShelterReliefDemandData } from "../types/api";

interface ShelterInventoryForm {
  water_liters: number;
  food_rations: number;
  medical_supplies: number;
  blankets: number;
  medicines: number;
  hygiene_kits: number;
}

const RESOURCE_CONFIG = [
  { key: "water_liters" as const, label: "Clean Water", icon: Droplet, unit: "L", color: "text-blue-600" },
  { key: "food_rations" as const, label: "Food Rations", icon: Utensils, unit: "meals", color: "text-amber-600" },
  { key: "medical_supplies" as const, label: "Trauma Kits", icon: HeartPulse, unit: "kits", color: "text-red-600" },
  { key: "blankets" as const, label: "Bedding / Blankets", icon: Home, unit: "units", color: "text-indigo-600" },
  { key: "medicines" as const, label: "Essential Meds", icon: Pill, unit: "doses", color: "text-emerald-600" },
  { key: "hygiene_kits" as const, label: "Hygiene Packs", icon: Sparkles, unit: "packs", color: "text-purple-600" },
];

export const CampResourcesPage: React.FC = () => {
  const { reliefOverview, refreshRelief, addNotification } = useApp();

  const [planningDays, setPlanningDays] = useState<number>(3.0);
  const [allocationData, setAllocationData] = useState<ReliefAllocationData | null>(
    reliefOverview?.resources || null
  );
  const [isComputing, setIsComputing] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Selected shelter for inventory editing
  const [selectedShelterId, setSelectedShelterId] = useState<string>("");
  const [inventoryForm, setInventoryForm] = useState<ShelterInventoryForm>({
    water_liters: 0,
    food_rations: 0,
    medical_supplies: 0,
    blankets: 0,
    medicines: 0,
    hygiene_kits: 0,
  });

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Sync with global overview when ready
  useEffect(() => {
    if (reliefOverview?.resources && planningDays === 3.0 && !allocationData) {
      setAllocationData(reliefOverview.resources);
    }
  }, [reliefOverview, planningDays, allocationData]);

  const shelters: ShelterReliefDemandData[] = allocationData?.shelter_allocations || [];

  // Default selected shelter to the first available shelter if not set
  useEffect(() => {
    if (shelters.length > 0 && (!selectedShelterId || !shelters.find(s => s.shelter_id === selectedShelterId))) {
      setSelectedShelterId(shelters[0].shelter_id);
    }
  }, [shelters, selectedShelterId]);

  // Synchronize form when selected shelter changes or allocationData updates
  useEffect(() => {
    if (!selectedShelterId) return;
    const currentShelter = shelters.find((s) => s.shelter_id === selectedShelterId);
    if (currentShelter) {
      setInventoryForm({
        water_liters: currentShelter.resources.water_liters?.current_stock ?? 0,
        food_rations: currentShelter.resources.food_rations?.current_stock ?? 0,
        medical_supplies: currentShelter.resources.medical_supplies?.current_stock ?? 0,
        blankets: currentShelter.resources.blankets?.current_stock ?? 0,
        medicines: currentShelter.resources.medicines?.current_stock ?? 0,
        hygiene_kits: currentShelter.resources.hygiene_kits?.current_stock ?? 0,
      });
      setErrors({});
    }
  }, [selectedShelterId, allocationData]);

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

  // Handle inventory input change
  const handleInputChange = (field: keyof ShelterInventoryForm, valueString: string) => {
    const val = valueString === "" ? 0 : parseInt(valueString, 10);
    const newErrors = { ...errors };

    if (isNaN(val) || val < 0) {
      newErrors[field] = "Must be a non-negative whole number (≥ 0)";
    } else {
      delete newErrors[field];
    }
    setErrors(newErrors);

    setInventoryForm((prev) => ({
      ...prev,
      [field]: isNaN(val) ? 0 : Math.max(0, val),
    }));
  };

  // Reset form to currently saved shelter stock
  const handleResetForm = () => {
    const currentShelter = shelters.find((s) => s.shelter_id === selectedShelterId);
    if (currentShelter) {
      setInventoryForm({
        water_liters: currentShelter.resources.water_liters?.current_stock ?? 0,
        food_rations: currentShelter.resources.food_rations?.current_stock ?? 0,
        medical_supplies: currentShelter.resources.medical_supplies?.current_stock ?? 0,
        blankets: currentShelter.resources.blankets?.current_stock ?? 0,
        medicines: currentShelter.resources.medicines?.current_stock ?? 0,
        hygiene_kits: currentShelter.resources.hygiene_kits?.current_stock ?? 0,
      });
      setErrors({});
      addNotification("info", `Reset inventory form for ${currentShelter.shelter_name}.`);
    }
  };

  // Zero-out inventory for drill testing
  const handleZeroOut = () => {
    setInventoryForm({
      water_liters: 0,
      food_rations: 0,
      medical_supplies: 0,
      blankets: 0,
      medicines: 0,
      hygiene_kits: 0,
    });
    setErrors({});
  };

  // Save updated shelter inventory
  const handleSaveInventory = async () => {
    if (!selectedShelterId) return;

    // Validate all fields
    const invalidFields = Object.entries(inventoryForm).some(
      ([, v]) => typeof v !== "number" || isNaN(v) || v < 0
    );
    if (invalidFields || Object.keys(errors).length > 0) {
      addNotification("error", "Please fix invalid quantities before saving. All values must be non-negative.");
      return;
    }

    try {
      setIsSaving(true);
      const updatedAllocation = await api.updateShelterInventory(
        selectedShelterId,
        inventoryForm,
        planningDays
      );
      setAllocationData(updatedAllocation);
      await refreshRelief();
      const currentShelter = shelters.find((s) => s.shelter_id === selectedShelterId);
      addNotification(
        "success",
        `Physical inventory for ${currentShelter?.shelter_name || selectedShelterId} updated and camp allocations refreshed.`
      );
    } catch (err: any) {
      addNotification("error", `Failed to update shelter inventory: ${err.message || "Network error"}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Quick edit button from shelter card
  const handleQuickEdit = (shelterId: string) => {
    setSelectedShelterId(shelterId);
    const element = document.getElementById("edit-inventory-section");
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const selectedShelter = shelters.find((s) => s.shelter_id === selectedShelterId);
  const depotInitial = allocationData?.central_depot_inventory || {};
  const depotAllocated = allocationData?.total_allocated || {};
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

  const hasErrors = Object.keys(errors).length > 0;

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
              Shelter occupant intake forecasting, physical local stock management, gross demand estimation, and fair-share central depot distribution.
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
              disabled={isComputing || isSaving}
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

      {/* EDIT SHELTER INVENTORY SECTION */}
      <div id="edit-inventory-section" className="bg-white border border-blue-200 rounded-2xl p-6 space-y-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-700">
              <Edit3 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                Edit Shelter Physical Inventory
              </h2>
              <p className="text-[11px] text-slate-500">
                Enter physical supplies on-site at emergency camps. Changes automatically recalculate net deficits and depot allocations.
              </p>
            </div>
          </div>

          {/* Shelter Selector Dropdown */}
          <div className="flex items-center gap-2">
            <label htmlFor="shelter-select" className="text-xs font-semibold text-slate-600 whitespace-nowrap">
              Target Shelter:
            </label>
            <select
              id="shelter-select"
              value={selectedShelterId}
              onChange={(e) => setSelectedShelterId(e.target.value)}
              disabled={isSaving}
              aria-label="Target Shelter"
              className="bg-slate-50 border border-slate-300 rounded-xl px-3 py-1.5 text-xs font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {shelters.map((s) => (
                <option key={s.shelter_id} value={s.shelter_id}>
                  {s.shelter_name} ({s.shelter_id}) — {s.total_occupants_served} evacuees
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedShelter && (
          <div className="space-y-4">
            {/* Shelter Context Info Banner */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-slate-600" />
                <span className="font-semibold text-slate-700">
                  {selectedShelter.shelter_name} ({selectedShelter.shelter_id})
                </span>
                <span className="text-slate-400">|</span>
                <span className="text-slate-600">
                  Total Occupants: <strong className="text-slate-900">{selectedShelter.total_occupants_served.toLocaleString()}</strong> evacuees
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px] font-mono">
                <span className="text-slate-500">
                  Autonomy: <strong className="text-blue-700">{selectedShelter.minimum_autonomy_days.toFixed(1)} Days</strong>
                </span>
                <span className="text-slate-400">|</span>
                <span className="text-slate-500">
                  Deficit Alerts:{" "}
                  <strong className={selectedShelter.critical_shortages_count > 0 ? "text-amber-700 font-bold" : "text-emerald-700"}>
                    {selectedShelter.critical_shortages_count} items
                  </strong>
                </span>
              </div>
            </div>

            {/* 6 Resource Input Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {RESOURCE_CONFIG.map((res) => {
                const Icon = res.icon;
                const fieldKey = res.key;
                const currentVal = inventoryForm[fieldKey];
                const resData = selectedShelter.resources[fieldKey];
                const grossDemand = resData?.gross_demand || 0;
                const netDeficit = Math.max(0, grossDemand - currentVal);
                const hasFieldError = !!errors[fieldKey];

                return (
                  <div
                    key={fieldKey}
                    className={`p-3.5 rounded-xl border transition-all ${
                      hasFieldError
                        ? "bg-red-50/50 border-red-300"
                        : "bg-slate-50/70 border-slate-200 hover:border-blue-200"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                        <Icon className={`w-3.5 h-3.5 ${res.color}`} />
                        <span>{res.label}</span>
                      </div>
                      <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-600">
                        {res.unit}
                      </span>
                    </div>

                    {/* Numeric Input */}
                    <div className="space-y-1">
                      <label className="text-[10px] uppercase font-semibold text-slate-500 block">
                        Physical Stock On-Site:
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={currentVal}
                        onChange={(e) => handleInputChange(fieldKey, e.target.value)}
                        disabled={isSaving}
                        className={`w-full px-3 py-1.5 bg-white border rounded-lg text-xs font-mono font-bold text-slate-900 focus:outline-none focus:ring-2 ${
                          hasFieldError
                            ? "border-red-400 focus:ring-red-400"
                            : "border-slate-300 focus:ring-blue-500"
                        }`}
                        placeholder="0"
                      />
                      {hasFieldError && (
                        <p className="text-[10px] text-red-600 font-semibold mt-0.5">
                          {errors[fieldKey]}
                        </p>
                      )}
                    </div>

                    {/* Live Calculation Preview */}
                    <div className="mt-2.5 pt-2 border-t border-slate-200/80 text-[11px] font-mono space-y-1 text-slate-600">
                      <div className="flex justify-between">
                        <span>Gross Demand:</span>
                        <span className="font-bold text-slate-900">{grossDemand.toLocaleString()} {res.unit}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Net Deficit:</span>
                        <span className={`font-bold ${netDeficit > 0 ? "text-amber-700" : "text-emerald-700"}`}>
                          {netDeficit > 0 ? `-${netDeficit.toLocaleString()} ${res.unit}` : "0 (Covered)"}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleResetForm}
                  disabled={isSaving}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset to Saved Stock
                </button>
                <button
                  type="button"
                  onClick={handleZeroOut}
                  disabled={isSaving}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  Set All to 0 (Drill)
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveInventory}
                  disabled={isSaving || hasErrors}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {isSaving ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Saving &amp; Reallocating...
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5" />
                      Save &amp; Recalculate Allocation
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
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
          {RESOURCE_CONFIG.map((res) => {
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

                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => handleQuickEdit(shelter.shelter_id)}
                    className="px-2.5 py-1 rounded-lg border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                    title="Edit physical stock for this shelter"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Edit Inventory
                  </button>

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
                      <th className="py-3 px-3.5">Local Stock (On-Site)</th>
                      <th className="py-3 px-3.5">Gross Demand</th>
                      <th className="py-3 px-3.5">Net Deficit</th>
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
                      const hasDeficit = item.net_demand > 0;
                      return (
                        <tr key={resKey} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3 px-3.5 font-sans font-bold text-slate-900">
                            {item.resource_label}
                          </td>
                          <td className="py-3 px-3.5 text-blue-800 font-bold">
                            {item.current_stock.toLocaleString()} {item.unit}
                          </td>
                          <td className="py-3 px-3.5 text-slate-900 font-bold">
                            {item.gross_demand.toLocaleString()} {item.unit}
                          </td>
                          <td className={`py-3 px-3.5 font-bold ${hasDeficit ? "text-amber-700" : "text-emerald-700"}`}>
                            {hasDeficit ? `-${item.net_demand.toLocaleString()} ${item.unit}` : "0 (Covered)"}
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
