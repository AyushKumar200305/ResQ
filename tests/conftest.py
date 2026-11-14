"""Shared test fixtures for ResQ graph model and flow network builder tests."""

import pytest

from resq.domain import EvacuationNetwork, NodeType


@pytest.fixture
def sample_evacuation_network() -> EvacuationNetwork:
    """Create a multi-source, multi-shelter network with parallel and two-way roads."""
    net = EvacuationNetwork(
        network_id="coastal-sector-1",
        name="Coastal Sector Evacuation Grid",
        description="Two affected zones routing through two junctions into two shelters.",
    )
    net.add_node(
        "A1",
        "Harbor Ward",
        NodeType.AFFECTED_AREA,
        population=600,
        x=0.0,
        y=1.0,
    )
    net.add_node(
        "A2",
        "Dockside District",
        NodeType.AFFECTED_AREA,
        population=400,
        x=0.0,
        y=-1.0,
    )
    net.add_node("J1", "North Overpass", NodeType.JUNCTION, x=2.0, y=0.8)
    net.add_node("J2", "South Interchange", NodeType.JUNCTION, x=2.0, y=-0.8)
    net.add_node(
        "S1",
        "Highland Arena",
        NodeType.SHELTER,
        shelter_capacity=550,
        x=4.0,
        y=1.0,
    )
    net.add_node(
        "S2",
        "Civic Complex",
        NodeType.SHELTER,
        shelter_capacity=500,
        x=4.0,
        y=-1.0,
    )

    net.add_road("R1", "A1", "J1", 450, name="Harbor Causeway", travel_time_min=12.0)
    net.add_road("R2", "A1", "J2", 250, name="Coastal Spur", travel_time_min=15.0)
    net.add_road("R3", "A2", "J2", 400, name="Dockside Avenue", travel_time_min=10.0)
    # Bidirectional cross-connector between junctions
    net.add_road("R4_N2S", "J1", "J2", 200, name="Crosslink Southbound")
    net.add_road("R4_S2N", "J2", "J1", 150, name="Crosslink Northbound")
    # Parallel roads from J1 to S1 with distinct identifiers
    net.add_road("R5_MAIN", "J1", "S1", 350, name="Highway 1 Express")
    net.add_road("R5_ALT", "J1", "S1", 200, name="Service Frontage Road")
    net.add_road("R6", "J2", "S2", 500, name="Civic Boulevard")
    net.add_road("R7", "J2", "S1", 150, name="Ridge Connector")
    return net
