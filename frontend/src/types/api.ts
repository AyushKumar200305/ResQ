/**
 * TypeScript type definitions mapping to ResQ FastAPI backend schemas.
 */

export type NodeType = "affected_area" | "junction" | "shelter";

export interface NodeData {
  node_id: string;
  name: string;
  node_type: NodeType;
  population: number;
  shelter_capacity: number;
  x?: number | null;
  y?: number | null;
  metadata?: Record<string, unknown>;
}

export interface RoadData {
  road_id: string;
  source_id: string;
  target_id: string;
  capacity: number;
  effective_capacity: number;
  name: string;
  distance: number;
  travel_time_min: number;
  is_active: boolean;
  metadata?: Record<string, unknown>;
}

export interface NetworkData {
  schema_version: string;
  network_id: string;
  name: string;
  description: string;
  total_population: number;
  total_shelter_capacity: number;
  total_active_road_capacity: number;
  nodes: NodeData[];
  roads: RoadData[];
  metadata?: Record<string, unknown>;
}

export interface ValidationReport {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  affected_areas_count: number;
  junctions_count: number;
  shelters_count: number;
  roads_count: number;
  total_population: number;
  total_shelter_capacity: number;
}

export interface PresetSummary {
  key: string;
  title: string;
  filename: string;
  summary: string;
}

export interface RoadFlowDetail {
  road_id: string;
  road_name: string;
  source_id: string;
  target_id: string;
  original_capacity: number;
  effective_capacity: number;
  flow: number;
  remaining_capacity: number;
  utilization_ratio: number;
  is_saturated: boolean;
  is_active: boolean;
}

export interface SourceEvacuationDetail {
  node_id: string;
  name: string;
  population: number;
  evacuated: number;
  unmet_demand: number;
  completion_pct: number;
}

export interface ShelterIntakeDetail {
  node_id: string;
  name: string;
  shelter_capacity: number;
  assigned_flow: number;
  remaining_capacity: number;
  utilization_pct: number;
}

export interface CutEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  original_capacity: number;
  flow: number;
  edge_kind: "road" | "super_sink" | "super_source" | string;
}

export interface MinCutData {
  total_cut_capacity: number;
  reachable_node_ids: string[];
  unreachable_node_ids: string[];
  road_bottlenecks: CutEdge[];
  shelter_capacity_cuts: CutEdge[];
  source_demand_cuts: CutEdge[];
  saturated_non_cut_roads: string[];
  road_cut_capacity: number;
  shelter_cut_capacity: number;
  super_source_cut_capacity: number;
}

export interface DinicPhaseTrace {
  phase_index: number;
  sink_level: number | null;
  node_levels: Record<string, number>;
  phase_flow: number;
  augmentations_count: number;
}

export interface DinicData {
  max_flow: number;
  total_population: number;
  total_shelter_capacity: number;
  unmet_demand: number;
  evacuation_rate: number;
  execution_time_ms: number;
  bfs_phases: number;
  total_augmentations: number;
  road_flows: RoadFlowDetail[];
  source_evacuations: SourceEvacuationDetail[];
  shelter_intakes: ShelterIntakeDetail[];
  phase_trace?: DinicPhaseTrace[] | null;
}

export interface EvacuationRoute {
  route_index: number;
  source_id: string;
  source_name: string;
  shelter_id: string;
  shelter_name: string;
  node_path: string[];
  road_ids: string[];
  flow: number;
  total_distance: number;
  total_travel_time_min: number;
  bottleneck_road_id: string;
  bottleneck_capacity: number;
}

export interface UpgradeCandidate {
  target_id: string;
  target_kind: "road" | "shelter" | string;
  label: string;
  current_capacity: number;
  added_capacity: number;
  base_max_flow: number;
  new_max_flow: number;
  marginal_flow_gain: number;
  gain_per_unit: number;
}

export interface WaveStep {
  hour: number;
  evacuated_this_hour: number;
  cumulative_evacuated: number;
  remaining_population: number;
  remaining_shelter_capacity: number;
  completion_pct: number;
}

export interface FullAnalysisData {
  dinic: DinicData;
  min_cut: MinCutData;
  routes: EvacuationRoute[];
  upgrade_candidates: UpgradeCandidate[];
  wave_timeline: WaveStep[];
}

export interface PlaybackFrame {
  step_index: number;
  total_steps: number;
  phase_index: number;
  bfs_sink_level: number | null;
  bfs_node_levels: Record<string, number>;
  active_path_nodes: string[];
  active_road_ids: string[];
  rerouted_road_ids: string[];
  flow_sent_this_step: number;
  cumulative_flow: number;
  road_flows: Record<string, number>;
  road_remaining: Record<string, number>;
  source_evacuated: Record<string, number>;
  shelter_assigned: Record<string, number>;
  explanation: string;
}

export interface PlaybackData {
  total_frames: number;
  max_flow: number;
  bfs_phases: number;
  total_augmentations: number;
  frames: PlaybackFrame[];
}

export interface ScenarioEvaluationData {
  scenario_key: string;
  scenario_name: string;
  scenario_kind: string;
  description: string;
  max_flow: number;
  unmet_demand: number;
  evacuation_rate: number;
  baseline_delta: number;
  baseline_delta_pct: number;
  cut_capacity: number;
  bottleneck_roads_count: number;
  observations: string[];
  network: NetworkData;
  bundle?: FullAnalysisData | null;
}

export interface ScenarioComparisonData {
  baseline_flow: number;
  scenarios: ScenarioEvaluationData[];
}

export interface EdgeComparisonDetail {
  edge_id: string;
  source_id: string;
  target_id: string;
  capacity: number;
  dinic_flow: number;
  greedy_flow: number;
  flow_delta: number;
}

export interface GreedyCompareData {
  dinic_max_flow: number;
  greedy_flow: number;
  flow_difference: number;
  optimality_gap_pct: number;
  dinic_time_ms: number;
  greedy_time_ms: number;
  greedy_rule: string;
  rule_explanation: string;
  edges: EdgeComparisonDetail[];
}

export interface BenchmarkTier {
  tier_name: string;
  vertices: number;
  edges: number;
  dinic_time_ms: number;
  greedy_time_ms: number;
  dinic_max_flow: number;
  greedy_flow: number;
  speedup_ratio: number;
}

export interface BenchmarkData {
  total_duration_sec: number;
  disclaimer: string;
  tiers: BenchmarkTier[];
}

export interface DijkstraRouteDetail {
  node_path: string[];
  road_ids: string[];
  total_distance: number;
  total_travel_time_min: number;
  bottleneck_capacity: number;
}

export interface DijkstraComparison {
  system_max_flow: number;
  source_population: number;
  source_dispatched_flow: number;
  shelter_capacity: number;
  shelter_received_flow: number;
  bottleneck_on_shortest_path: number;
  educational_takeaway: string;
}

export interface DijkstraData {
  source_id: string;
  shelter_id: string;
  is_reachable: boolean;
  execution_time_ms: number;
  relaxed_edges_count: number;
  heap_pops: number;
  shortest_route?: DijkstraRouteDetail | null;
  alternative_route?: DijkstraRouteDetail | null;
  comparison?: DijkstraComparison | null;
}

export interface HealthData {
  status: string;
  service: string;
  version: string;
  timestamp_utc: string;
  active_network: {
    network_id: string;
    name: string;
    nodes_count: number;
    roads_count: number;
    total_population: number;
    total_shelter_capacity: number;
  };
}

// User & Role State for emergency management entry
export type UserRole = "commander" | "coordinator" | "evaluator" | "guest";

export interface UserSession {
  name: string;
  role: UserRole;
  callsign: string;
  enteredAt: string;
}

// =====================================================================
// Disaster Evacuation Planning & Relief Management Types
// =====================================================================

export interface AreaPriorityData {
  area_id: string;
  area_name: string;
  population: number;
  hazard_severity: string;
  time_to_impact_hours: number;
  vulnerable_population: number;
  vulnerability_pct: number;
  outgoing_capacity: number;
  capacity_deficit: number;
  spans_minimum_cut: boolean;
  priority_score: number;
  priority_tier: "Critical" | "High" | "Moderate" | "Low";
  dispatch_order: number;
  explanation: string;
}

export interface RouteRecommendationData {
  route_id: string;
  source_id: string;
  source_name: string;
  shelter_id: string;
  shelter_name: string;
  is_primary: boolean;
  node_path: string[];
  road_ids: string[];
  total_distance_km: number;
  total_travel_time_min: number;
  bottleneck_capacity: number;
  hazard_risk_score: number;
  has_unverified_roads: boolean;
  has_hazard_roads: boolean;
  unverified_road_ids: string[];
  hazard_road_ids: string[];
  operational_advisory: string;
  recommendation_notes: string;
}

export interface ShelterAllocationStatusData {
  shelter_id: string;
  shelter_name: string;
  shelter_type: string;
  total_capacity: number;
  current_occupancy: number;
  available_capacity: number;
  expected_incoming: number;
  projected_total: number;
  saturation_pct: number;
  is_overcapacity: boolean;
  capacity_status: "AVAILABLE" | "NEAR_CAPACITY" | "SATURATED" | "OVERFLOW_RISK";
  serviced_area_ids: string[];
  feasible_route_count: number;
  estimated_hours_to_saturation?: number | null;
  operational_advisory: string;
}

export interface ShelterResourceItemData {
  resource: string;
  resource_label: string;
  unit: string;
  current_stock: number;
  gross_demand: number;
  net_demand: number;
  allocated_stock: number;
  final_stock: number;
  shortage: number;
  fulfillment_pct: number;
  days_of_autonomy: number;
  status: "SUFFICIENT" | "DEFICIT_WARNING" | "CRITICAL_SHORTAGE";
}

export interface ShelterReliefDemandData {
  shelter_id: string;
  shelter_name: string;
  total_occupants_served: number;
  resources: Record<string, ShelterResourceItemData>;
  critical_shortages_count: number;
  minimum_autonomy_days: number;
  shelter_priority_weight: number;
  explanation: string;
}

export interface ReliefAllocationData {
  planning_duration_days: number;
  total_population_served: number;
  central_depot_inventory: Record<string, number>;
  total_demand: Record<string, number>;
  total_allocated: Record<string, number>;
  total_shortages: Record<string, number>;
  shelter_allocations: ShelterReliefDemandData[];
  depot_remaining_inventory: Record<string, number>;
  allocation_heuristic_explanation: string;
  algorithm_clarification: string;
}

export interface ReliefOverviewData {
  priorities: AreaPriorityData[];
  routes: RouteRecommendationData[];
  shelters: ShelterAllocationStatusData[];
  resources: ReliefAllocationData;
  summary_advisories: string[];
  algorithm_clarification: string;
}
