"""Educational shortest-path analysis and comparison against Dinic's Maximum Flow."""

from dataclasses import dataclass

from resq.algorithms.dijkstra import solve_shortest_path_dijkstra
from resq.domain.models import EvacuationNetwork
from resq.domain.results import DijkstraResult, ShortestPathRoute
from resq.services.evacuation_simulator import (
    FullAnalysisBundle,
    run_full_evacuation_analysis,
)


@dataclass(frozen=True, slots=True)
class FlowRouteComparisonRow:
    """Decomposed Dinic evacuation route enriched with route distance metrics."""

    route_index: int
    source_id: str
    shelter_id: str
    node_path: tuple[str, ...]
    road_ids: tuple[str, ...]
    flow_allocated: int
    total_distance: float
    bottleneck_capacity: int
    matches_shortest_pair_route: bool


@dataclass(frozen=True, slots=True)
class ShortestRoadFlowStatus:
    """How much maximum-flow traffic Dinic assigned to one road along the shortest route."""

    road_id: str
    road_name: str
    from_node: str
    to_node: str
    distance: float
    capacity: int
    dinic_flow: int
    remaining_capacity: int
    utilization_pct: float
    is_saturated: bool
    is_min_cut: bool


@dataclass(frozen=True, slots=True)
class ShortestVsMaxFlowComparison:
    """Comprehensive side-by-side comparison between Dijkstra and Dinic's Max Flow."""

    dijkstra_result: DijkstraResult
    source_id: str
    shelter_id: str
    shortest_route: ShortestPathRoute | None
    alternative_route: ShortestPathRoute | None
    flow_analysis_available: bool
    system_max_flow: int
    source_population: int
    source_dispatched_flow: int
    shelter_capacity: int
    shelter_received_flow: int
    pair_routed_flow: int
    exact_shortest_path_used_by_dinic: bool
    pair_flow_routes: tuple[FlowRouteComparisonRow, ...]
    source_flow_routes: tuple[FlowRouteComparisonRow, ...]
    shortest_road_statuses: tuple[ShortestRoadFlowStatus, ...]
    shared_road_ids: tuple[str, ...]
    problem_distinction_summary: str
    observations: tuple[str, ...]


PROBLEM_DISTINCTION_SUMMARY = (
    "Dijkstra's Shortest Path and Dinic's Maximum Flow solve fundamentally different optimization "
    "problems: Dijkstra minimizes total non-negative road distance along a single uncapacitated "
    "path between one chosen Affected Area and one Shelter in O((V + E) log V) time, ignoring "
    "road throughput and shelter bed limits. Dinic's Maximum Flow maximizes total evacuees across "
    "ALL sources and ALL shelters simultaneously subject to integer road and shelter capacity limits "
    "in O(V^2 E) worst-case time, routing across longer or parallel corridors whenever shorter roads saturate."
)


def _route_distance_and_bottleneck(
    network: EvacuationNetwork,
    road_ids: tuple[str, ...],
) -> tuple[float, int]:
    if not road_ids:
        return 0.0, 0
    total_dist = 0.0
    min_cap: int | None = None
    for rid in road_ids:
        road = network.roads.get(rid)
        if road is None:
            continue
        total_dist += float(road.distance)
        eff = road.effective_capacity
        min_cap = eff if min_cap is None else min(min_cap, eff)
    return float(total_dist), (min_cap if min_cap is not None else 0)


def _build_observations(
    *,
    dijkstra_result: DijkstraResult,
    shortest: ShortestPathRoute | None,
    alternative: ShortestPathRoute | None,
    source_id: str,
    shelter_id: str,
    pair_routed_flow: int,
    exact_used: bool,
    pair_flow_routes: tuple[FlowRouteComparisonRow, ...],
    source_flow_routes: tuple[FlowRouteComparisonRow, ...],
    road_statuses: tuple[ShortestRoadFlowStatus, ...],
    system_max_flow: int,
) -> tuple[str, ...]:
    notes: list[str] = []
    if not dijkstra_result.reachable or shortest is None:
        notes.append(
            f"No active directed road path reaches shelter '{shelter_id}' from affected area '{source_id}'."
        )
        if source_flow_routes:
            dests = ", ".join(sorted({r.shelter_id for r in source_flow_routes}))
            notes.append(
                f"However, Dinic's global max-flow still evacuated people from '{source_id}' "
                f"to alternative shelter(s): {dests}."
            )
        return tuple(notes)

    if alternative is not None:
        delta = alternative.total_distance - shortest.total_distance
        notes.append(
            f"Shortest route spans {shortest.total_distance:.2f} km ({len(shortest.road_ids)} road(s), "
            f"bottleneck capacity {shortest.bottleneck_capacity:,}); alternative route spans "
            f"{alternative.total_distance:.2f} km (+{delta:.2f} km longer)."
        )
    else:
        notes.append(
            f"Shortest route spans {shortest.total_distance:.2f} km with no distinct alternative "
            f"simple path available between '{source_id}' and '{shelter_id}'."
        )

    if shortest.bottleneck_capacity == 0:
        notes.append(
            "Because Dijkstra ignores capacity weights, its shortest route traverses an active corridor "
            "with 0 effective capacity and therefore can carry 0 evacuees in maximum flow."
        )

    if pair_routed_flow == 0:
        if source_flow_routes:
            used_shelters = ", ".join(sorted({r.shelter_id for r in source_flow_routes}))
            notes.append(
                f"Dinic allocated 0 flow along '{source_id} -> {shelter_id}', sending '{source_id}' "
                f"evacuees to {used_shelters} instead to achieve global max flow ({system_max_flow:,})."
            )
        else:
            notes.append(
                f"Dinic routed 0 flow from '{source_id}' to '{shelter_id}' because downstream or "
                f"upstream minimum-cut constraints prevent further evacuation."
            )
    else:
        if exact_used:
            matched = [r for r in pair_flow_routes if r.matches_shortest_pair_route]
            matched_flow = sum(r.flow_allocated for r in matched)
            notes.append(
                f"Dinic routed {matched_flow:,} evacuees on the exact shortest corridor "
                f"(out of {pair_routed_flow:,} total routed along '{source_id} -> {shelter_id}')."
            )
        else:
            notes.append(
                f"Even though Dinic sent {pair_routed_flow:,} evacuees between '{source_id}' and "
                f"'{shelter_id}', it avoided the exact shortest-distance chain in favor of higher-capacity or "
                f"less-congested detours."
            )

        longer_flow_routes = [
            r
            for r in source_flow_routes
            if r.total_distance > shortest.total_distance + 1e-9
        ]
        if longer_flow_routes:
            max_flow_dist = max(r.total_distance for r in longer_flow_routes)
            extra_flow = sum(r.flow_allocated for r in longer_flow_routes)
            notes.append(
                f"To maximize throughput, Dinic also dispatched {extra_flow:,} evacuees from '{source_id}' "
                f"over longer routes (up to {max_flow_dist:.2f} km vs Dijkstra's {shortest.total_distance:.2f} km)."
            )

    saturated_on_shortest = [s.road_id for s in road_statuses if s.is_saturated]
    if saturated_on_shortest:
        notes.append(
            "Shortest-path link(s) saturated under Max Flow: "
            + ", ".join(saturated_on_shortest)
            + "."
        )

    return tuple(notes)


def compare_shortest_path_with_max_flow(
    network: EvacuationNetwork,
    source_id: str,
    shelter_id: str,
    *,
    bundle: FullAnalysisBundle | None = None,
    dijkstra_result: DijkstraResult | None = None,
    active_roads_only: bool = True,
    compute_flow_if_missing: bool = False,
) -> ShortestVsMaxFlowComparison:
    """Compare Dijkstra shortest-distance route against Dinic's maximum-flow solution."""
    if dijkstra_result is None or (
        dijkstra_result.source_id != source_id or dijkstra_result.shelter_id != shelter_id
    ):
        dijkstra_result = solve_shortest_path_dijkstra(
            network,
            source_id,
            shelter_id,
            active_roads_only=active_roads_only,
            require_area_and_shelter=True,
            find_alternative=True,
        )

    resolved_bundle = bundle
    if resolved_bundle is None and compute_flow_if_missing:
        resolved_bundle = run_full_evacuation_analysis(network, trace=False)

    shortest = dijkstra_result.shortest_route
    alternative = dijkstra_result.alternative_route
    src_node = network.get_node(source_id)
    dst_node = network.get_node(shelter_id)

    if resolved_bundle is None:
        return ShortestVsMaxFlowComparison(
            dijkstra_result=dijkstra_result,
            source_id=source_id,
            shelter_id=shelter_id,
            shortest_route=shortest,
            alternative_route=alternative,
            flow_analysis_available=False,
            system_max_flow=0,
            source_population=src_node.population,
            source_dispatched_flow=0,
            shelter_capacity=dst_node.shelter_capacity,
            shelter_received_flow=0,
            pair_routed_flow=0,
            exact_shortest_path_used_by_dinic=False,
            pair_flow_routes=(),
            source_flow_routes=(),
            shortest_road_statuses=(),
            shared_road_ids=(),
            problem_distinction_summary=PROBLEM_DISTINCTION_SUMMARY,
            observations=(
                "Run Max-Flow Analysis to populate live Dinic evacuation paths and compare "
                "throughput allocations against this shortest-distance route.",
            ),
        )

    dinic = resolved_bundle.dinic_result
    cut_road_ids = {e.edge_id for e in resolved_bundle.min_cut.road_bottlenecks}
    shortest_roads_tuple = shortest.road_ids if shortest is not None else ()

    pair_rows: list[FlowRouteComparisonRow] = []
    source_rows: list[FlowRouteComparisonRow] = []

    for route in resolved_bundle.routes:
        total_dist, min_cap = _route_distance_and_bottleneck(network, route.road_ids)
        is_exact = (
            shortest is not None
            and route.source_id == source_id
            and route.shelter_id == shelter_id
            and route.road_ids == shortest_roads_tuple
        )
        row = FlowRouteComparisonRow(
            route_index=route.route_index,
            source_id=route.source_id,
            shelter_id=route.shelter_id,
            node_path=route.node_path,
            road_ids=route.road_ids,
            flow_allocated=route.flow,
            total_distance=total_dist,
            bottleneck_capacity=min_cap,
            matches_shortest_pair_route=is_exact,
        )
        if route.source_id == source_id:
            source_rows.append(row)
            if route.shelter_id == shelter_id:
                pair_rows.append(row)

    road_statuses: list[ShortestRoadFlowStatus] = []
    for rid in shortest_roads_tuple:
        road = network.roads[rid]
        detail = dinic.road_flows.get(rid)
        dinic_flow = detail.flow if detail else 0
        orig_cap = detail.original_capacity if detail else road.effective_capacity
        rem_cap = detail.remaining_capacity if detail else (orig_cap - dinic_flow)
        util_pct = (detail.utilization_ratio * 100.0) if detail else 0.0
        is_sat = detail.is_saturated if detail else False
        road_statuses.append(
            ShortestRoadFlowStatus(
                road_id=rid,
                road_name=road.name or rid,
                from_node=road.source_id,
                to_node=road.target_id,
                distance=float(road.distance),
                capacity=orig_cap,
                dinic_flow=dinic_flow,
                remaining_capacity=rem_cap,
                utilization_pct=util_pct,
                is_saturated=is_sat,
                is_min_cut=rid in cut_road_ids,
            )
        )

    source_active_roads = {
        rid for row in source_rows for rid in row.road_ids
    }
    shared_roads = tuple(rid for rid in shortest_roads_tuple if rid in source_active_roads)

    src_detail = dinic.source_evacuations.get(source_id)
    shl_detail = dinic.shelter_intakes.get(shelter_id)
    pair_routed = sum(row.flow_allocated for row in pair_rows)
    exact_used = any(row.matches_shortest_pair_route for row in pair_rows)

    observations = _build_observations(
        dijkstra_result=dijkstra_result,
        shortest=shortest,
        alternative=alternative,
        source_id=source_id,
        shelter_id=shelter_id,
        pair_routed_flow=pair_routed,
        exact_used=exact_used,
        pair_flow_routes=tuple(pair_rows),
        source_flow_routes=tuple(source_rows),
        road_statuses=tuple(road_statuses),
        system_max_flow=dinic.max_flow,
    )

    return ShortestVsMaxFlowComparison(
        dijkstra_result=dijkstra_result,
        source_id=source_id,
        shelter_id=shelter_id,
        shortest_route=shortest,
        alternative_route=alternative,
        flow_analysis_available=True,
        system_max_flow=dinic.max_flow,
        source_population=src_detail.population if src_detail else src_node.population,
        source_dispatched_flow=src_detail.evacuated if src_detail else 0,
        shelter_capacity=shl_detail.shelter_capacity if shl_detail else dst_node.shelter_capacity,
        shelter_received_flow=shl_detail.assigned_flow if shl_detail else 0,
        pair_routed_flow=pair_routed,
        exact_shortest_path_used_by_dinic=exact_used,
        pair_flow_routes=tuple(pair_rows),
        source_flow_routes=tuple(source_rows),
        shortest_road_statuses=tuple(road_statuses),
        shared_road_ids=shared_roads,
        problem_distinction_summary=PROBLEM_DISTINCTION_SUMMARY,
        observations=observations,
    )
