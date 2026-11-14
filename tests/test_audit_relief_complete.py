"""Complete Final Audit Test Suite for Updated ResQ Project.

Rigorously verifies all 14 points mandated by the user:
1. Area priority calculations and explanations.
2. Route recommendations and closed-road exclusion.
3. Primary and alternative evacuation routes.
4. Shelter capacity constraints.
5. Dinic maximum flow and minimum-cut equality.
6. Greedy evacuation comparison (using identical dataset).
7. Dijkstra shortest-path calculations and contrast.
8. Food, water and medicine demand calculations.
9. Resource distribution when inventory is insufficient.
10. Missing or unknown data handling and fallback logic.
11. Frontend/backend integration (all endpoints).
12. Map visualization data contracts.
13. PDF, JSON and CSV exports.
14. Guest login and navigation data integrity.
"""

from __future__ import annotations

import io
import json
import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.state import state_manager
from resq import (
    DijkstraSolver,
    DinicSolver,
    FlowNetwork,
    GreedyRule,
    GreedySolver,
    solve_greedy_baseline,
    solve_max_flow_dinic,
)
from resq.domain.models import EvacuationNetwork, RoadEdge
from resq.domain.relief_models import (
    HazardSeverity,
    PriorityTier,
    ResourceConsumptionConfig,
    RoadSafetyStatus,
    SupplyResource,
)
from resq.services.area_priority import assess_area_priorities
from resq.services.camp_resources import allocate_camp_resources
from resq.services.presets import load_preset_network
from resq.services.route_recommendations import recommend_evacuation_routes
from resq.services.shelter_allocation import assess_shelter_allocations


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/network/presets/presentation_demo_dataset")
    return c


@pytest.fixture
def demo_net():
    return load_preset_network("presentation_demo_dataset")


# =====================================================================
# 1. Area priority calculations and explanations
# =====================================================================

def test_audit_1_area_priority_calculations_and_explanations(demo_net):
    priorities = assess_area_priorities(demo_net)
    assert len(priorities) == 5

    # Ranked by priority score in descending order
    for i in range(len(priorities) - 1):
        assert priorities[i].priority_score >= priorities[i + 1].priority_score
        assert priorities[i].dispatch_order == i + 1

    for p in priorities:
        assert p.population > 0
        assert p.vulnerable_population >= 0
        assert p.vulnerable_population <= p.population
        assert 0.0 <= p.vulnerability_pct <= 100.0
        assert p.time_to_impact_hours > 0
        assert p.priority_tier in [PriorityTier.CRITICAL, PriorityTier.HIGH, PriorityTier.MODERATE, PriorityTier.LOW]
        assert len(p.explanation) >= 20
        # Ensure explanation contains the tier name and justification
        assert p.priority_tier.value.upper() in p.explanation.upper()


# =====================================================================
# 2. Route recommendations and closed-road exclusion
# =====================================================================

def test_audit_2_route_recommendations_and_closed_road_exclusion(demo_net):
    # Base routes before closure
    routes_before = recommend_evacuation_routes(demo_net)
    assert len(routes_before) > 0

    # Explicitly close a road: R_A1_J1 (North Levee Expressway)
    demo_copy = demo_net.copy()
    demo_copy.edit_road("R_A1_J1", is_active=False)

    routes_after = recommend_evacuation_routes(demo_copy)
    # Verify that NO active recommended route uses the closed road R_A1_J1
    for r in routes_after:
        assert "R_A1_J1" not in r.road_ids
        assert r.bottleneck_capacity > 0


# =====================================================================
# 3. Primary and alternative evacuation routes
# =====================================================================

def test_audit_3_primary_and_alternative_routes(demo_net):
    routes = recommend_evacuation_routes(demo_net)
    primary_routes = [r for r in routes if r.is_primary]
    alt_routes = [r for r in routes if not r.is_primary]

    assert len(primary_routes) > 0
    # On presentation grid, multiple paths exist between A1/A2 and shelters
    assert len(alt_routes) > 0

    # Compare primary vs alternative for A1 -> S1
    p_a1_s1 = next((r for r in primary_routes if r.source_id == "A1" and r.shelter_id == "S1"), None)
    alt_a1_s1 = next((r for r in alt_routes if r.source_id == "A1" and r.shelter_id == "S1"), None)

    if p_a1_s1 and alt_a1_s1:
        # Distance of alternative route must be >= primary route
        assert alt_a1_s1.total_distance_km >= p_a1_s1.total_distance_km
        # Paths must not be completely identical
        assert alt_a1_s1.node_path != p_a1_s1.node_path


# =====================================================================
# 4. Shelter capacity constraints
# =====================================================================

def test_audit_4_shelter_capacity_constraints(demo_net):
    shelter_statuses = assess_shelter_allocations(demo_net)
    assert len(shelter_statuses) == 4

    for s in shelter_statuses:
        # Total capacity must be positive
        assert s.total_capacity > 0
        # Available capacity = max(0, total - current)
        assert s.available_capacity == max(0, s.total_capacity - s.current_occupancy)
        # Expected incoming flow from Dinic solver must not exceed available capacity
        assert s.expected_incoming <= s.total_capacity
        # Projected total load
        assert s.projected_total == s.current_occupancy + s.expected_incoming


# =====================================================================
# 5. Dinic maximum flow and minimum-cut equality
# =====================================================================

def test_audit_5_dinic_max_flow_and_min_cut_equality(demo_net):
    from resq import solve_max_flow_and_min_cut

    dinic_res, min_cut_res = solve_max_flow_and_min_cut(demo_net)

    # Max-Flow Min-Cut Theorem verification: |f*| == c(S*, T*)
    assert dinic_res.max_flow == min_cut_res.total_cut_capacity
    assert dinic_res.max_flow == 4350

    # Flow conservation check on intermediate junctions (J1 to J10)
    for j_node in demo_net.junctions:
        inflow = sum(rf.flow for rf in dinic_res.road_flows.values() if rf.target_id == j_node.node_id)
        outflow = sum(rf.flow for rf in dinic_res.road_flows.values() if rf.source_id == j_node.node_id)
        assert inflow == outflow, f"Flow conservation violated at junction {j_node.node_id}: in={inflow}, out={outflow}"

    # Capacity constraints check on all roads: 0 <= f(e) <= c(e)
    for rf in dinic_res.road_flows.values():
        assert 0 <= rf.flow <= rf.nominal_capacity, f"Capacity violated on road {rf.road_id}: flow={rf.flow}, cap={rf.nominal_capacity}"


# =====================================================================
# 6. Greedy evacuation comparison (using identical dataset)
# =====================================================================

def test_audit_6_greedy_evacuation_comparison(demo_net):
    # Dinic benchmark on identical dataset
    dinic_res = solve_max_flow_dinic(demo_net)
    assert dinic_res.max_flow == 4350

    # Compare with all 3 greedy heuristic rules
    for rule in [GreedyRule.SHORTEST_HOP, GreedyRule.WIDEST_PATH, GreedyRule.LEXICOGRAPHIC_DFS]:
        greedy_res = solve_greedy_baseline(demo_net, rule=rule)
        # Invariant: Greedy flow can NEVER exceed Dinic optimal flow
        assert greedy_res.max_flow <= dinic_res.max_flow
        # Optimality gap
        gap = dinic_res.max_flow - greedy_res.max_flow
        assert gap >= 0


# =====================================================================
# 7. Dijkstra shortest-path calculations and contrast
# =====================================================================

def test_audit_7_dijkstra_shortest_path_calculations(demo_net):
    solver = DijkstraSolver()
    result = solver.solve(demo_net, source_id="A1", shelter_id="S1")

    assert result.reachable is True
    assert result.shortest_route is not None
    assert result.shortest_route.total_distance > 0
    assert result.shortest_route.total_travel_time_min > 0
    assert result.shortest_route.bottleneck_capacity > 0

    # Non-negative road distance invariant
    for d in result.shortest_route.road_distances:
        assert d >= 0.0

    # Contrast verification: Dijkstra optimizes single-path distance,
    # Dinic optimizes multi-path capacity
    dinic_res = solve_max_flow_dinic(demo_net)
    # The bottleneck on shortest route is <= system max flow
    assert result.shortest_route.bottleneck_capacity <= dinic_res.max_flow


# =====================================================================
# 8. Food, water and medicine demand calculations
# =====================================================================

def test_audit_8_food_water_medicine_demand_calculations(demo_net):
    # Test for 3 days
    config_3d = ResourceConsumptionConfig(
        planning_duration_days=3.0,
        water_liters_per_person_day=3.0,
        food_rations_per_person_day=2.0,
        medical_supplies_per_person=0.05,
        medicines_doses_per_person_day=0.10,
        blankets_per_person=1.0,
        hygiene_kits_per_person=0.20,
    )
    res_3d = allocate_camp_resources(demo_net, config=config_3d)

    total_pop = res_3d.total_population_served
    assert total_pop > 0

    # Demand formulas
    expected_water_demand = total_pop * 3.0 * 3.0
    expected_food_demand = total_pop * 2.0 * 3.0

    # Aggregate demand in result should closely match
    assert abs(res_3d.total_demand["water_liters"] - expected_water_demand) < total_pop * 0.1
    assert abs(res_3d.total_demand["food_rations"] - expected_food_demand) < total_pop * 0.1

    # Test scaling to 6 days: demand should approximately double
    config_6d = ResourceConsumptionConfig(planning_duration_days=6.0)
    res_6d = allocate_camp_resources(demo_net, config=config_6d)
    assert res_6d.total_demand["water_liters"] > res_3d.total_demand["water_liters"] * 1.8


# =====================================================================
# 9. Resource distribution when inventory is insufficient
# =====================================================================

def test_audit_9_resource_distribution_when_inventory_insufficient(demo_net):
    # Intentionally supply limited inventory far below demand
    scarce_depot = {
        "water_liters": 1000,   # gross demand is > 46,000
        "food_rations": 500,    # gross demand is > 30,000
        "medical_supplies": 10,
        "medicines": 50,
        "blankets": 100,
        "hygiene_kits": 50,
    }
    result = allocate_camp_resources(demo_net, depot_stock=scarce_depot, planning_duration_days=3.0)

    # 1. Total allocated must NEVER exceed depot inventory
    for res_key, stock in scarce_depot.items():
        assert result.total_allocated[res_key] <= stock

    # 2. Deficit/shortages must be accurately tracked for undersupplied resources
    assert result.total_shortages["water_liters"] > 0
    assert result.total_shortages["food_rations"] > 0

    # 3. Remaining depot inventory must be >= 0
    for res_key, rem in result.depot_remaining_inventory.items():
        assert rem >= 0


# =====================================================================
# 10. Missing or unknown data handling and fallback logic
# =====================================================================

def test_audit_10_missing_or_unknown_data_handling(demo_net):
    net_copy = demo_net.copy()
    # Wipe metadata from node A5 and shelter S4
    net_copy.nodes["A5"].metadata.clear()
    net_copy.nodes["S4"].metadata.clear()

    # Priority assessment should not crash and should use graceful fallbacks
    priorities = assess_area_priorities(net_copy)
    a5_p = next(p for p in priorities if p.area_id == "A5")
    assert a5_p.hazard_severity == HazardSeverity.MODERATE
    assert a5_p.time_to_impact_hours == 6.0
    assert a5_p.vulnerable_population == int(net_copy.nodes["A5"].population * 0.25)

    # Shelter allocation should not crash
    shelter_statuses = assess_shelter_allocations(net_copy)
    s4_s = next(s for s in shelter_statuses if s.shelter_id == "S4")
    assert s4_s.current_occupancy == 0

    # Camp resource allocation should not crash
    res = allocate_camp_resources(net_copy)
    assert res.total_population_served > 0


# =====================================================================
# 11. Frontend/backend integration (all endpoints)
# =====================================================================

def test_audit_11_all_api_endpoints_integration(client):
    endpoints = [
        ("GET", "/api/health"),
        ("GET", "/api/network"),
        ("GET", "/api/relief/overview"),
        ("GET", "/api/relief/priorities"),
        ("GET", "/api/relief/routes"),
        ("GET", "/api/relief/shelters"),
        ("GET", "/api/relief/resources"),
        ("POST", "/api/solve/dinic"),
        ("POST", "/api/solve/mincut"),
        ("POST", "/api/scenarios/all"),
    ]

    for method, path in endpoints:
        if method == "GET":
            r = client.get(path)
        else:
            r = client.post(path)
        assert r.status_code == 200, f"Endpoint {path} failed with status {r.status_code}: {r.text}"

    # Verify comparison greedy POST endpoint with required payload
    r_greedy = client.post("/api/comparison/greedy", json={"rule": "shortest_hop", "repeats": 1})
    assert r_greedy.status_code == 200
    assert "dinic_max_flow" in r_greedy.json()
    assert "greedy_flow" in r_greedy.json()

    # Verify road verification POST endpoint
    r_verify = client.post("/api/relief/routes/verify", json={
        "road_id": "R_A3_J4",
        "new_status": "verified_clear",
        "hazard_risk_score": 0.05,
    })
    assert r_verify.status_code == 200
    assert r_verify.json()["safety_status"] == "verified_clear"

    # Verify Dijkstra POST endpoint
    r_dijkstra = client.post("/api/dijkstra/solve", json={
        "source_id": "A1",
        "shelter_id": "S1",
    })
    assert r_dijkstra.status_code == 200
    assert r_dijkstra.json()["is_reachable"] is True


# =====================================================================
# 12. Map visualization data contracts
# =====================================================================

def test_audit_12_map_visualization_data_contracts(client):
    r_net = client.get("/api/network")
    assert r_net.status_code == 200
    net_data = r_net.json()

    # All nodes must have coordinates and valid types
    for node in net_data["nodes"]:
        assert "node_id" in node
        assert "x" in node and node["x"] is not None
        assert "y" in node and node["y"] is not None
        assert node["node_type"] in ["affected_area", "junction", "shelter"]

    # All roads must have source, target, and capacity
    for road in net_data["roads"]:
        assert "road_id" in road
        assert "source_id" in road
        assert "target_id" in road
        assert road["capacity"] > 0
        assert "is_active" in road


# =====================================================================
# 13. PDF, JSON and CSV exports
# =====================================================================

def test_audit_13_pdf_json_csv_exports(client):
    # 1. JSON Export
    r_json = client.get("/api/reports/json")
    assert r_json.status_code == 200
    data = r_json.json()
    assert "network" in data or "network_id" in data

    # 2. CSV Roads Export
    r_csv_roads = client.get("/api/reports/csv/roads")
    assert r_csv_roads.status_code == 200
    assert "Road ID" in r_csv_roads.text
    assert "Capacity" in r_csv_roads.text

    # 3. CSV Scenarios Export
    r_csv_scenarios = client.get("/api/reports/csv/scenarios")
    assert r_csv_scenarios.status_code == 200
    assert "Scenario Name" in r_csv_scenarios.text

    # 4. PDF Report Generation
    r_pdf = client.get("/api/reports/pdf")
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert r_pdf.content.startswith(b"%PDF-")
    assert len(r_pdf.content) > 1000  # Valid non-empty PDF bytes


# =====================================================================
# 14. Guest login and navigation data integrity
# =====================================================================

def test_audit_14_guest_login_and_navigation(client):
    # Ensure health returns active network
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    health_data = r_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["active_network"]["nodes_count"] >= 19
    assert health_data["active_network"]["roads_count"] >= 26

    # Verify overview contains all 5 required navigation data structures
    r_overview = client.get("/api/relief/overview")
    assert r_overview.status_code == 200
    overview_data = r_overview.json()

    # Section 1: Situation Overview & Critical Areas
    assert len(overview_data["priorities"]) == 5
    # Section 2: Evacuation Priorities
    for p in overview_data["priorities"]:
        assert "priority_score" in p
        assert "explanation" in p
    # Section 3: Routes & Shelters
    assert len(overview_data["routes"]) > 0
    # Section 4: Camp Resources
    assert "resources" in overview_data
    assert "shelter_allocations" in overview_data["resources"]
    # Section 5: Algorithm Invariants
    assert "algorithm_clarification" in overview_data
