"""Pydantic schemas for maximum flow, minimum cut, path decomposition, and playback."""

from typing import Any
from pydantic import BaseModel, Field


class RoadFlowDetailSchema(BaseModel):
    """Calculated flow metrics for one directed road corridor."""

    road_id: str
    road_name: str
    source_id: str
    target_id: str
    original_capacity: int
    effective_capacity: int
    flow: int
    remaining_capacity: int
    utilization_ratio: float
    is_saturated: bool
    is_active: bool


class SourceEvacuationDetailSchema(BaseModel):
    """Evacuation status of one affected area."""

    node_id: str
    name: str
    population: int
    evacuated: int
    unmet_demand: int
    completion_pct: float


class ShelterIntakeDetailSchema(BaseModel):
    """Shelter intake and capacity utilization."""

    node_id: str
    name: str
    shelter_capacity: int
    assigned_flow: int
    remaining_capacity: int
    utilization_pct: float


class CutEdgeSchema(BaseModel):
    """Edge spanning the S*-T* minimum cut partition."""

    edge_id: str
    source_id: str
    target_id: str
    original_capacity: int
    flow: int
    edge_kind: str  # "road", "super_sink", "super_source"


class MinCutResponse(BaseModel):
    """Minimum-cut partition and bottleneck diagnostics."""

    total_cut_capacity: int
    reachable_node_ids: list[str]
    unreachable_node_ids: list[str]
    road_bottlenecks: list[CutEdgeSchema]
    shelter_capacity_cuts: list[CutEdgeSchema]
    source_demand_cuts: list[CutEdgeSchema]
    saturated_non_cut_roads: list[str]
    road_cut_capacity: int
    shelter_cut_capacity: int
    super_source_cut_capacity: int


class DinicResponse(BaseModel):
    """Dinic's maximum-flow optimization results."""

    max_flow: int
    total_population: int
    total_shelter_capacity: int
    unmet_demand: int
    evacuation_rate: float
    execution_time_ms: float
    bfs_phases: int
    total_augmentations: int
    road_flows: list[RoadFlowDetailSchema]
    source_evacuations: list[SourceEvacuationDetailSchema]
    shelter_intakes: list[ShelterIntakeDetailSchema]
    phase_trace: list[dict[str, Any]] | None = None


class EvacuationRouteSchema(BaseModel):
    """Decomposed single-path evacuation corridor."""

    route_index: int
    source_id: str
    source_name: str
    shelter_id: str
    shelter_name: str
    node_path: list[str]
    road_ids: list[str]
    flow: int
    total_distance: float
    total_travel_time_min: float
    bottleneck_road_id: str = ""
    bottleneck_capacity: int = 0


class UpgradeCandidateSchema(BaseModel):
    """Marginal throughput gain from expanding a bottleneck."""

    target_id: str
    target_kind: str
    label: str
    current_capacity: int
    added_capacity: int
    base_max_flow: int
    new_max_flow: int
    marginal_flow_gain: int
    gain_per_unit: float


class WaveStepSchema(BaseModel):
    """Discrete hourly wave projection."""

    hour: int
    evacuated_this_hour: int
    cumulative_evacuated: int
    remaining_population: int
    remaining_shelter_capacity: int
    completion_pct: float


class FullAnalysisResponse(BaseModel):
    """Complete mathematical diagnostic snapshot."""

    dinic: DinicResponse
    min_cut: MinCutResponse
    routes: list[EvacuationRouteSchema]
    upgrade_candidates: list[UpgradeCandidateSchema]
    wave_timeline: list[WaveStepSchema]


class PlaybackFrameSchema(BaseModel):
    """Step-by-step frame state for animated flow playback."""

    step_index: int
    total_steps: int
    phase_index: int
    bfs_sink_level: int | None = None
    bfs_node_levels: dict[str, int]
    active_path_nodes: list[str]
    active_road_ids: list[str]
    rerouted_road_ids: list[str]
    flow_sent_this_step: int
    cumulative_flow: int
    road_flows: dict[str, int]
    road_remaining: dict[str, int]
    source_evacuated: dict[str, int]
    shelter_assigned: dict[str, int]
    explanation: str


class PlaybackResponse(BaseModel):
    """Array of playback frames with execution metadata."""

    total_frames: int
    max_flow: int
    bfs_phases: int
    total_augmentations: int
    frames: list[PlaybackFrameSchema]
