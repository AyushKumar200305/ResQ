"""Shared flow telemetry extraction helpers for flow solvers."""

from dataclasses import dataclass

from resq.algorithms.residual_graph import FlowNetwork
from resq.domain.models import EvacuationNetwork
from resq.domain.results import (
    EdgeFlowDetail,
    ShelterFlowDetail,
    SourceFlowDetail,
)


@dataclass(frozen=True, slots=True)
class FlowTelemetryBundle:
    """Common road, source, and shelter breakdown derived from a solved FlowNetwork."""

    total_population: int
    total_shelter_capacity: int
    unmet_demand: int
    evacuation_rate: float
    road_flows: dict[str, EdgeFlowDetail]
    source_evacuations: dict[str, SourceFlowDetail]
    shelter_intakes: dict[str, ShelterFlowDetail]


def extract_flow_telemetry(
    flow_network: FlowNetwork,
    *,
    achieved_flow: int,
    domain_network: EvacuationNetwork | None = None,
) -> FlowTelemetryBundle:
    """Extract road, source, and shelter flow metrics from a FlowNetwork."""
    road_flows: dict[str, EdgeFlowDetail] = {}
    for edge in flow_network.get_road_edges():
        orig_cap = edge.original_capacity
        rem_cap = edge.residual_capacity
        flow_val = edge.flow
        util = (flow_val / orig_cap) if orig_cap > 0 else 0.0
        road_obj = (
            domain_network.roads.get(edge.edge_id)
            if domain_network is not None
            else None
        )
        road_flows[edge.edge_id] = EdgeFlowDetail(
            road_id=edge.edge_id,
            road_name=road_obj.name if road_obj is not None else "",
            source_id=edge.source_node_id,
            target_id=edge.target_node_id,
            original_capacity=orig_cap,
            nominal_capacity=edge.nominal_capacity,
            flow=flow_val,
            remaining_capacity=rem_cap,
            utilization_ratio=util,
            is_saturated=(orig_cap > 0 and rem_cap == 0),
            is_active=road_obj.is_active if road_obj is not None else (orig_cap > 0),
        )

    source_evacuations: dict[str, SourceFlowDetail] = {}
    total_population = 0
    for ss_edge in flow_network.get_super_source_edges():
        area_id = ss_edge.edge_id
        pop = ss_edge.original_capacity
        evac = ss_edge.flow
        total_population += pop
        node_obj = (
            domain_network.nodes.get(area_id)
            if domain_network is not None
            else None
        )
        source_evacuations[area_id] = SourceFlowDetail(
            node_id=area_id,
            name=node_obj.name if node_obj is not None else area_id,
            population=pop,
            evacuated=evac,
            unmet_demand=pop - evac,
        )

    shelter_intakes: dict[str, ShelterFlowDetail] = {}
    total_shelter_capacity = 0
    for st_edge in flow_network.get_super_sink_edges():
        shelter_id = st_edge.edge_id
        cap = st_edge.original_capacity
        assigned = st_edge.flow
        total_shelter_capacity += cap
        node_obj = (
            domain_network.nodes.get(shelter_id)
            if domain_network is not None
            else None
        )
        shelter_intakes[shelter_id] = ShelterFlowDetail(
            node_id=shelter_id,
            name=node_obj.name if node_obj is not None else shelter_id,
            shelter_capacity=cap,
            assigned_flow=assigned,
            remaining_capacity=cap - assigned,
        )

    unmet_demand = total_population - achieved_flow
    evacuation_rate = (achieved_flow / total_population) if total_population > 0 else 1.0

    return FlowTelemetryBundle(
        total_population=total_population,
        total_shelter_capacity=total_shelter_capacity,
        unmet_demand=unmet_demand,
        evacuation_rate=evacuation_rate,
        road_flows=road_flows,
        source_evacuations=source_evacuations,
        shelter_intakes=shelter_intakes,
    )
