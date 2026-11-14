"""Tests for ResQ Relief Management Backend Services and Endpoints.

Verifies the four practical disaster management decisions:
1. Area Priority Assessment
2. Evacuation Route Recommendations
3. Shelter Capacity and Allocation Status
4. Camp Relief Resource Allocation & Fair Distribution Heuristic
Plus API integration via FastAPI TestClient.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.state import state_manager
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
    # Initialize with presentation demo dataset for relief testing
    c = TestClient(app)
    c.post("/api/network/presets/presentation_demo_dataset")
    return c


@pytest.fixture
def demo_network():
    return load_preset_network("presentation_demo_dataset")


# =====================================================================
# 1. Decision 1: Area Priority Assessment
# =====================================================================

def test_area_priority_assessment_ranks_and_explains(demo_network):
    assessments = assess_area_priorities(demo_network)
    assert len(assessments) == 5  # A1, A2, A3, A4, A5

    # Check that assessments are sorted in descending priority order
    for i in range(len(assessments) - 1):
        assert assessments[i].priority_score >= assessments[i + 1].priority_score

    # Check valid priority tiers and explanation strings
    area_dict = {a.area_id: a for a in assessments}
    for area_id, a in area_dict.items():
        assert a.priority_tier in [PriorityTier.CRITICAL, PriorityTier.HIGH, PriorityTier.MODERATE, PriorityTier.LOW]
        assert len(a.explanation) > 10
        assert a.time_to_impact_hours > 0
        assert a.population > 0

    # Top area should be Critical or High
    top_area = assessments[0]
    assert top_area.priority_tier in [PriorityTier.CRITICAL, PriorityTier.HIGH]
    assert "hazard" in top_area.explanation.lower() or "population" in top_area.explanation.lower()


def test_area_priority_custom_node_attributes(demo_network):
    # Verify fallback behavior when metadata is partially missing
    a5 = demo_network.nodes["A5"]
    a5.metadata.clear()  # wipe metadata to test default fallback logic

    assessments = assess_area_priorities(demo_network)
    a5_assessment = next(a for a in assessments if a.area_id == "A5")
    assert a5_assessment.hazard_severity == HazardSeverity.MODERATE  # default fallback
    assert a5_assessment.time_to_impact_hours == 6.0
    assert a5_assessment.vulnerable_population == 200  # 25% default fallback


# =====================================================================
# 2. Decision 2: Evacuation Route Recommendations
# =====================================================================

def test_route_recommendations_primary_and_alternative(demo_network):
    recommendations = recommend_evacuation_routes(demo_network)
    assert len(recommendations) > 0

    # Find recommendation for A1 -> S1
    a1_s1 = next((r for r in recommendations if r.source_id == "A1" and r.shelter_id == "S1"), None)
    assert a1_s1 is not None
    assert a1_s1.node_path[0] == "A1"
    assert a1_s1.node_path[-1] == "S1"
    assert a1_s1.total_distance_km > 0
    assert a1_s1.total_travel_time_min > 0


def test_route_recommendations_unverified_flag(demo_network):
    # R_A3_J4 is flagged as unverified_report in presentation demo dataset
    recommendations = recommend_evacuation_routes(demo_network)
    unverified = [r for r in recommendations if r.has_unverified_roads]
    assert len(unverified) >= 1
    for r in unverified:
        assert "R_A3_J4" in r.unverified_road_ids
        assert r.has_unverified_roads is True


# =====================================================================
# 3. Decision 3: Shelter Allocation Assessment
# =====================================================================

def test_shelter_allocation_with_dinic_intake(demo_network):
    statuses = assess_shelter_allocations(demo_network)
    assert len(statuses) == 4  # S1, S2, S3, S4

    shelter_dict = {s.shelter_id: s for s in statuses}
    total_assigned_intake = sum(s.expected_incoming for s in statuses)

    # Dinic max flow on presentation dataset is 4,350
    assert total_assigned_intake == 4350

    for s_id, s in shelter_dict.items():
        assert s.total_capacity > 0
        assert s.available_capacity == max(0, s.total_capacity - s.current_occupancy)
        assert s.projected_total == s.current_occupancy + s.expected_incoming
        assert len(s.serviced_area_ids) > 0


# =====================================================================
# 4. Decision 4: Camp Resource Allocation Heuristic
# =====================================================================

def test_camp_resource_allocation_proportional_and_shortages(demo_network):
    config = ResourceConsumptionConfig(planning_duration_days=3.0)
    result = allocate_camp_resources(demo_network, config=config)

    assert result.planning_duration_days == 3.0
    assert result.total_population_served > 0
    assert len(result.shelter_allocations) == 4
    assert len(result.central_depot_inventory) == 6
    assert len(result.total_allocated) == 6
    assert len(result.total_shortages) == 6

    # Verify each resource demand is computed and positive
    for s in result.shelter_allocations:
        assert s.total_occupants_served > 0
        for res_name in [SupplyResource.WATER.value, SupplyResource.FOOD.value, SupplyResource.MEDICAL_SUPPLIES.value]:
            detail = s.resources[res_name]
            assert detail.gross_demand > 0
            assert detail.fulfillment_pct <= 100.0

    # Verify that allocated depot stock never exceeds initial depot stock
    for res_name in SupplyResource:
        key = res_name.value
        init_val = result.central_depot_inventory.get(key, 0)
        alloc_val = result.total_allocated.get(key, 0)
        assert alloc_val <= init_val


def test_camp_resource_allocation_custom_config(demo_network):
    # Test with 7 days horizon vs 3 days horizon
    config_7d = ResourceConsumptionConfig(planning_duration_days=7.0)
    result_7d = allocate_camp_resources(demo_network, config=config_7d)

    config_3d = ResourceConsumptionConfig(planning_duration_days=3.0)
    result_3d = allocate_camp_resources(demo_network, config=config_3d)

    s1_demand_7d = next(s for s in result_7d.shelter_allocations if s.shelter_id == "S1")
    s1_demand_3d = next(s for s in result_3d.shelter_allocations if s.shelter_id == "S1")

    assert s1_demand_7d.resources[SupplyResource.WATER.value].gross_demand > s1_demand_3d.resources[SupplyResource.WATER.value].gross_demand


# =====================================================================
# 5. Algorithmic Distinction Invariant
# =====================================================================

def test_algorithm_distinction_dinic_vs_greedy_vs_relief(demo_network):
    from resq import solve_max_flow_dinic, solve_greedy_baseline

    # Dinic gives 4,350 max flow
    dinic_res = solve_max_flow_dinic(demo_network)
    assert dinic_res.max_flow == 4350

    # Greedy gives <= 4,350 flow
    greedy_res = solve_greedy_baseline(demo_network)
    assert greedy_res.max_flow <= dinic_res.max_flow

    # Camp resource heuristic allocates supplies according to Sphere standards,
    # completely independent of network edge capacities
    relief_res = allocate_camp_resources(demo_network)
    assert relief_res.total_population_served > 0
    assert relief_res.total_allocated[SupplyResource.WATER.value] > 0
    assert "mathematically independent from the Dinic Maximum Flow algorithm" in relief_res.algorithm_clarification


# =====================================================================
# 6. FastAPI Relief Endpoints Integration
# =====================================================================

def test_api_relief_overview(client):
    response = client.get("/api/relief/overview")
    assert response.status_code == 200
    data = response.json()
    assert "priorities" in data
    assert "routes" in data
    assert "shelters" in data
    assert "resources" in data
    assert "summary_advisories" in data
    assert "algorithm_clarification" in data
    assert len(data["priorities"]) == 5
    assert len(data["shelters"]) == 4


def test_api_relief_priorities(client):
    response = client.get("/api/relief/priorities")
    assert response.status_code == 200
    priorities = response.json()
    assert len(priorities) == 5
    first = priorities[0]
    assert "area_id" in first
    assert "priority_score" in first
    assert "priority_tier" in first
    assert "explanation" in first


def test_api_relief_routes(client):
    response = client.get("/api/relief/routes")
    assert response.status_code == 200
    routes = response.json()
    assert len(routes) > 0
    sample = routes[0]
    assert "route_id" in sample
    assert "source_id" in sample
    assert "shelter_id" in sample
    assert "node_path" in sample
    assert "total_distance_km" in sample


def test_api_relief_routes_verify(client):
    # Verify unverified road R_A3_J4
    verify_payload = {
        "road_id": "R_A3_J4",
        "new_status": "verified_clear",
        "hazard_risk_score": 0.05,
        "verification_notes": "Field scout inspected road; debris cleared, safe for transit."
    }
    response = client.post("/api/relief/routes/verify", json=verify_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["road_id"] == "R_A3_J4"
    assert data["safety_status"] == "verified_clear"
    assert data["is_active"] is True


def test_api_relief_shelters(client):
    response = client.get("/api/relief/shelters")
    assert response.status_code == 200
    shelters = response.json()
    assert len(shelters) == 4
    for s in shelters:
        assert "shelter_id" in s
        assert "total_capacity" in s
        assert "available_capacity" in s
        assert "expected_incoming" in s


def test_api_relief_resources_get_and_post(client):
    # GET default resources
    get_resp = client.get("/api/relief/resources?days=3")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["planning_duration_days"] == 3.0
    assert "shelter_allocations" in data

    # POST custom configuration (5 days)
    post_payload = {
        "planning_duration_days": 5.0,
        "water_liters_per_person_day": 3.5,
    }
    post_resp = client.post("/api/relief/resources", json=post_payload)
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert post_data["planning_duration_days"] == 5.0
    assert post_data["total_demand"]["water_liters"] > data["total_demand"]["water_liters"]
