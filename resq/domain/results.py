"""Typed output and trace data models for ResQ flow, min-cut, and comparison solvers."""

from dataclasses import dataclass, field

from resq.domain.exceptions import EntityNotFoundError


@dataclass(frozen=True, slots=True)
class EdgeFlowDetail:
    """Flow and capacity summary for a single directed physical road."""

    road_id: str
    road_name: str
    source_id: str
    target_id: str
    original_capacity: int
    nominal_capacity: int
    flow: int
    remaining_capacity: int
    utilization_ratio: float
    is_saturated: bool
    is_active: bool


@dataclass(frozen=True, slots=True)
class SourceFlowDetail:
    """Evacuation throughput summary for an affected-area source vertex."""

    node_id: str
    name: str
    population: int
    evacuated: int
    unmet_demand: int


@dataclass(frozen=True, slots=True)
class ShelterFlowDetail:
    """Intake utilization summary for a shelter destination vertex."""

    node_id: str
    name: str
    shelter_capacity: int
    assigned_flow: int
    remaining_capacity: int


@dataclass(frozen=True, slots=True)
class ResidualUpdateTrace:
    """Before/after residual capacity changes on one edge during path augmentation."""

    edge_id: str
    edge_kind: str
    traversed_from: str
    traversed_to: str
    used_reverse_edge: bool
    flow_delta: int
    forward_residual_before: int
    forward_residual_after: int
    reverse_residual_before: int
    reverse_residual_after: int


@dataclass(frozen=True, slots=True)
class AugmentationStepTrace:
    """Explainable record of a single DFS augmenting path push within a Dinic phase."""

    step_index: int
    phase_index: int
    selected_path: tuple[str, ...]
    path_edge_labels: tuple[str, ...]
    flow_sent: int
    edge_updates: tuple[ResidualUpdateTrace, ...]
    rerouted_via_reverse_edge: bool


@dataclass(frozen=True, slots=True)
class DinicPhaseTrace:
    """Explainable snapshot of one BFS level-graph phase and its DFS blocking flow."""

    phase_index: int
    sink_reachable: bool
    sink_level: int | None
    node_levels: dict[str, int]
    augmentations: tuple[AugmentationStepTrace, ...]
    phase_flow_pushed: int
    cumulative_flow: int


@dataclass(frozen=True, slots=True)
class DinicTrace:
    """Complete phase-by-phase educational trace of Dinic's Maximum Flow execution."""

    phases: tuple[DinicPhaseTrace, ...] = field(default_factory=tuple)
    total_phases_with_flow: int = 0
    total_augmentations: int = 0
    reverse_rerouting_steps: int = 0


@dataclass(frozen=True, slots=True)
class DinicResult:
    """Structured output returned by Dinic's Maximum Flow solver."""

    max_flow: int
    total_population: int
    total_shelter_capacity: int
    unmet_demand: int
    evacuation_rate: float
    road_flows: dict[str, EdgeFlowDetail]
    source_evacuations: dict[str, SourceFlowDetail]
    shelter_intakes: dict[str, ShelterFlowDetail]
    bfs_phases: int
    bfs_calls: int
    dfs_attempts: int
    useful_augmentations: int
    dfs_edge_scans: int
    execution_time_ns: int
    execution_time_ms: float
    algorithm_name: str = "Dinic's Maximum Flow"
    trace: DinicTrace | None = None

    def get_road_flow(self, road_id: str) -> EdgeFlowDetail:
        """Retrieve flow telemetry for a given road_id."""
        if road_id not in self.road_flows:
            raise EntityNotFoundError(
                f"Road '{road_id}' not found in DinicResult road_flows."
            )
        return self.road_flows[road_id]

    def saturated_roads(self) -> list[EdgeFlowDetail]:
        """Return all active positive-capacity roads with zero remaining capacity."""
        return [detail for detail in self.road_flows.values() if detail.is_saturated]


@dataclass(frozen=True, slots=True)
class MinCutEdgeDetail:
    """Original forward edge crossing from the reachable partition A to unreachable B."""

    edge_id: str
    edge_kind: str
    source_id: str
    target_id: str
    label: str
    original_capacity: int
    flow: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class MinCutResult:
    """Minimum S*-T* cut extracted from Dinic's saturated residual network."""

    max_flow: int
    total_cut_capacity: int
    reachable_vertices: tuple[str, ...]
    unreachable_vertices: tuple[str, ...]
    reachable_domain_nodes: tuple[str, ...]
    unreachable_domain_nodes: tuple[str, ...]
    cut_edges: tuple[MinCutEdgeDetail, ...]
    road_bottlenecks: tuple[MinCutEdgeDetail, ...]
    super_source_cuts: tuple[MinCutEdgeDetail, ...]
    shelter_capacity_cuts: tuple[MinCutEdgeDetail, ...]
    saturated_non_cut_roads: tuple[str, ...]
    road_cut_capacity: int
    super_source_cut_capacity: int
    shelter_cut_capacity: int


@dataclass(frozen=True, slots=True)
class GreedyStepDetail:
    """Single deterministic forward-only augmentation step of the Greedy baseline."""

    step_index: int
    selected_path: tuple[str, ...]
    path_edge_labels: tuple[str, ...]
    flow_sent: int
    cumulative_flow: int


@dataclass(frozen=True, slots=True)
class GreedyResult:
    """Structured output returned by the forward-only Greedy flow baseline."""

    rule: str
    max_flow: int
    total_population: int
    total_shelter_capacity: int
    unmet_demand: int
    evacuation_rate: float
    road_flows: dict[str, EdgeFlowDetail]
    source_evacuations: dict[str, SourceFlowDetail]
    shelter_intakes: dict[str, ShelterFlowDetail]
    augmentations: int
    paths_explored: int
    execution_time_ns: int
    execution_time_ms: float
    algorithm_name: str = "Greedy Baseline"
    steps: tuple[GreedyStepDetail, ...] | None = None


@dataclass(frozen=True, slots=True)
class EdgeComparisonDetail:
    """Road-level flow comparison between Dinic's optimal flow and Greedy baseline."""

    road_id: str
    road_name: str
    source_id: str
    target_id: str
    capacity: int
    dinic_flow: int
    greedy_flow: int
    flow_difference: int


@dataclass(frozen=True, slots=True)
class AlgorithmComparisonResult:
    """Head-to-head comparison between Dinic's Maximum Flow and a Greedy baseline."""

    dinic_result: DinicResult
    greedy_result: GreedyResult
    dinic_max_flow: int
    greedy_flow: int
    flow_difference: int
    optimality_gap_pct: float
    greedy_efficiency_ratio: float
    dinic_time_ns: int
    dinic_time_ms: float
    greedy_time_ns: int
    greedy_time_ms: float
    relative_speed_ratio: float
    benchmark_repeats: int
    road_comparisons: tuple[EdgeComparisonDetail, ...]
    rule_explanation: str


@dataclass(frozen=True, slots=True)
class ShortestPathRoute:
    """Single directed simple path ranked by total non-negative road distance."""

    rank: int
    source_id: str
    source_name: str
    shelter_id: str
    shelter_name: str
    total_distance: float
    node_path: tuple[str, ...]
    node_names: tuple[str, ...]
    road_ids: tuple[str, ...]
    road_names: tuple[str, ...]
    road_distances: tuple[float, ...]
    road_capacities: tuple[int, ...]
    bottleneck_capacity: int
    total_travel_time_min: float


@dataclass(frozen=True, slots=True)
class DijkstraResult:
    """Structured result from Dijkstra's shortest-path solver and alternative search."""

    source_id: str
    source_name: str
    shelter_id: str
    shelter_name: str
    reachable: bool
    shortest_route: ShortestPathRoute | None
    alternative_route: ShortestPathRoute | None
    distances_from_source: dict[str, float]
    relaxed_edges_count: int
    heap_pops: int
    vertex_count: int
    edge_count: int
    execution_time_ns: int
    execution_time_ms: float
    algorithm_name: str = "Dijkstra Shortest Path"
