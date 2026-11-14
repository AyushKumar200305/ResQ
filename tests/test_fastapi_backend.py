"""Comprehensive integration test suite for ResQ FastAPI backend API endpoints."""

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.state import state_manager


@pytest.fixture(autouse=True)
def reset_backend_state():
    """Ensure every test begins with a fresh clean demo network."""
    state_manager.reset_to_preset("metro_flood_baseline")
    yield
    state_manager.reset_to_preset("metro_flood_baseline")


@pytest.fixture
def client():
    """TestClient instance for making API requests."""
    return TestClient(app)


def test_root_and_health_endpoints(client):
    """Test GET / and GET /api/health."""
    r_root = client.get("/")
    assert r_root.status_code == 200
    root_data = r_root.json()
    assert root_data["status"] == "operational"
    assert "documentation" in root_data

    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    health_data = r_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["version"] == "1.0.0"
    assert health_data["active_network"]["network_id"] == "metro-flood-baseline"
    assert health_data["active_network"]["nodes_count"] == 11
    assert health_data["active_network"]["roads_count"] == 15


def test_network_get_and_demo_reload(client):
    """Test GET /api/network and POST /api/network/demo."""
    r = client.get("/api/network")
    assert r.status_code == 200
    data = r.json()
    assert data["network_id"] == "metro-flood-baseline"
    assert data["total_population"] == 3100
    assert data["total_shelter_capacity"] == 3300
    assert len(data["nodes"]) == 11
    assert len(data["roads"]) == 15

    r_demo = client.post("/api/network/demo")
    assert r_demo.status_code == 200
    assert r_demo.json()["network_id"] == "metro-flood-baseline"


def test_presets_list_and_load(client):
    """Test GET /api/network/presets and POST /api/network/presets/{key}."""
    r = client.get("/api/network/presets")
    assert r.status_code == 200
    presets = r.json()
    assert len(presets) >= 4
    keys = [p["key"] for p in presets]
    assert "metro_flood_baseline" in keys
    assert "greedy_trap_benchmark" in keys

    r_load = client.post("/api/network/presets/greedy_trap_benchmark")
    assert r_load.status_code == 200
    trap_data = r_load.json()
    assert trap_data["network_id"] == "greedy-trap-benchmark"

    r_college = client.post("/api/network/presets/presentation_demo_dataset")
    assert r_college.status_code == 200
    college_data = r_college.json()
    assert college_data["network_id"] == "presentation-demo-dataset"
    assert len(college_data["nodes"]) == 19
    assert len(college_data["roads"]) == 26
    assert college_data["total_population"] == 5500
    assert college_data["total_shelter_capacity"] == 5100

    r_bad = client.post("/api/network/presets/non_existent_preset_key")
    assert r_bad.status_code == 404
    assert "Unknown preset" in r_bad.json()["detail"]


def test_network_validation_endpoint(client):
    """Test GET /api/network/validate."""
    r = client.get("/api/network/validate")
    assert r.status_code == 200
    data = r.json()
    assert data["is_valid"] is True
    assert data["errors"] == []
    assert data["affected_areas_count"] == 3
    assert data["shelters_count"] == 3


def test_node_crud_endpoints(client):
    """Test POST, PUT, DELETE for nodes including duplicate and 404 guards."""
    new_node = {
        "node_id": "TEST_A1",
        "name": "Test Affected Zone",
        "node_type": "affected_area",
        "population": 450,
        "shelter_capacity": 0,
        "x": 100.0,
        "y": 200.0,
    }
    r_create = client.post("/api/network/nodes", json=new_node)
    assert r_create.status_code == 201
    created_data = r_create.json()
    assert created_data["node_id"] == "TEST_A1"
    assert created_data["population"] == 450

    # Duplicate ID -> 409
    r_dup = client.post("/api/network/nodes", json=new_node)
    assert r_dup.status_code == 409
    assert "already exists" in r_dup.json()["detail"]

    # Update node
    r_update = client.put("/api/network/nodes/TEST_A1", json={"population": 600, "name": "Updated Zone"})
    assert r_update.status_code == 200
    assert r_update.json()["population"] == 600
    assert r_update.json()["name"] == "Updated Zone"

    # Update non-existent -> 404
    r_bad_update = client.put("/api/network/nodes/DOES_NOT_EXIST", json={"population": 100})
    assert r_bad_update.status_code == 404

    # Delete node
    r_del = client.delete("/api/network/nodes/TEST_A1")
    assert r_del.status_code == 200
    assert r_del.json()["deleted_node_id"] == "TEST_A1"

    # Delete non-existent -> 404
    r_bad_del = client.delete("/api/network/nodes/TEST_A1")
    assert r_bad_del.status_code == 404


def test_road_crud_endpoints(client):
    """Test POST, PUT, DELETE for roads including invalid endpoint and 404 guards."""
    new_road = {
        "road_id": "TEST_R1",
        "source_id": "A1",
        "target_id": "J1",
        "capacity": 750,
        "name": "Emergency Spur",
        "distance": 3.2,
        "is_active": True,
    }
    r_create = client.post("/api/network/roads", json=new_road)
    assert r_create.status_code == 201
    road_data = r_create.json()
    assert road_data["road_id"] == "TEST_R1"
    assert road_data["capacity"] == 750

    # Self loop -> 400
    bad_road = {
        "road_id": "BAD_LOOP",
        "source_id": "A1",
        "target_id": "A1",
        "capacity": 100,
    }
    r_loop = client.post("/api/network/roads", json=bad_road)
    assert r_loop.status_code == 400
    assert "cannot be a self-loop" in r_loop.json()["detail"]

    # Update road
    r_update = client.put("/api/network/roads/TEST_R1", json={"capacity": 900, "is_active": False})
    assert r_update.status_code == 200
    assert r_update.json()["capacity"] == 900
    assert r_update.json()["effective_capacity"] == 0
    assert r_update.json()["is_active"] is False

    # Update non-existent -> 404
    r_bad_up = client.put("/api/network/roads/UNKNOWN_ROAD", json={"capacity": 500})
    assert r_bad_up.status_code == 404

    # Delete road
    r_del = client.delete("/api/network/roads/TEST_R1")
    assert r_del.status_code == 200
    assert r_del.json()["deleted_road_id"] == "TEST_R1"

    # Delete non-existent -> 404
    r_bad_del = client.delete("/api/network/roads/TEST_R1")
    assert r_bad_del.status_code == 404


def test_solve_dinic_and_mincut(client):
    """Test POST /api/solve/dinic, GET /api/solve/dinic, and POST /api/solve/mincut."""
    # Run Dinic
    r_dinic = client.post("/api/solve/dinic?trace=true")
    assert r_dinic.status_code == 200
    d_data = r_dinic.json()
    assert d_data["max_flow"] == 2250
    assert d_data["total_population"] == 3100
    assert d_data["unmet_demand"] == 850
    assert len(d_data["road_flows"]) == 15
    assert len(d_data["source_evacuations"]) == 3
    assert len(d_data["shelter_intakes"]) == 3
    assert d_data["phase_trace"] is not None

    # Get cached Dinic
    r_get_dinic = client.get("/api/solve/dinic")
    assert r_get_dinic.status_code == 200
    assert r_get_dinic.json()["max_flow"] == 2250

    # Run Min-Cut
    r_mc = client.post("/api/solve/mincut")
    assert r_mc.status_code == 200
    mc_data = r_mc.json()
    # Max-Flow = Min-Cut theorem
    assert mc_data["total_cut_capacity"] == 2250
    assert len(mc_data["reachable_node_ids"]) > 0
    assert len(mc_data["unreachable_node_ids"]) > 0
    assert len(mc_data["road_bottlenecks"]) >= 1


def test_solve_full_analysis_and_waves(client):
    """Test POST /api/solve/full and POST /api/solve/waves."""
    r_full = client.post("/api/solve/full?wave_hours=6&upgrade_delta=150")
    assert r_full.status_code == 200
    full_data = r_full.json()
    assert full_data["dinic"]["max_flow"] == 2250
    assert full_data["min_cut"]["total_cut_capacity"] == 2250
    assert len(full_data["routes"]) >= 1
    assert len(full_data["upgrade_candidates"]) >= 1
    assert len(full_data["wave_timeline"]) == 6

    # Waves standalone endpoint
    r_waves = client.post("/api/solve/waves?hours=4")
    assert r_waves.status_code == 200
    waves_data = r_waves.json()
    assert len(waves_data) == 4
    assert waves_data[0]["hour"] == 1
    assert waves_data[0]["evacuated_this_hour"] == 2250
    assert waves_data[1]["hour"] == 2
    assert waves_data[1]["cumulative_evacuated"] == 3100  # Cleared by hour 2


def test_solve_trace_and_playback(client):
    """Test GET /api/solve/trace and POST /api/solve/playback."""
    r_trace = client.get("/api/solve/trace")
    assert r_trace.status_code == 200
    trace_data = r_trace.json()
    assert trace_data["algorithm"] == "Dinic's Maximum Flow Algorithm"
    assert trace_data["time_complexity"] == "O(V^2 E)"
    assert trace_data["max_flow"] == 2250
    assert len(trace_data["phases"]) >= 1

    r_playback = client.post("/api/solve/playback")
    assert r_playback.status_code == 200
    pb_data = r_playback.json()
    assert pb_data["total_frames"] >= 1
    assert pb_data["max_flow"] == 2250
    first_frame = pb_data["frames"][0]
    assert first_frame["step_index"] == 0
    assert "explanation" in first_frame


def test_scenario_lab_endpoints(client):
    """Test all Scenario Lab endpoints: baseline, road closure, reduced shelter, increased shelter, multi-road failure, and all."""
    # 1. Baseline
    r_base = client.post("/api/scenarios/baseline")
    assert r_base.status_code == 200
    assert r_base.json()["max_flow"] == 2250
    assert r_base.json()["baseline_delta"] == 0

    # 2. Road closure
    r_close = client.post("/api/scenarios/road-closure", json={"road_id": "R_J1_J4"})
    assert r_close.status_code == 200
    close_data = r_close.json()
    assert close_data["scenario_kind"] == "road_closure"
    assert close_data["max_flow"] <= 2250

    # 3. Reduced shelter
    r_red = client.post("/api/scenarios/reduced-shelter", json={"shelter_id": "S1", "new_capacity": 300})
    assert r_red.status_code == 200
    red_data = r_red.json()
    assert red_data["scenario_kind"] == "reduced_shelter"

    # 4. Increased shelter
    r_inc = client.post("/api/scenarios/increased-shelter", json={"shelter_id": "S2", "added_capacity": 400})
    assert r_inc.status_code == 200

    # 5. Multi-road failure
    r_multi = client.post("/api/scenarios/multi-road-failure", json={"road_ids": ["R_J1_J4", "R_A1_J1"]})
    assert r_multi.status_code == 200
    assert r_multi.json()["scenario_kind"] == "multi_road_failure"

    # 6. All 5 scenarios
    r_all = client.post("/api/scenarios/all")
    assert r_all.status_code == 200
    all_data = r_all.json()
    assert all_data["baseline_flow"] == 2250
    assert len(all_data["scenarios"]) == 5


def test_algorithm_comparison_greedy_and_benchmark(client):
    """Test POST /api/comparison/greedy and POST /api/comparison/benchmark."""
    # Load greedy trap benchmark to verify greedy suboptimality
    client.post("/api/network/presets/greedy_trap_benchmark")

    r_greedy = client.post("/api/comparison/greedy", json={"rule": "shortest_hop", "repeats": 2})
    assert r_greedy.status_code == 200
    comp_data = r_greedy.json()
    assert comp_data["dinic_max_flow"] == 2000
    assert comp_data["greedy_flow"] == 1000
    assert comp_data["flow_difference"] == 1000
    assert comp_data["optimality_gap_pct"] == 50.0

    # Scalability benchmark (1 repetition for fast testing)
    r_bench = client.post("/api/comparison/benchmark?repeats=1")
    assert r_bench.status_code == 200
    bench_data = r_bench.json()
    assert len(bench_data["tiers"]) == 5
    assert bench_data["tiers"][0]["tier_name"] == "XS (12V)"


def test_dijkstra_shortest_path_endpoint(client):
    """Test POST /api/dijkstra/solve."""
    r = client.post("/api/dijkstra/solve", json={"source_id": "A1", "shelter_id": "S1"})
    assert r.status_code == 200
    dijk_data = r.json()
    assert dijk_data["is_reachable"] is True
    assert dijk_data["shortest_route"] is not None
    assert dijk_data["shortest_route"]["total_distance"] > 0.0
    assert len(dijk_data["shortest_route"]["node_path"]) >= 2
    assert dijk_data["shortest_route"]["node_path"][0] == "A1"
    assert dijk_data["shortest_route"]["node_path"][-1] == "S1"
    assert dijk_data["comparison"] is not None

    # Invalid node -> 404
    r_bad = client.post("/api/dijkstra/solve", json={"source_id": "DOES_NOT_EXIST", "shelter_id": "S1"})
    assert r_bad.status_code == 404


def test_report_export_endpoints(client):
    """Test GET /api/reports/json, /csv/roads, /csv/scenarios, and /pdf."""
    # JSON export
    r_json = client.get("/api/reports/json")
    assert r_json.status_code == 200
    assert r_json.headers["content-type"] == "application/json"
    assert "attachment; filename=" in r_json.headers["content-disposition"]
    assert "schema_version" in r_json.text

    # CSV road flows export
    r_csv_roads = client.get("/api/reports/csv/roads")
    assert r_csv_roads.status_code == 200
    assert "text/csv" in r_csv_roads.headers["content-type"]
    assert "Road ID,Name,From,To,Capacity,Flow" in r_csv_roads.text

    # CSV scenarios export
    r_csv_scenarios = client.get("/api/reports/csv/scenarios")
    assert r_csv_scenarios.status_code == 200
    assert "text/csv" in r_csv_scenarios.headers["content-type"]
    assert "Scenario Name,Maximum Flow" in r_csv_scenarios.text

    # PDF situation report export
    r_pdf = client.get("/api/reports/pdf")
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert r_pdf.content.startswith(b"%PDF-")
    assert len(r_pdf.content) > 1000
