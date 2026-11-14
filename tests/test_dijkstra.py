"""Unit and integration tests for Dijkstra's shortest-path extension and Max-Flow comparison."""

import math
import pytest

from resq import (
    DinicSolver,
    EntityNotFoundError,
    EvacuationNetwork,
    GraphValidationError,
    NodeType,
    build_evacuation_network,
    compare_shortest_path_with_max_flow,
    import_network_from_json,
    solve_shortest_path_dijkstra,
)
from resq.services import load_preset_network, run_full_evacuation_analysis
from resq.ui.components import build_network_figure


def _build_educational_contrast_network() -> EvacuationNetwork:
    """Graph where shortest distance uses low-capacity 2-hop corridor instead of high-capacity bridge."""
    net = EvacuationNetwork(network_id="dijkstra-contrast", name="Distance vs Capacity Test")
    net.add_node("A1", "Flood Zone A1", NodeType.AFFECTED_AREA, population=500)
    net.add_node("J1", "Low Bridge J1", NodeType.JUNCTION)
    net.add_node("J2", "Bypass Ridge J2", NodeType.JUNCTION)
    net.add_node("J3", "East Relay J3", NodeType.JUNCTION)
    net.add_node("S1", "Main Shelter S1", NodeType.SHELTER, shelter_capacity=500)

    # Shortest distance path: A1 -> J1 -> S1 (distance = 1.5 + 1.5 = 3.0 km, capacity = 50)
    net.add_road("R_A1_J1", "A1", "J1", capacity=50, name="Narrow Footbridge", distance=1.5)
    net.add_road("R_J1_S1", "J1", "S1", capacity=50, name="Old Mill Lane", distance=1.5)

    # Multi-hop shorter-weight path vs 2nd shortest wide expressway:
    # A1 -> J2 -> J3 -> S1: 2.0 + 1.0 + 1.5 = 4.5 km (3 hops, capacity = 400)
    net.add_road("R_A1_J2", "A1", "J2", capacity=400, name="Highway Ramp", distance=2.0)
    net.add_road("R_J2_J3", "J2", "J3", capacity=400, name="Ridge Expressway", distance=1.0)
    net.add_road("R_J3_S1", "J3", "S1", capacity=400, name="Shelter Boulevard", distance=1.5)

    # Even longer detour via J2 -> S1 directly: 2.0 + 6.0 = 8.0 km (capacity = 300)
    net.add_road("R_J2_S1", "J2", "S1", capacity=300, name="Outer Beltway", distance=6.0)
    return net


def test_dijkstra_finds_shortest_distance_and_alternative_route() -> None:
    net = _build_educational_contrast_network()
    res = solve_shortest_path_dijkstra(net, "A1", "S1")

    assert res.reachable is True
    assert res.vertex_count == 5
    assert res.edge_count == 6
    assert res.shortest_route is not None
    assert res.alternative_route is not None

    shortest = res.shortest_route
    assert shortest.rank == 1
    assert shortest.total_distance == pytest.approx(3.0)
    assert shortest.node_path == ("A1", "J1", "S1")
    assert shortest.node_names == ("Flood Zone A1", "Low Bridge J1", "Main Shelter S1")
    assert shortest.road_ids == ("R_A1_J1", "R_J1_S1")
    assert shortest.road_distances == (1.5, 1.5)
    assert shortest.bottleneck_capacity == 50

    alt = res.alternative_route
    assert alt.rank == 2
    assert alt.total_distance == pytest.approx(4.5)
    assert alt.node_path == ("A1", "J2", "J3", "S1")
    assert alt.road_ids == ("R_A1_J2", "R_J2_J3", "R_J3_S1")
    assert alt.bottleneck_capacity == 400

    # All finite single-source shortest distances checked
    assert res.distances_from_source["A1"] == pytest.approx(0.0)
    assert res.distances_from_source["J1"] == pytest.approx(1.5)
    assert res.distances_from_source["J2"] == pytest.approx(2.0)
    assert res.distances_from_source["J3"] == pytest.approx(3.0)
    assert res.distances_from_source["S1"] == pytest.approx(3.0)


def test_dijkstra_handles_parallel_roads_and_alternative_route() -> None:
    net = EvacuationNetwork(network_id="parallel-dist", name="Parallel Roads Distance")
    net.add_node("A1", "Area", NodeType.AFFECTED_AREA, population=300)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=300)
    net.add_road("R_FAST_THIN", "A1", "S1", capacity=40, name="Short Alley", distance=2.2)
    net.add_road("R_WIDE_LONG", "A1", "S1", capacity=500, name="Main Arterial", distance=4.8)

    res = solve_shortest_path_dijkstra(net, "A1", "S1")
    assert res.shortest_route is not None
    assert res.alternative_route is not None
    assert res.shortest_route.road_ids == ("R_FAST_THIN",)
    assert res.shortest_route.total_distance == pytest.approx(2.2)
    assert res.alternative_route.road_ids == ("R_WIDE_LONG",)
    assert res.alternative_route.total_distance == pytest.approx(4.8)


def test_dijkstra_returns_none_alternative_for_unique_path_and_handles_unreachable() -> None:
    net = EvacuationNetwork(network_id="unique-and-disc", name="Unique / Disconnected")
    net.add_node("A1", "Area", NodeType.AFFECTED_AREA, population=100)
    net.add_node("J1", "Relay", NodeType.JUNCTION)
    net.add_node("S1", "Reachable Shelter", NodeType.SHELTER, shelter_capacity=100)
    net.add_node("S2", "Isolated Shelter", NodeType.SHELTER, shelter_capacity=100)

    net.add_road("R1", "A1", "J1", capacity=100, distance=3.0)
    net.add_road("R2", "J1", "S1", capacity=100, distance=4.0)

    res_unique = solve_shortest_path_dijkstra(net, "A1", "S1")
    assert res_unique.reachable is True
    assert res_unique.shortest_route is not None
    assert res_unique.shortest_route.total_distance == pytest.approx(7.0)
    assert res_unique.alternative_route is None

    res_disc = solve_shortest_path_dijkstra(net, "A1", "S2")
    assert res_disc.reachable is False
    assert res_disc.shortest_route is None
    assert res_disc.alternative_route is None
    assert "S2" not in res_disc.distances_from_source


def test_dijkstra_validates_non_negative_distance_and_ignores_capacity_until_comparison() -> None:
    net = EvacuationNetwork(network_id="zero-dist-zero-cap", name="Zero Edge Edge Cases")
    net.add_node("A1", "Area", NodeType.AFFECTED_AREA, population=200)
    net.add_node("J1", "Staging", NodeType.JUNCTION)
    net.add_node("J2", "Staging 2", NodeType.JUNCTION)
    net.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=200)

    # Zero-distance active link cycle + zero-capacity short link
    net.add_road("R_ZERO_FWD", "A1", "J1", capacity=0, distance=0.0)
    net.add_road("R_CYCLE_1", "J1", "J2", capacity=100, distance=0.0)
    net.add_road("R_CYCLE_2", "J2", "J1", capacity=100, distance=0.0)
    net.add_road("R_J1_S1", "J1", "S1", capacity=200, distance=2.0)
    net.add_road("R_BYPASS", "A1", "S1", capacity=200, distance=5.0)

    # Negative distance must be rejected
    with pytest.raises(GraphValidationError):
        net.add_road("R_NEG", "A1", "S1", capacity=100, distance=-0.5)

    # NaN / inf distance must be rejected
    with pytest.raises(GraphValidationError):
        net.add_road("R_NAN", "A1", "S1", capacity=100, distance=math.nan)

    # Dijkstra ignores road capacity and skips zero-weight cycle safely
    res = solve_shortest_path_dijkstra(net, "A1", "S1")
    assert res.shortest_route is not None
    assert res.shortest_route.total_distance == pytest.approx(2.0)
    assert res.shortest_route.bottleneck_capacity == 0
    assert res.alternative_route is not None
    assert res.alternative_route.road_ids == ("R_BYPASS",)
    assert res.alternative_route.total_distance == pytest.approx(5.0)

    # Closed (inactive) road is excluded from drivable shortest path
    net.edit_road("R_ZERO_FWD", is_active=False)
    res_closed = solve_shortest_path_dijkstra(net, "A1", "S1")
    assert res_closed.shortest_route is not None
    assert res_closed.shortest_route.road_ids == ("R_BYPASS",)
    assert res_closed.alternative_route is None


def test_dijkstra_role_and_entity_validation_and_json_roundtrip() -> None:
    net = _build_educational_contrast_network()
    with pytest.raises(EntityNotFoundError):
        solve_shortest_path_dijkstra(net, "NO_SUCH_NODE", "S1")
    with pytest.raises(GraphValidationError):
        solve_shortest_path_dijkstra(net, "J1", "S1", require_area_and_shelter=True)
    with pytest.raises(GraphValidationError):
        solve_shortest_path_dijkstra(net, "A1", "J2", require_area_and_shelter=True)

    # Roundtrip preserves explicit distances; legacy JSON omitting distance defaults cleanly to 1.0
    restored = import_network_from_json(net.to_json())
    assert restored.get_road("R_A1_J1").distance == pytest.approx(1.5)
    assert restored.to_dict() == net.to_dict()

    legacy_json = (
        '{"schema_version": "1.0", "nodes": ['
        '{"node_id": "A1", "name": "A1", "node_type": "affected_area", "population": 10},'
        '{"node_id": "S1", "name": "S1", "node_type": "shelter", "shelter_capacity": 10}'
        '], "roads": ['
        '{"road_id": "R1", "source_id": "A1", "target_id": "S1", "capacity": 10}'
        ']}'
    )
    legacy_net = import_network_from_json(legacy_json)
    assert legacy_net.get_road("R1").distance == pytest.approx(1.0)


def test_compare_shortest_path_vs_dinic_max_flow_and_dinic_unchanged() -> None:
    # Verify Dinic produces exact same max flow as before and highlights conceptual differences
    trap = load_preset_network("greedy_trap_benchmark")
    dinic_standalone = DinicSolver().solve(build_evacuation_network(trap))
    assert dinic_standalone.max_flow == 2000

    # Pre-analysis comparison does not fabricate Dinic metrics
    pre_comp = compare_shortest_path_with_max_flow(trap, "A", "S", bundle=None)
    assert pre_comp.flow_analysis_available is False
    assert pre_comp.shortest_route is not None
    assert pre_comp.shortest_route.total_distance == pytest.approx(5.5)
    assert pre_comp.shortest_route.node_path == ("A", "J1", "J4", "S")
    assert pre_comp.alternative_route is not None
    assert pre_comp.alternative_route.node_path == ("A", "J9", "J2", "J4", "S")
    assert pre_comp.alternative_route.total_distance == pytest.approx(9.0)

    # Post-analysis comparison shows Dinic bypasses R_J1_J4 (0 flow) across longer corridors!
    bundle = run_full_evacuation_analysis(trap, trace=True)
    comp = compare_shortest_path_with_max_flow(trap, "A", "S", bundle=bundle)
    assert comp.flow_analysis_available is True
    assert comp.system_max_flow == 2000
    assert comp.pair_routed_flow == 2000
    assert comp.exact_shortest_path_used_by_dinic is False
    assert "different optimization" in comp.problem_distinction_summary.lower()
    assert any(s.road_id == "R_J1_J4" and s.dinic_flow == 0 for s in comp.shortest_road_statuses)

    # Also test default demo preset A1 -> S1 + Plotly shortest_path rendering
    demo = load_preset_network("metro_flood_baseline")
    demo_bundle = run_full_evacuation_analysis(demo, trace=True)
    demo_comp = compare_shortest_path_with_max_flow(demo, "A1", "S1", bundle=demo_bundle)
    assert demo_comp.shortest_route is not None
    assert demo_comp.shortest_route.node_path == ("A1", "J2", "J4", "S1")
    assert demo_comp.shortest_route.total_distance == pytest.approx(7.2)
    assert demo_comp.alternative_route is not None
    assert demo_comp.alternative_route.node_path == ("A1", "J1", "J4", "S1")
    assert demo_comp.alternative_route.total_distance == pytest.approx(10.0)

    fig = build_network_figure(
        demo,
        mode="shortest_path",
        dijkstra_result=demo_comp.dijkstra_result,
    )
    assert len(fig.data) > 0
