"""Algorithmic comparison between Dinic's Maximum Flow and Greedy baselines."""

from statistics import median

from resq.algorithms.dinic import DinicSolver
from resq.algorithms.greedy import GreedySolver
from resq.domain.enums import GreedyRule
from resq.domain.exceptions import GraphValidationError
from resq.domain.models import EvacuationNetwork
from resq.domain.results import (
    AlgorithmComparisonResult,
    DinicResult,
    EdgeComparisonDetail,
    GreedyResult,
)
from resq.services.network_builder import build_evacuation_network

RULE_EXPLANATIONS: dict[GreedyRule, str] = {
    GreedyRule.SHORTEST_HOP: (
        "Shortest-Hop Greedy selects the fewest-hop S*->T* forward path at each step "
        "in fixed lexicographical neighbor order. Because it cannot push flow along "
        "reverse residual edges, taking an early shortcut that shares a downstream "
        "bottleneck can permanently block longer parallel corridors."
    ),
    GreedyRule.WIDEST_PATH: (
        "Widest-Path Greedy prioritizes the single forward path with the highest "
        "bottleneck capacity (tie-breaking by fewest hops). When a high-capacity "
        "diagonal crosses two moderate corridors, saturating it first can sever both "
        "paths and yield less total flow than two narrower disjoint routes."
    ),
    GreedyRule.LEXICOGRAPHIC_DFS: (
        "Lexicographic DFS Greedy greedily commits flow along the first valid "
        "forward path discovered in sorted (target_id, road_id) order. Because route "
        "choices depend strictly on identifier ordering and cannot be reversed, flow "
        "frequently becomes trapped in suboptimal local paths."
    ),
}


def explain_greedy_rule(rule: GreedyRule | str) -> str:
    """Return a concise explanation of why the selected greedy heuristic can misroute flow."""
    parsed = GreedyRule.parse(rule)
    return RULE_EXPLANATIONS[parsed]


def compare_dinic_vs_greedy(
    network: EvacuationNetwork,
    *,
    greedy_rule: GreedyRule | str = GreedyRule.SHORTEST_HOP,
    repeats: int = 1,
    trace: bool = False,
) -> AlgorithmComparisonResult:
    """Compare Dinic's Maximum Flow against an independent Greedy baseline on `network`.

    Each algorithm solves its own isolated FlowNetwork instance so Greedy never mutates
    Dinic's residual graph. When `repeats > 1`, uninstrumented runs (`trace=False`) are
    timed repeatedly and median latencies are reported without altering measured values.
    """
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise GraphValidationError(f"repeats must be an integer >= 1, got {repeats!r}.")

    parsed_rule = GreedyRule.parse(greedy_rule)

    dinic_flow_net = build_evacuation_network(network)
    greedy_flow_net = build_evacuation_network(network)

    dinic_solver = DinicSolver()
    greedy_solver = GreedySolver()

    dinic_result: DinicResult = dinic_solver.solve(
        dinic_flow_net,
        domain_network=network,
        trace=trace,
        reset=False,
        verify_invariants=True,
    )
    greedy_result: GreedyResult = greedy_solver.solve(
        greedy_flow_net,
        domain_network=network,
        rule=parsed_rule,
        trace=trace,
        reset=False,
        verify_invariants=True,
    )

    if repeats == 1:
        dinic_time_ns = dinic_result.execution_time_ns
        greedy_time_ns = greedy_result.execution_time_ns
    else:
        dinic_timings = [
            dinic_solver.solve(
                dinic_flow_net,
                domain_network=network,
                trace=False,
                reset=True,
                verify_invariants=False,
            ).execution_time_ns
            for _ in range(repeats)
        ]
        greedy_timings = [
            greedy_solver.solve(
                greedy_flow_net,
                domain_network=network,
                rule=parsed_rule,
                trace=False,
                reset=True,
                verify_invariants=False,
            ).execution_time_ns
            for _ in range(repeats)
        ]
        dinic_time_ns = int(median(dinic_timings))
        greedy_time_ns = int(median(greedy_timings))

    dinic_flow = dinic_result.max_flow
    greedy_flow = greedy_result.max_flow
    flow_diff = dinic_flow - greedy_flow
    optimality_gap_pct = (flow_diff / dinic_flow * 100.0) if dinic_flow > 0 else 0.0
    greedy_efficiency_ratio = (greedy_flow / dinic_flow) if dinic_flow > 0 else 1.0

    dinic_time_ms = dinic_time_ns / 1_000_000.0
    greedy_time_ms = greedy_time_ns / 1_000_000.0
    relative_speed_ratio = (
        (greedy_time_ns / dinic_time_ns) if dinic_time_ns > 0 else 1.0
    )

    road_comparisons: list[EdgeComparisonDetail] = []
    for road_id, d_edge in dinic_result.road_flows.items():
        g_edge = greedy_result.road_flows[road_id]
        road_comparisons.append(
            EdgeComparisonDetail(
                road_id=road_id,
                road_name=d_edge.road_name,
                source_id=d_edge.source_id,
                target_id=d_edge.target_id,
                capacity=d_edge.original_capacity,
                dinic_flow=d_edge.flow,
                greedy_flow=g_edge.flow,
                flow_difference=d_edge.flow - g_edge.flow,
            )
        )

    return AlgorithmComparisonResult(
        dinic_result=dinic_result,
        greedy_result=greedy_result,
        dinic_max_flow=dinic_flow,
        greedy_flow=greedy_flow,
        flow_difference=flow_diff,
        optimality_gap_pct=optimality_gap_pct,
        greedy_efficiency_ratio=greedy_efficiency_ratio,
        dinic_time_ns=dinic_time_ns,
        dinic_time_ms=dinic_time_ms,
        greedy_time_ns=greedy_time_ns,
        greedy_time_ms=greedy_time_ms,
        relative_speed_ratio=relative_speed_ratio,
        benchmark_repeats=repeats,
        road_comparisons=tuple(road_comparisons),
        rule_explanation=explain_greedy_rule(parsed_rule),
    )
