"""Transforms an EvacuationNetwork domain graph into an augmented FlowNetwork."""

from resq.algorithms.residual_graph import EdgeKind, FlowNetwork
from resq.domain.models import EvacuationNetwork
from resq.domain.validation import (
    SUPER_SINK_ID,
    SUPER_SOURCE_ID,
    validate_network_or_raise,
)


def build_evacuation_network(network: EvacuationNetwork) -> FlowNetwork:
    """Build an augmented Super-Source / Super-Sink FlowNetwork from an EvacuationNetwork.

    - Adds virtual Super-Source (S*) connected to each affected area s_i with capacity = s_i.population.
    - Adds all directed roads u -> v with capacity = road.effective_capacity (0 if inactive).
    - Adds virtual Super-Sink (T*) connected from each shelter t_j with capacity = t_j.shelter_capacity.
    - Leaves the input EvacuationNetwork completely unmodified.
    """
    validate_network_or_raise(network)

    flow_network = FlowNetwork(
        super_source_id=SUPER_SOURCE_ID,
        super_sink_id=SUPER_SINK_ID,
    )

    for node_id in network.nodes:
        flow_network.register_node(node_id)

    for area in network.affected_areas:
        flow_network.add_directed_edge(
            SUPER_SOURCE_ID,
            area.node_id,
            area.population,
            edge_id=area.node_id,
            edge_kind=EdgeKind.SUPER_SOURCE,
            nominal_capacity=area.population,
        )

    for road in network.roads.values():
        flow_network.add_directed_edge(
            road.source_id,
            road.target_id,
            road.effective_capacity,
            edge_id=road.road_id,
            edge_kind=EdgeKind.ROAD,
            nominal_capacity=road.capacity,
        )

    for shelter in network.shelters:
        flow_network.add_directed_edge(
            shelter.node_id,
            SUPER_SINK_ID,
            shelter.shelter_capacity,
            edge_id=shelter.node_id,
            edge_kind=EdgeKind.SUPER_SINK,
            nominal_capacity=shelter.shelter_capacity,
        )

    return flow_network
