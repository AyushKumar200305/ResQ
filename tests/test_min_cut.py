"""Unit and property tests for Minimum Cut extraction and bottleneck classification."""

import random
import pytest

from resq import (
    EvacuationNetwork,
    GraphValidationError,
    NodeType,
    SUPER_SINK_ID,
    SUPER_SOURCE_ID,
    build_evacuation_network,
    extract_min_cut,
    solve_max_flow_and_min_cut,
)


def test_min_cut_clrs_equals_max_flow() -> None:
    net = EvacuationNetwork()
    net.add_node("S", "Source", NodeType.AFFECTED_AREA, population=100)
    for vid in ("V1", "V2", "V3", "V4"):
        net.add_node(vid, vid, NodeType.JUNCTION)
    net.add_node("T", "Shelter", NodeType.SHELTER, shelter_capacity=100)

    net.add_road("E_S_V1", "S", "V1", 16)
    net.add_road("E_S_V2", "S", "V2", 13)
    net.add_road("E_V1_V3", "V1", "V3", 12)
    net.add_road("E_V2_V1", "V2", "V1", 4)
    net.add_road("E_V2_V4", "V2", "V4", 14)
    net.add_road("E_V3_V2", "V3", "V2", 9)
    net.add_road("E_V3_T", "V3", "T", 20)
    net.add_road("E_V4_V3", "V4", "V3", 7)
    net.add_road("E_V4_T", "V4", "T", 4)

    dinic_res, min_cut = solve_max_flow_and_min_cut(net)
    assert dinic_res.max_flow == 23
    assert min_cut.total_cut_capacity == 23
    assert SUPER_SOURCE_ID in min_cut.reachable_vertices
    assert SUPER_SINK_ID in min_cut.unreachable_vertices
    assert SUPER_SOURCE_ID not in min_cut.reachable_domain_nodes
    assert SUPER_SINK_ID not in min_cut.unreachable_domain_nodes
    assert {e.edge_id for e in min_cut.road_bottlenecks} == {
        "E_V1_V3",
        "E_V4_V3",
        "E_V4_T",
    }


def test_min_cut_separates_road_source_and_shelter_bottlenecks() -> None:
    """Verify distinct separation of road bottlenecks, shelter limits, and demand caps."""
    net = EvacuationNetwork(network_id="mixed-cuts", name="Mixed Bottlenecks")
    # Branch 1: Shelter S1 cap (120) < Road R1 (150) & R3 (400) -> shelter capacity cut
    net.add_node("A1", "Zone 1", NodeType.AFFECTED_AREA, population=500)
    net.add_node("J1", "Junction 1", NodeType.JUNCTION)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=120)
    net.add_road("R1", "A1", "J1", 150)
    net.add_road("R3", "J1", "S1", 400)

    # Branch 2: Demand at A2 (100) < Road R2 (300) & S2 (300) -> super-source cut
    net.add_node("A2", "Zone 2", NodeType.AFFECTED_AREA, population=100)
    net.add_node("S2", "Shelter 2", NodeType.SHELTER, shelter_capacity=300)
    net.add_road("R2", "A2", "S2", 300)

    # Branch 3: Road R4 (90) < Demand A3 (400) & Shelter S3 (500) -> road bottleneck
    net.add_node("A3", "Zone 3", NodeType.AFFECTED_AREA, population=400)
    net.add_node("S3", "Shelter 3", NodeType.SHELTER, shelter_capacity=500)
    net.add_road("R4", "A3", "S3", 90)

    dinic_res, min_cut = solve_max_flow_and_min_cut(net)
    assert dinic_res.max_flow == 310
    assert min_cut.total_cut_capacity == 310

    assert [e.edge_id for e in min_cut.road_bottlenecks] == ["R4"]
    assert [e.edge_id for e in min_cut.shelter_capacity_cuts] == ["S1"]
    assert [e.edge_id for e in min_cut.super_source_cuts] == ["A2"]

    assert min_cut.road_cut_capacity == 90
    assert min_cut.shelter_cut_capacity == 120
    assert min_cut.super_source_cut_capacity == 100
    assert (
        min_cut.road_cut_capacity
        + min_cut.shelter_cut_capacity
        + min_cut.super_source_cut_capacity
        == min_cut.total_cut_capacity
    )


def test_saturated_non_cut_roads_are_not_reported_as_min_cut_edges() -> None:
    """Ensure saturated roads internal to partition B (or A) are excluded from min-cut."""
    net = EvacuationNetwork()
    net.add_node("A1", "Zone 1", NodeType.AFFECTED_AREA, population=100)
    net.add_node("J1", "Junction 1", NodeType.JUNCTION)
    net.add_node("J2", "Junction 2", NodeType.JUNCTION)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=100)

    # Both R_A1_J1 and R_J1_S1 saturate at 20, yet J1 and S1 are both unreachable from S*.
    net.add_road("R_A1_J1", "A1", "J1", 20)
    net.add_road("R_J1_S1", "J1", "S1", 20)
    net.add_road("R_A1_J2", "A1", "J2", 30)
    net.add_road("R_J2_S1", "J2", "S1", 100)

    dinic_res, min_cut = solve_max_flow_and_min_cut(net)
    assert dinic_res.max_flow == 50
    assert min_cut.total_cut_capacity == 50

    assert set(min_cut.reachable_domain_nodes) == {"A1"}
    assert set(min_cut.unreachable_domain_nodes) == {"J1", "J2", "S1"}
    assert {e.edge_id for e in min_cut.road_bottlenecks} == {"R_A1_J1", "R_A1_J2"}
    assert "R_J1_S1" not in {e.edge_id for e in min_cut.cut_edges}
    assert "R_J1_S1" in min_cut.saturated_non_cut_roads


def test_extract_min_cut_rejects_unsolved_network() -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Zone", NodeType.AFFECTED_AREA, population=50)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=50)
    net.add_road("R1", "A1", "S1", 50)

    flow_net = build_evacuation_network(net)
    with pytest.raises(GraphValidationError):
        extract_min_cut(flow_net)


@pytest.mark.parametrize("seed", range(20))
def test_min_cut_invariant_across_random_graphs(seed: int) -> None:
    rng = random.Random(100 + seed)
    net = EvacuationNetwork(network_id=f"mc-{seed}", name=f"MC {seed}")

    node_ids: list[str] = []
    for i in range(rng.randint(1, 3)):
        nid = f"A_{i}"
        net.add_node(nid, nid, NodeType.AFFECTED_AREA, population=rng.randint(0, 300))
        node_ids.append(nid)
    for i in range(rng.randint(2, 5)):
        nid = f"J_{i}"
        net.add_node(nid, nid, NodeType.JUNCTION)
        node_ids.append(nid)
    for i in range(rng.randint(1, 3)):
        nid = f"S_{i}"
        net.add_node(nid, nid, NodeType.SHELTER, shelter_capacity=rng.randint(0, 300))
        node_ids.append(nid)

    for e_idx in range(rng.randint(6, 20)):
        u, v = rng.sample(node_ids, 2)
        net.add_road(f"R_{e_idx}", u, v, rng.randint(0, 200))

    dinic_res, min_cut = solve_max_flow_and_min_cut(net)
    assert min_cut.total_cut_capacity == dinic_res.max_flow
    assert (
        min_cut.road_cut_capacity
        + min_cut.super_source_cut_capacity
        + min_cut.shelter_cut_capacity
        == min_cut.total_cut_capacity
    )
    all_domain = set(net.nodes.keys())
    assert set(min_cut.reachable_domain_nodes) | set(min_cut.unreachable_domain_nodes) == all_domain
    assert set(min_cut.reachable_domain_nodes).isdisjoint(set(min_cut.unreachable_domain_nodes))
