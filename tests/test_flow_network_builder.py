"""Unit tests for Super-Source/Super-Sink FlowNetwork builder and residual capacity separation."""

import pytest

from resq import (
    EdgeKind,
    EvacuationNetwork,
    GraphValidationError,
    NodeType,
    SUPER_SINK_ID,
    SUPER_SOURCE_ID,
    build_evacuation_network,
)


def test_build_evacuation_network_creates_super_source_and_super_sink(
    sample_evacuation_network: EvacuationNetwork,
) -> None:
    flow_net = build_evacuation_network(sample_evacuation_network)

    # 6 domain nodes + 2 virtual endpoints (S*, T*)
    assert flow_net.num_nodes == 8
    assert flow_net.super_source_id == SUPER_SOURCE_ID
    assert flow_net.super_sink_id == SUPER_SINK_ID

    ss_edges = flow_net.get_super_source_edges()
    assert len(ss_edges) == 2
    assert flow_net.get_super_source_edge("A1").original_capacity == 600
    assert flow_net.get_super_source_edge("A2").original_capacity == 400

    st_edges = flow_net.get_super_sink_edges()
    assert len(st_edges) == 2
    assert flow_net.get_super_sink_edge("S1").original_capacity == 550
    assert flow_net.get_super_sink_edge("S2").original_capacity == 500

    road_edges = flow_net.get_road_edges()
    assert len(road_edges) == 9
    assert flow_net.get_road_edge("R5_MAIN").original_capacity == 350
    assert flow_net.get_road_edge("R5_ALT").original_capacity == 200
    flow_net.verify_flow_invariants()


def test_inactive_road_maps_to_zero_effective_capacity_keeping_nominal() -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=300)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=300)
    net.add_road("R1", "A1", "S1", 250, is_active=False)

    flow_net = build_evacuation_network(net)
    road_edge = flow_net.get_road_edge("R1")
    assert road_edge.original_capacity == 0
    assert road_edge.residual_capacity == 0
    assert road_edge.nominal_capacity == 250
    assert net.get_road("R1").capacity == 250


def test_original_capacities_remain_separate_from_residual_capacities() -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=100)
    net.add_node("J1", "Junction", NodeType.JUNCTION)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=120)
    # Deliberately name a road "A1" to verify no namespace collision with super_source edge "A1"
    net.add_road("A1", "A1", "J1", 80)
    net.add_road("R2", "J1", "S1", 70)

    flow_net = build_evacuation_network(net)
    before_snapshot = flow_net.snapshot_capacities()
    assert before_snapshot["super_source:A1"]["original_capacity"] == 100
    assert before_snapshot["road:A1"]["original_capacity"] == 80

    # Manually push 60 units along S* -> A1 -> J1 -> S1 -> T*
    ss_idx = flow_net.super_source_idx
    a1_idx = flow_net.node_to_index["A1"]
    j1_idx = flow_net.node_to_index["J1"]
    s1_idx = flow_net.node_to_index["S1"]

    def _find_edge_pos(u_idx: int, kind: EdgeKind, eid: str) -> int:
        for i, e in enumerate(flow_net.adj[u_idx]):
            if e.is_forward and e.edge_kind == kind and e.edge_id == eid:
                return i
        raise AssertionError("Expected edge not found")

    e_ss = _find_edge_pos(ss_idx, EdgeKind.SUPER_SOURCE, "A1")
    e_r1 = _find_edge_pos(a1_idx, EdgeKind.ROAD, "A1")
    e_r2 = _find_edge_pos(j1_idx, EdgeKind.ROAD, "R2")
    e_st = _find_edge_pos(s1_idx, EdgeKind.SUPER_SINK, "S1")

    flow_net.push_flow(ss_idx, e_ss, 60)
    flow_net.push_flow(a1_idx, e_r1, 60)
    flow_net.push_flow(j1_idx, e_r2, 60)
    flow_net.push_flow(s1_idx, e_st, 60)

    flow_net.verify_flow_invariants()
    assert flow_net.total_outflow_from_super_source() == 60
    assert flow_net.total_inflow_to_super_sink() == 60

    # Original capacities must be untouched while residual capacities reflect pushed flow
    ss_edge = flow_net.get_super_source_edge("A1")
    road1 = flow_net.get_road_edge("A1")
    road2 = flow_net.get_road_edge("R2")
    st_edge = flow_net.get_super_sink_edge("S1")

    assert ss_edge.original_capacity == 100
    assert ss_edge.residual_capacity == 40
    assert ss_edge.flow == 60

    assert road1.original_capacity == 80
    assert road1.residual_capacity == 20
    assert road1.flow == 60

    assert road2.original_capacity == 70
    assert road2.residual_capacity == 10
    assert road2.flow == 60

    assert st_edge.original_capacity == 120
    assert st_edge.residual_capacity == 60
    assert st_edge.flow == 60

    # Paired reverse edge must now carry 60 residual capacity for backward cancellation
    rev_road1 = flow_net.adj[road1.to][road1.rev]
    assert rev_road1.original_capacity == 0
    assert rev_road1.residual_capacity == 60
    assert rev_road1.flow == -60

    # Domain network remained untouched
    assert net.get_node("A1").population == 100
    assert net.get_road("A1").capacity == 80

    # Reset restores all residuals cleanly
    flow_net.reset_flows()
    assert flow_net.snapshot_capacities() == before_snapshot
    flow_net.verify_flow_invariants()


def test_cannot_push_flow_beyond_residual_capacity() -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=50)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=50)
    net.add_road("R1", "A1", "S1", 30)

    flow_net = build_evacuation_network(net)
    a1_idx = flow_net.node_to_index["A1"]
    pos = next(
        i for i, e in enumerate(flow_net.adj[a1_idx]) if e.is_forward and e.edge_id == "R1"
    )
    with pytest.raises(GraphValidationError):
        flow_net.push_flow(a1_idx, pos, 31)


def test_build_evacuation_network_requires_sources_and_shelters() -> None:
    no_shelter = EvacuationNetwork()
    no_shelter.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=100)
    with pytest.raises(GraphValidationError):
        build_evacuation_network(no_shelter)

    no_source = EvacuationNetwork()
    no_source.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=100)
    with pytest.raises(GraphValidationError):
        build_evacuation_network(no_source)
