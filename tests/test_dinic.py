"""Unit and property tests for Dinic's Maximum Flow implementation."""

from collections import deque
import random
import pytest

from resq import (
    DinicSolver,
    EvacuationNetwork,
    NodeType,
    SUPER_SINK_ID,
    SUPER_SOURCE_ID,
    build_evacuation_network,
    solve_max_flow_dinic,
)


def _reference_edmonds_karp(network: EvacuationNetwork) -> int:
    """Independent BFS augmenting-path reference used strictly inside tests."""
    flow_net = build_evacuation_network(network)
    n = flow_net.num_nodes
    src = flow_net.super_source_idx
    snk = flow_net.super_sink_idx
    adj = flow_net.adj

    total = 0
    while True:
        parent_node = [-1] * n
        parent_edge = [-1] * n
        parent_node[src] = src
        q = deque([src])

        while q and parent_node[snk] == -1:
            u = q.popleft()
            for idx, edge in enumerate(adj[u]):
                if edge.residual_capacity > 0 and parent_node[edge.to] == -1:
                    parent_node[edge.to] = u
                    parent_edge[edge.to] = idx
                    q.append(edge.to)

        if parent_node[snk] == -1:
            break

        bottleneck = None
        v = snk
        while v != src:
            u = parent_node[v]
            cap = adj[u][parent_edge[v]].residual_capacity
            bottleneck = cap if bottleneck is None else min(bottleneck, cap)
            v = u
        assert bottleneck is not None and bottleneck > 0

        v = snk
        while v != src:
            u = parent_node[v]
            flow_net.push_flow(u, parent_edge[v], bottleneck)
            v = u
        total += bottleneck

    flow_net.verify_flow_invariants()
    return total


def test_dinic_clrs_classic_graph() -> None:
    """Classic 6-vertex CLRS max-flow benchmark (exact optimal flow = 23)."""
    net = EvacuationNetwork(network_id="clrs", name="CLRS Classic Graph")
    net.add_node("S", "Source District", NodeType.AFFECTED_AREA, population=100)
    for vid in ("V1", "V2", "V3", "V4"):
        net.add_node(vid, f"Junction {vid}", NodeType.JUNCTION)
    net.add_node("T", "Central Shelter", NodeType.SHELTER, shelter_capacity=100)

    net.add_road("E_S_V1", "S", "V1", 16)
    net.add_road("E_S_V2", "S", "V2", 13)
    net.add_road("E_V1_V3", "V1", "V3", 12)
    net.add_road("E_V2_V1", "V2", "V1", 4)
    net.add_road("E_V2_V4", "V2", "V4", 14)
    net.add_road("E_V3_V2", "V3", "V2", 9)
    net.add_road("E_V3_T", "V3", "T", 20)
    net.add_road("E_V4_V3", "V4", "V3", 7)
    net.add_road("E_V4_T", "V4", "T", 4)

    result = solve_max_flow_dinic(net, trace=False)
    assert result.max_flow == 23
    assert result.unmet_demand == 77
    assert result.trace is None
    assert result.bfs_phases >= 1
    assert result.useful_augmentations >= 1
    assert result.dfs_attempts >= result.useful_augmentations
    assert result.execution_time_ns >= 0

    for detail in result.road_flows.values():
        assert 0 <= detail.flow <= detail.original_capacity
        assert detail.remaining_capacity == detail.original_capacity - detail.flow


def test_dinic_multi_source_multi_shelter_and_capacity_bounds(
    sample_evacuation_network: EvacuationNetwork,
) -> None:
    result = solve_max_flow_dinic(sample_evacuation_network, trace=True)
    assert result.max_flow == 1000
    assert result.total_population == 1000
    assert result.unmet_demand == 0
    assert result.evacuation_rate == pytest.approx(1.0)
    assert result.source_evacuations["A1"].evacuated == 600
    assert result.source_evacuations["A2"].evacuated == 400
    assert (
        result.shelter_intakes["S1"].assigned_flow
        + result.shelter_intakes["S2"].assigned_flow
        == 1000
    )

    # Tighten shelter S1 capacity and disable expressway R5_MAIN
    constrained = sample_evacuation_network.copy()
    constrained.edit_node("S1", shelter_capacity=200)
    constrained.edit_road("R5_MAIN", is_active=False)

    constrained_res = solve_max_flow_dinic(constrained)
    # S1 max 200, S2 max 500 -> max flow cannot exceed 700
    assert constrained_res.max_flow == 700
    assert constrained_res.road_flows["R5_MAIN"].original_capacity == 0
    assert constrained_res.road_flows["R5_MAIN"].flow == 0
    assert constrained_res.shelter_intakes["S1"].assigned_flow == 200
    assert constrained_res.shelter_intakes["S2"].assigned_flow == 500


def test_dinic_uses_reverse_residual_edge_to_reroute_flow() -> None:
    """Verify Dinic's Phase 2 cancels an earlier Phase 1 shortcut via reverse edge."""
    net = EvacuationNetwork(network_id="reroute", name="Reverse Edge Reroute Proof")
    net.add_node("A", "Affected Area", NodeType.AFFECTED_AREA, population=20)
    for j in ("J0", "J1", "J2", "J3", "J4", "J5"):
        net.add_node(j, j, NodeType.JUNCTION)
    net.add_node("S", "Shelter", NodeType.SHELTER, shelter_capacity=20)

    # Short 3-road path chosen first in Phase 1: A -> J1 -> J4 -> S (cap 10)
    net.add_road("R_A_J1", "A", "J1", 10)
    net.add_road("R_J1_J4", "J1", "J4", 10)
    net.add_road("R_J4_S", "J4", "S", 10)

    # Longer 4-road bypasses requiring J1->J4 cancellation in Phase 2
    net.add_road("R_A_J0", "A", "J0", 10)
    net.add_road("R_J0_J2", "J0", "J2", 10)
    net.add_road("R_J2_J4", "J2", "J4", 10)

    net.add_road("R_J1_J3", "J1", "J3", 10)
    net.add_road("R_J3_J5", "J3", "J5", 10)
    net.add_road("R_J5_S", "J5", "S", 10)

    traced = solve_max_flow_dinic(net, trace=True)
    untraced = solve_max_flow_dinic(net, trace=False)

    assert untraced.max_flow == 20
    assert traced.max_flow == 20
    assert traced.bfs_phases == 2
    assert untraced.bfs_phases == traced.bfs_phases
    assert untraced.useful_augmentations == traced.useful_augmentations

    # R_J1_J4 must end with 0 net flow after Phase 2 cancels Phase 1's 10 units
    assert traced.road_flows["R_J1_J4"].flow == 0
    assert traced.road_flows["R_J1_J4"].remaining_capacity == 10
    assert traced.road_flows["R_J1_J3"].flow == 10
    assert traced.road_flows["R_J2_J4"].flow == 10

    assert traced.trace is not None
    assert traced.trace.reverse_rerouting_steps >= 1
    phase_1, phase_2, phase_3 = traced.trace.phases
    assert phase_1.sink_reachable is True
    assert phase_1.phase_flow_pushed == 10
    assert phase_1.node_levels[SUPER_SOURCE_ID] == 0
    assert phase_1.node_levels[SUPER_SINK_ID] == 5

    assert phase_2.sink_reachable is True
    assert phase_2.phase_flow_pushed == 10
    assert phase_2.cumulative_flow == 20
    assert any(step.rerouted_via_reverse_edge for step in phase_2.augmentations)

    rev_updates = [
        upd
        for step in phase_2.augmentations
        for upd in step.edge_updates
        if upd.used_reverse_edge
    ]
    assert any(
        upd.edge_id == "R_J1_J4"
        and upd.forward_residual_before == 0
        and upd.forward_residual_after == 10
        and upd.reverse_residual_before == 10
        and upd.reverse_residual_after == 0
        for upd in rev_updates
    )

    assert phase_3.sink_reachable is False
    assert phase_3.sink_level is None


def test_dinic_disconnected_and_zero_capacity_graphs() -> None:
    disconnected = EvacuationNetwork()
    disconnected.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=300)
    disconnected.add_node("J1", "Island Junction", NodeType.JUNCTION)
    disconnected.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=300)
    disconnected.add_road("R1", "A1", "J1", 200)
    # No path from J1 to S1

    res = solve_max_flow_dinic(disconnected, trace=True)
    assert res.max_flow == 0
    assert res.unmet_demand == 300
    assert res.bfs_phases == 0
    assert res.bfs_calls == 1
    assert res.useful_augmentations == 0
    assert res.trace is not None
    assert len(res.trace.phases) == 1
    assert res.trace.phases[0].sink_reachable is False

    zero_cap = EvacuationNetwork()
    zero_cap.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=0)
    zero_cap.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=100)
    zero_cap.add_road("R1", "A1", "S1", 0)
    res_zero = solve_max_flow_dinic(zero_cap)
    assert res_zero.max_flow == 0
    assert res_zero.evacuation_rate == pytest.approx(1.0)


def test_dinic_iterative_dfs_handles_deep_chain_without_recursion_error() -> None:
    """Verify iterative DFS safely processes > 1200 vertices without hitting recursion limits."""
    net = EvacuationNetwork(network_id="deep-chain", name="Deep Chain")
    chain_len = 1205
    net.add_node("N0", "Source", NodeType.AFFECTED_AREA, population=75)
    for idx in range(1, chain_len - 1):
        net.add_node(f"N{idx}", f"J{idx}", NodeType.JUNCTION)
    net.add_node(f"N{chain_len - 1}", "Shelter", NodeType.SHELTER, shelter_capacity=100)

    for idx in range(chain_len - 1):
        cap = 50 if idx == 600 else 90
        net.add_road(f"R{idx}", f"N{idx}", f"N{idx + 1}", cap)
        if idx % 10 == 0 and idx < chain_len - 2:
            # Add dead-end side node to exercise current-arc dead-end skipping
            dead_id = f"DEAD_{idx}"
            net.add_node(dead_id, dead_id, NodeType.JUNCTION)
            net.add_road(f"R_DEAD_{idx}", f"N{idx}", dead_id, 25)

    res = solve_max_flow_dinic(net)
    assert res.max_flow == 50
    assert res.bfs_phases == 1


@pytest.mark.parametrize("seed", range(25))
def test_dinic_matches_edmonds_karp_on_random_directed_graphs(seed: int) -> None:
    """Property check against independent Edmonds-Karp reference across 25 random graphs."""
    rng = random.Random(seed)
    net = EvacuationNetwork(network_id=f"rand-{seed}", name=f"Random {seed}")

    num_sources = rng.randint(1, 3)
    num_junctions = rng.randint(2, 6)
    num_shelters = rng.randint(1, 3)

    node_ids: list[str] = []
    for i in range(num_sources):
        nid = f"SRC_{i}"
        net.add_node(nid, nid, NodeType.AFFECTED_AREA, population=rng.randint(0, 400))
        node_ids.append(nid)
    for i in range(num_junctions):
        nid = f"JNC_{i}"
        net.add_node(nid, nid, NodeType.JUNCTION)
        node_ids.append(nid)
    for i in range(num_shelters):
        nid = f"SHL_{i}"
        net.add_node(nid, nid, NodeType.SHELTER, shelter_capacity=rng.randint(0, 400))
        node_ids.append(nid)

    edge_count = rng.randint(6, 22)
    for e_idx in range(edge_count):
        u, v = rng.sample(node_ids, 2)
        net.add_road(f"ROAD_{e_idx}", u, v, rng.randint(0, 250))

    expected_flow = _reference_edmonds_karp(net)
    dinic_res = solve_max_flow_dinic(net, trace=(seed % 2 == 0))

    assert dinic_res.max_flow == expected_flow
    assert dinic_res.max_flow <= net.total_population
    assert dinic_res.max_flow <= net.total_shelter_capacity
    assert sum(s.evacuated for s in dinic_res.source_evacuations.values()) == expected_flow
    assert sum(t.assigned_flow for t in dinic_res.shelter_intakes.values()) == expected_flow


def test_dinic_solver_reset_allows_clean_reruns(
    sample_evacuation_network: EvacuationNetwork,
) -> None:
    flow_net = build_evacuation_network(sample_evacuation_network)
    solver = DinicSolver()
    first = solver.solve(flow_net, domain_network=sample_evacuation_network, trace=False)
    second = solver.solve(flow_net, domain_network=sample_evacuation_network, trace=True)
    assert first.max_flow == second.max_flow == 1000
    assert second.trace is not None
