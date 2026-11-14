"""Mapping helpers between internal ResQ domain models and FastAPI Pydantic schemas."""

from resq.domain.models import EvacuationNetwork, Node, RoadEdge
from resq.domain.results import DinicResult, MinCutResult
from resq.domain.validation import ValidationReport
from resq.services.evacuation_simulator import FullAnalysisBundle
from resq.services.scenario_lab import ScenarioEvaluation

from backend.schemas.analysis import (
    CutEdgeSchema,
    DinicResponse,
    EvacuationRouteSchema,
    FullAnalysisResponse,
    MinCutResponse,
    RoadFlowDetailSchema,
    ShelterIntakeDetailSchema,
    SourceEvacuationDetailSchema,
    UpgradeCandidateSchema,
    WaveStepSchema,
)
from backend.schemas.network import (
    NetworkResponse,
    NodeResponse,
    RoadResponse,
    ValidationReportResponse,
)
from backend.schemas.scenarios import ScenarioEvaluationResponse


def node_to_response(node: Node) -> NodeResponse:
    """Convert a domain Node to NodeResponse schema."""
    return NodeResponse(
        node_id=node.node_id,
        name=node.name,
        node_type=node.node_type.value,
        population=node.population,
        shelter_capacity=node.shelter_capacity,
        x=node.x,
        y=node.y,
        metadata=dict(node.metadata),
    )


def road_to_response(road: RoadEdge) -> RoadResponse:
    """Convert a domain RoadEdge to RoadResponse schema."""
    return RoadResponse(
        road_id=road.road_id,
        source_id=road.source_id,
        target_id=road.target_id,
        capacity=road.capacity,
        effective_capacity=road.effective_capacity,
        name=road.name,
        distance=road.distance,
        travel_time_min=road.travel_time_min,
        is_active=road.is_active,
        metadata=dict(road.metadata),
    )


def network_to_response(network: EvacuationNetwork) -> NetworkResponse:
    """Convert an EvacuationNetwork to NetworkResponse schema."""
    return NetworkResponse(
        network_id=network.network_id,
        name=network.name,
        description=network.description,
        total_population=network.total_population,
        total_shelter_capacity=network.total_shelter_capacity,
        total_active_road_capacity=network.total_active_road_capacity,
        nodes=[node_to_response(n) for n in network.nodes.values()],
        roads=[road_to_response(r) for r in network.roads.values()],
        metadata=dict(network.metadata),
    )


def validation_to_response(report: ValidationReport, network: EvacuationNetwork) -> ValidationReportResponse:
    """Convert ValidationReport and network to ValidationReportResponse."""
    return ValidationReportResponse(
        is_valid=report.is_valid,
        errors=list(report.errors),
        warnings=list(report.warnings),
        affected_areas_count=len(network.affected_areas),
        junctions_count=len(network.junctions),
        shelters_count=len(network.shelters),
        roads_count=len(network.roads),
        total_population=network.total_population,
        total_shelter_capacity=network.total_shelter_capacity,
    )


def dinic_to_response(res: DinicResult) -> DinicResponse:
    """Convert DinicResult dataclass to DinicResponse schema."""
    road_flows = [
        RoadFlowDetailSchema(
            road_id=rf.road_id,
            road_name=rf.road_name,
            source_id=rf.source_id,
            target_id=rf.target_id,
            original_capacity=rf.original_capacity,
            effective_capacity=rf.nominal_capacity,
            flow=rf.flow,
            remaining_capacity=rf.remaining_capacity,
            utilization_ratio=rf.utilization_ratio,
            is_saturated=rf.is_saturated,
            is_active=rf.is_active,
        )
        for rf in res.road_flows.values()
    ]
    source_evacuations = [
        SourceEvacuationDetailSchema(
            node_id=s.node_id,
            name=s.name,
            population=s.population,
            evacuated=s.evacuated,
            unmet_demand=s.unmet_demand,
            completion_pct=(s.evacuated / s.population * 100.0) if s.population > 0 else 100.0,
        )
        for s in res.source_evacuations.values()
    ]
    shelter_intakes = [
        ShelterIntakeDetailSchema(
            node_id=sh.node_id,
            name=sh.name,
            shelter_capacity=sh.shelter_capacity,
            assigned_flow=sh.assigned_flow,
            remaining_capacity=sh.remaining_capacity,
            utilization_pct=(sh.assigned_flow / sh.shelter_capacity * 100.0) if sh.shelter_capacity > 0 else 0.0,
        )
        for sh in res.shelter_intakes.values()
    ]

    phase_trace_data: list[dict] | None = None
    if res.trace and res.trace.phases:
        phase_trace_data = [
            {
                "phase_index": p.phase_index,
                "sink_level": p.sink_level,
                "node_levels": p.node_levels,
                "phase_flow": p.phase_flow_pushed,
                "augmentations_count": len(p.augmentations),
            }
            for p in res.trace.phases
        ]

    return DinicResponse(
        max_flow=res.max_flow,
        total_population=res.total_population,
        total_shelter_capacity=res.total_shelter_capacity,
        unmet_demand=res.unmet_demand,
        evacuation_rate=res.evacuation_rate,
        execution_time_ms=res.execution_time_ms,
        bfs_phases=res.bfs_phases,
        total_augmentations=res.useful_augmentations,
        road_flows=road_flows,
        source_evacuations=source_evacuations,
        shelter_intakes=shelter_intakes,
        phase_trace=phase_trace_data,
    )


def min_cut_to_response(mc: MinCutResult) -> MinCutResponse:
    """Convert MinCutResult dataclass to MinCutResponse schema."""
    return MinCutResponse(
        total_cut_capacity=mc.total_cut_capacity,
        reachable_node_ids=list(mc.reachable_domain_nodes),
        unreachable_node_ids=list(mc.unreachable_domain_nodes),
        road_bottlenecks=[
            CutEdgeSchema(
                edge_id=e.edge_id,
                source_id=e.source_id,
                target_id=e.target_id,
                original_capacity=e.original_capacity,
                flow=e.flow,
                edge_kind=e.edge_kind,
            )
            for e in mc.road_bottlenecks
        ],
        shelter_capacity_cuts=[
            CutEdgeSchema(
                edge_id=e.edge_id,
                source_id=e.source_id,
                target_id=e.target_id,
                original_capacity=e.original_capacity,
                flow=e.flow,
                edge_kind=e.edge_kind,
            )
            for e in mc.shelter_capacity_cuts
        ],
        source_demand_cuts=[
            CutEdgeSchema(
                edge_id=e.edge_id,
                source_id=e.source_id,
                target_id=e.target_id,
                original_capacity=e.original_capacity,
                flow=e.flow,
                edge_kind=e.edge_kind,
            )
            for e in mc.super_source_cuts
        ],
        saturated_non_cut_roads=list(mc.saturated_non_cut_roads),
        road_cut_capacity=mc.road_cut_capacity,
        shelter_cut_capacity=mc.shelter_cut_capacity,
        super_source_cut_capacity=mc.super_source_cut_capacity,
    )


def bundle_to_response(bundle: FullAnalysisBundle) -> FullAnalysisResponse:
    """Convert FullAnalysisBundle to FullAnalysisResponse schema."""
    dinic_resp = dinic_to_response(bundle.dinic_result)
    min_cut_resp = min_cut_to_response(bundle.min_cut)

    routes_resp = []
    roads_map = bundle.network.roads
    for r in bundle.routes:
        dist = sum(roads_map[rid].distance for rid in r.road_ids if rid in roads_map)
        min_cap = min((roads_map[rid].capacity for rid in r.road_ids if rid in roads_map), default=0)
        bn_id = min((rid for rid in r.road_ids if rid in roads_map), key=lambda x: roads_map[x].capacity, default="")
        routes_resp.append(
            EvacuationRouteSchema(
                route_index=r.route_index,
                source_id=r.source_id,
                source_name=r.source_name,
                shelter_id=r.shelter_id,
                shelter_name=r.shelter_name,
                node_path=list(r.node_path),
                road_ids=list(r.road_ids),
                flow=r.flow,
                total_distance=round(dist, 2),
                total_travel_time_min=round(r.total_travel_time_min, 1),
                bottleneck_road_id=bn_id,
                bottleneck_capacity=min_cap,
            )
        )

    upgrades_resp = [
        UpgradeCandidateSchema(
            target_id=u.target_id,
            target_kind=u.target_kind,
            label=u.label,
            current_capacity=u.current_capacity,
            added_capacity=u.added_capacity,
            base_max_flow=u.base_max_flow,
            new_max_flow=u.new_max_flow,
            marginal_flow_gain=u.marginal_flow_gain,
            gain_per_unit=u.gain_per_unit,
        )
        for u in bundle.upgrade_candidates
    ]

    waves_resp = [
        WaveStepSchema(
            hour=w.hour,
            evacuated_this_hour=w.evacuated_this_hour,
            cumulative_evacuated=w.cumulative_evacuated,
            remaining_population=w.remaining_population,
            remaining_shelter_capacity=w.remaining_shelter_capacity,
            completion_pct=w.completion_pct,
        )
        for w in bundle.wave_timeline
    ]

    return FullAnalysisResponse(
        dinic=dinic_resp,
        min_cut=min_cut_resp,
        routes=routes_resp,
        upgrade_candidates=upgrades_resp,
        wave_timeline=waves_resp,
    )


def scenario_to_response(
    ev: ScenarioEvaluation,
    *,
    include_bundle: bool = False,
) -> ScenarioEvaluationResponse:
    """Convert ScenarioEvaluation to ScenarioEvaluationResponse."""
    d = ev.bundle.dinic_result
    mc = ev.bundle.min_cut
    return ScenarioEvaluationResponse(
        scenario_key=ev.scenario_key,
        scenario_name=ev.scenario_name,
        scenario_kind=ev.scenario_kind,
        description=ev.description,
        max_flow=d.max_flow,
        unmet_demand=d.unmet_demand,
        evacuation_rate=d.evacuation_rate,
        baseline_delta=ev.baseline_delta,
        baseline_delta_pct=ev.baseline_delta_pct,
        cut_capacity=mc.total_cut_capacity,
        bottleneck_roads_count=len(mc.road_bottlenecks),
        observations=list(ev.observations),
        network=network_to_response(ev.network),
        bundle=bundle_to_response(ev.bundle) if include_bundle else None,
    )
