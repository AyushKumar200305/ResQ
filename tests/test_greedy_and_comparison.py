"""Unit and property tests for Greedy baseline and Dinic-vs-Greedy comparison."""

import random
import pytest

from resq import (
    DinicSolver,
    EvacuationNetwork,
    GreedyRule,
    NodeType,
    build_evacuation_network,
    compare_dinic_vs_greedy,
    explain_greedy_rule,
    solve_greedy_baseline,
)


def _build_shortcut_trap_network() -> EvacuationNetwork:
    """Graph where Greedy shortest-hop/lex-DFS traps itself at 10 while Dinic gets 20."""
    net = EvacuationNetwork(network_id="shortcut-trap", name="Shortcut Trap")
    net.add_node("A", "Affected Area", NodeType.AFFECTED_AREA, population=20)
    for j in ("J1", "J2", "J3", "J4", "J5", "J9"):
        net.add_node(j, j, NodeType.JUNCTION)
    net.add_node("S", "Shelter", NodeType.SHELTER, shelter_capacity=20)

    # 3-road shortcut saturated first by shortest-hop & lex-DFS (J1 < J9)
    net.add_road("R_A_J1", "A", "J1", 10)
    net.add_road("R_J1_J4", "J1", "J4", 10)
    net.add_road("R_J4_S", "J4", "S", 10)

    # 4-road parallel bypasses requiring reverse cancellation of R_J1_J4
    net.add_road("R_A_J9", "A", "J9", 10)
    net.add_road("R_J9_J2", "J9", "J2", 10)
    net.add_road("R_J2_J4", "J2", "J4", 10)

    net.add_road("R_J1_J3", "J1", "J3", 10)
    net.add_road("R_J3_J5", "J3", "J5", 10)
    net.add_road("R_J5_S", "J5", "S", 10)
    return net


def _build_widest_path_trap_network() -> EvacuationNetwork:
    """Graph where Widest-Path Greedy traps itself at 12 while Dinic & Shortest-Hop get 22."""
    net = EvacuationNetwork(network_id="widest-trap", name="Widest Path Trap")
    net.add_node("A", "Zone A", NodeType.AFFECTED_AREA, population=22)
    net.add_node("J1", "Junction 1", NodeType.JUNCTION)
    net.add_node("J2", "Junction 2", NodeType.JUNCTION)
    net.add_node("S", "Shelter S", NodeType.SHELTER, shelter_capacity=22)

    net.add_road("R_A_J1", "A", "J1", 12)
    net.add_road("R_J1_S", "J1", "S", 10)
    net.add_road("R_A_J2", "A", "J2", 10)
    net.add_road("R_J2_S", "J2", "S", 12)
    # Cross-link of capacity 12 makes A->J1->J2->S widest single path (bottleneck 12)
    net.add_road("R_J1_J2", "J1", "J2", 12)
    return net


def test_greedy_uses_isolated_residual_network_without_modifying_dinic() -> None:
    net = _build_shortcut_trap_network()
    dinic_flow_net = build_evacuation_network(net)
    dinic_res = DinicSolver().solve(dinic_flow_net, domain_network=net)
    dinic_snapshot_before = dinic_flow_net.snapshot_capacities()

    greedy_res = solve_greedy_baseline(net, rule=GreedyRule.SHORTEST_HOP, trace=True)

    assert dinic_res.max_flow == 20
    assert greedy_res.max_flow == 10
    assert dinic_flow_net.snapshot_capacities() == dinic_snapshot_before
    assert greedy_res.steps is not None
    assert len(greedy_res.steps) == greedy_res.augmentations == 1


def test_greedy_suboptimality_and_rule_sensitivity() -> None:
    shortcut_net = _build_shortcut_trap_network()
    comp_short = compare_dinic_vs_greedy(
        shortcut_net, greedy_rule=GreedyRule.SHORTEST_HOP, repeats=3
    )
    assert comp_short.dinic_max_flow == 20
    assert comp_short.greedy_flow == 10
    assert comp_short.flow_difference == 10
    assert comp_short.optimality_gap_pct == pytest.approx(50.0)
    assert comp_short.greedy_efficiency_ratio == pytest.approx(0.5)
    assert comp_short.benchmark_repeats == 3
    assert comp_short.dinic_time_ns >= 0
    assert comp_short.greedy_time_ns >= 0
    assert "reverse residual" in comp_short.rule_explanation.lower()

    # On shortcut_trap: Shortest-Hop picks the 3-hop bridge and gets trapped at 10,
    # whereas Lexicographic DFS visits J3 before J4 (J3 < J4) and avoids the trap.
    comp_dfs_short = compare_dinic_vs_greedy(
        shortcut_net, greedy_rule=GreedyRule.LEXICOGRAPHIC_DFS
    )
    assert comp_dfs_short.dinic_max_flow == 20
    assert comp_dfs_short.greedy_flow == 20

    # On widest_trap: Widest-Path and Lexicographic DFS (J2 < S) both saturate
    # the cross-edge A->J1->J2->S (12) and get trapped at 12 while Dinic & Shortest-Hop get 22.
    widest_trap = _build_widest_path_trap_network()
    res_widest = solve_greedy_baseline(widest_trap, rule=GreedyRule.WIDEST_PATH, trace=True)
    res_short = solve_greedy_baseline(widest_trap, rule=GreedyRule.SHORTEST_HOP, trace=True)
    comp_widest = compare_dinic_vs_greedy(widest_trap, greedy_rule=GreedyRule.WIDEST_PATH)
    comp_dfs_wide = compare_dinic_vs_greedy(
        widest_trap, greedy_rule=GreedyRule.LEXICOGRAPHIC_DFS
    )

    # Demonstrates why greedy varies by selection rule on the exact same topology
    assert comp_widest.dinic_max_flow == 22
    assert res_short.max_flow == 22
    assert res_widest.max_flow == 12
    assert comp_dfs_wide.greedy_flow == 12
    assert res_widest.max_flow < res_short.max_flow
    assert comp_widest.flow_difference == 10
    assert any(rc.flow_difference != 0 for rc in comp_widest.road_comparisons)


def test_comparison_on_disconnected_zero_flow_graph() -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Zone", NodeType.AFFECTED_AREA, population=200)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=200)
    # No roads connecting A1 and S1

    comp = compare_dinic_vs_greedy(net, greedy_rule=GreedyRule.SHORTEST_HOP)
    assert comp.dinic_max_flow == 0
    assert comp.greedy_flow == 0
    assert comp.flow_difference == 0
    assert comp.optimality_gap_pct == pytest.approx(0.0)
    assert comp.greedy_efficiency_ratio == pytest.approx(1.0)


def test_explain_greedy_rule_returns_distinct_explanations() -> None:
    explanations = {explain_greedy_rule(rule) for rule in GreedyRule}
    assert len(explanations) == len(GreedyRule)


@pytest.mark.parametrize("rule", list(GreedyRule))
def test_greedy_never_exceeds_dinic_and_respects_invariants_on_random_graphs(
    rule: GreedyRule,
) -> None:
    for seed in range(15):
        rng = random.Random(200 + seed)
        net = EvacuationNetwork(network_id=f"gr-{seed}", name=f"GR {seed}")

        node_ids: list[str] = []
        for i in range(rng.randint(1, 3)):
            nid = f"A_{i}"
            net.add_node(nid, nid, NodeType.AFFECTED_AREA, population=rng.randint(0, 350))
            node_ids.append(nid)
        for i in range(rng.randint(2, 5)):
            nid = f"J_{i}"
            net.add_node(nid, nid, NodeType.JUNCTION)
            node_ids.append(nid)
        for i in range(rng.randint(1, 3)):
            nid = f"S_{i}"
            net.add_node(nid, nid, NodeType.SHELTER, shelter_capacity=rng.randint(0, 350))
            node_ids.append(nid)

        for e_idx in range(rng.randint(6, 20)):
            u, v = rng.sample(node_ids, 2)
            net.add_road(f"R_{e_idx}", u, v, rng.randint(0, 200))

        comp = compare_dinic_vs_greedy(net, greedy_rule=rule)
        assert 0 <= comp.greedy_flow <= comp.dinic_max_flow
        assert comp.flow_difference == comp.dinic_max_flow - comp.greedy_flow
        assert len(comp.road_comparisons) == len(net.roads)
