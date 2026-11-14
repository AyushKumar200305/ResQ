/**
 * Unified API Client communicating with the ResQ FastAPI backend.
 */

import type {
  AreaPriorityData,
  BenchmarkData,
  DijkstraData,
  DinicData,
  FullAnalysisData,
  GreedyCompareData,
  HealthData,
  MinCutData,
  NetworkData,
  NodeData,
  PlaybackData,
  PresetSummary,
  ReliefAllocationData,
  ReliefOverviewData,
  RoadData,
  RouteRecommendationData,
  ScenarioComparisonData,
  ScenarioEvaluationData,
  ShelterAllocationStatusData,
  ValidationReport,
  WaveStep,
} from "../types/api";

const API_BASE = "http://localhost:8000";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let errorMsg = `Server responded with status ${res.status}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errorMsg = errorData.detail;
        }
      } catch {
        // use default error message
      }
      throw new Error(errorMsg);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error("Network error connecting to ResQ backend service.");
  }
}

export const api = {
  // System Health
  getHealth: () => request<HealthData>("/api/health"),

  // Network & Presets
  getCurrentNetwork: () => request<NetworkData>("/api/network"),
  createNetwork: (data: Partial<NetworkData>) =>
    request<NetworkData>("/api/network", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  loadDemoNetwork: () =>
    request<NetworkData>("/api/network/demo", {
      method: "POST",
    }),
  getPresets: () => request<PresetSummary[]>("/api/network/presets"),
  loadPreset: (key: string) =>
    request<NetworkData>(`/api/network/presets/${encodeURIComponent(key)}`, {
      method: "POST",
    }),
  validateNetwork: () => request<ValidationReport>("/api/network/validate"),

  // Node CRUD
  addNode: (node: Partial<NodeData>) =>
    request<NodeData>("/api/network/nodes", {
      method: "POST",
      body: JSON.stringify(node),
    }),
  updateNode: (nodeId: string, node: Partial<NodeData>) =>
    request<NodeData>(`/api/network/nodes/${encodeURIComponent(nodeId)}`, {
      method: "PUT",
      body: JSON.stringify(node),
    }),
  deleteNode: (nodeId: string, cascade = true) =>
    request<{ deleted_node_id: string }>(
      `/api/network/nodes/${encodeURIComponent(nodeId)}?cascade=${cascade}`,
      { method: "DELETE" }
    ),

  // Road CRUD
  addRoad: (road: Partial<RoadData>) =>
    request<RoadData>("/api/network/roads", {
      method: "POST",
      body: JSON.stringify(road),
    }),
  updateRoad: (roadId: string, road: Partial<RoadData>) =>
    request<RoadData>(`/api/network/roads/${encodeURIComponent(roadId)}`, {
      method: "PUT",
      body: JSON.stringify(road),
    }),
  deleteRoad: (roadId: string) =>
    request<{ deleted_road_id: string }>(
      `/api/network/roads/${encodeURIComponent(roadId)}`,
      { method: "DELETE" }
    ),

  // Solvers & Simulation
  runDinic: (trace = true) =>
    request<DinicData>(`/api/solve/dinic?trace=${trace}`, { method: "POST" }),
  getDinicResults: () => request<DinicData>("/api/solve/dinic"),
  runMinCut: () => request<MinCutData>("/api/solve/mincut", { method: "POST" }),
  getMinCutResults: () => request<MinCutData>("/api/solve/mincut"),
  runFullAnalysis: (waveHours = 8, upgradeDelta = 100) =>
    request<FullAnalysisData>(
      `/api/solve/full?wave_hours=${waveHours}&upgrade_delta=${upgradeDelta}`,
      { method: "POST" }
    ),
  getAlgorithmTrace: () => request<Record<string, unknown>>("/api/solve/trace"),
  getPlaybackFrames: () =>
    request<PlaybackData>("/api/solve/playback", { method: "POST" }),
  getWaveSimulation: (hours = 12) =>
    request<WaveStep[]>(`/api/solve/waves?hours=${hours}`, { method: "POST" }),

  // What-If Scenario Lab
  runBaselineScenario: () =>
    request<ScenarioEvaluationData>("/api/scenarios/baseline", {
      method: "POST",
    }),
  runRoadClosureScenario: (roadId: string, scenarioName?: string) =>
    request<ScenarioEvaluationData>("/api/scenarios/road-closure", {
      method: "POST",
      body: JSON.stringify({ road_id: roadId, scenario_name: scenarioName }),
    }),
  runReducedShelterScenario: (
    shelterId: string,
    newCapacity: number,
    scenarioName?: string
  ) =>
    request<ScenarioEvaluationData>("/api/scenarios/reduced-shelter", {
      method: "POST",
      body: JSON.stringify({
        shelter_id: shelterId,
        new_capacity: newCapacity,
        scenario_name: scenarioName,
      }),
    }),
  runIncreasedShelterScenario: (
    shelterId: string,
    addedCapacity: number,
    scenarioName?: string
  ) =>
    request<ScenarioEvaluationData>("/api/scenarios/increased-shelter", {
      method: "POST",
      body: JSON.stringify({
        shelter_id: shelterId,
        added_capacity: addedCapacity,
        scenario_name: scenarioName,
      }),
    }),
  runMultiRoadFailureScenario: (roadIds: string[], scenarioName?: string) =>
    request<ScenarioEvaluationData>("/api/scenarios/multi-road-failure", {
      method: "POST",
      body: JSON.stringify({ road_ids: roadIds, scenario_name: scenarioName }),
    }),
  runAllScenarios: () =>
    request<ScenarioComparisonData>("/api/scenarios/all", { method: "POST" }),

  // Algorithm Comparison & Benchmark
  compareGreedy: (rule = "shortest_hop", repeats = 3) =>
    request<GreedyCompareData>("/api/comparison/greedy", {
      method: "POST",
      body: JSON.stringify({ rule, repeats }),
    }),
  runBenchmark: (rule = "shortest_hop", repeats = 3) =>
    request<BenchmarkData>(
      `/api/comparison/benchmark?rule=${encodeURIComponent(rule)}&repeats=${repeats}`,
      { method: "POST" }
    ),

  // Dijkstra Shortest Path
  solveDijkstra: (sourceId: string, shelterId: string) =>
    request<DijkstraData>("/api/dijkstra/solve", {
      method: "POST",
      body: JSON.stringify({ source_id: sourceId, shelter_id: shelterId }),
    }),

  // Disaster Evacuation & Relief Management Endpoints
  getReliefOverview: () => request<ReliefOverviewData>("/api/relief/overview"),
  getAreaPriorities: () => request<AreaPriorityData[]>("/api/relief/priorities"),
  getRouteRecommendations: () =>
    request<RouteRecommendationData[]>("/api/relief/routes"),
  verifyRoadStatus: (payload: {
    road_id: string;
    new_status: string;
    hazard_risk_score?: number;
    verification_notes?: string;
  }) =>
    request<{ status: string; road_id: string; safety_status: string; message: string }>(
      "/api/relief/routes/verify",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),
  getShelterAllocations: () =>
    request<ShelterAllocationStatusData[]>("/api/relief/shelters"),
  getCampResources: (days = 3) =>
    request<ReliefAllocationData>(`/api/relief/resources?days=${days}`),
  computeCampResources: (payload: {
    planning_duration_days?: number;
    water_liters_per_person_day?: number;
    food_rations_per_person_day?: number;
    medical_supplies_per_person?: number;
    medicines_doses_per_person_day?: number;
    blankets_per_person?: number;
    hygiene_kits_per_person?: number;
    depot_stock_override?: Record<string, number>;
  }) =>
    request<ReliefAllocationData>("/api/relief/resources", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateShelterInventory: (
    shelterId: string,
    inventory: {
      water_liters: number;
      food_rations: number;
      medical_supplies: number;
      medicines: number;
      blankets: number;
      hygiene_kits: number;
    },
    days = 3
  ) =>
    request<ReliefAllocationData>(
      `/api/relief/shelters/${encodeURIComponent(shelterId)}/inventory?days=${days}`,
      {
        method: "PUT",
        body: JSON.stringify(inventory),
      }
    ),

  // Export URLs
  exportJsonUrl: `${API_BASE}/api/reports/json`,
  exportCsvRoadsUrl: `${API_BASE}/api/reports/csv/roads`,
  exportCsvScenariosUrl: `${API_BASE}/api/reports/csv/scenarios`,
  exportPdfUrl: `${API_BASE}/api/reports/pdf`,

  // File Download Helper
  downloadFile: async (url: string, filename: string) => {
    const fullUrl = url.startsWith("http") ? url : `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
    const res = await fetch(fullUrl);
    if (!res.ok) {
      throw new Error(`Failed to download report: HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },
};
