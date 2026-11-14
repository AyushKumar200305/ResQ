"""Final Audit & Presentation Readiness Verification Test Suite.

Validates:
1. Fast, live API communication between frontend expectations and backend endpoints.
2. Presentation demo dataset integrity (5 hazard zones, 10 junctions, 4 shelters, 26 roads).
3. Dinic maximum-flow and Minimum-Cut exact theorem equivalence (|f*| == c(S*, T*)).
4. Dijkstra shortest path vs max-flow separation.
5. All 5 scenario lab what-if simulations with independent copies.
6. Reports & export generation (PDF, JSON, CSV roads, CSV scenarios).
"""

import json
import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.state import state_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_final_audit_presentation_dataset_and_solver_integrity(client):
    """Verify demo dataset loading and algorithmic correctness."""
    # 1. Load Presentation Demo Grid
    r_load = client.post("/api/network/presets/presentation_demo_dataset")
    assert r_load.status_code == 200
    net_data = r_load.json()
    assert net_data["network_id"] == "presentation-demo-dataset"
    assert len(net_data["nodes"]) == 19
    assert len(net_data["roads"]) == 26
    assert net_data["total_population"] == 5500
    assert net_data["total_shelter_capacity"] == 5100

    # 2. Run Dinic's Algorithm
    r_dinic = client.post("/api/solve/dinic?trace=true")
    assert r_dinic.status_code == 200
    dinic_res = r_dinic.json()
    assert dinic_res["max_flow"] == 4350
    assert dinic_res["unmet_demand"] == 1150
    assert dinic_res["bfs_phases"] > 0
    assert dinic_res["total_augmentations"] > 0
    assert len(dinic_res["road_flows"]) == 26

    # 3. Extract Minimum Cut & Verify Theorem
    r_mincut = client.post("/api/solve/mincut")
    assert r_mincut.status_code == 200
    mincut_res = r_mincut.json()
    assert mincut_res["total_cut_capacity"] == dinic_res["max_flow"]
    assert len(mincut_res["road_bottlenecks"]) == 4
    assert len(mincut_res["shelter_capacity_cuts"]) == 1
    assert mincut_res["shelter_capacity_cuts"][0]["source_id"] == "S3"

    # 4. Run Full Analysis (Routes + Upgrades + Waves)
    r_full = client.post("/api/solve/full?wave_hours=8&upgrade_delta=100")
    assert r_full.status_code == 200
    full_data = r_full.json()
    assert len(full_data["routes"]) > 0
    assert len(full_data["upgrade_candidates"]) > 0
    assert len(full_data["wave_timeline"]) == 8


def test_final_audit_dijkstra_shortest_path_vs_flow(client):
    """Verify educational Dijkstra shortest-path calculations."""
    client.post("/api/network/presets/presentation_demo_dataset")
    r = client.post("/api/dijkstra/solve", json={"source_id": "A1", "shelter_id": "S1"})
    assert r.status_code == 200
    data = r.json()
    assert data["is_reachable"] is True
    assert data["shortest_route"]["node_path"] == ["A1", "J2", "J6", "S1"]
    assert round(data["shortest_route"]["total_distance"], 1) == 7.6


def test_final_audit_scenario_lab_and_independent_copies(client):
    """Verify all 5 scenarios and ensure the baseline network is not mutated."""
    client.post("/api/network/presets/presentation_demo_dataset")
    base_net_before = client.get("/api/network").json()

    # Run all 5 scenarios
    r_all = client.post("/api/scenarios/all")
    assert r_all.status_code == 200
    sc_summary = r_all.json()
    assert sc_summary["baseline_flow"] == 4350
    assert len(sc_summary["scenarios"]) == 5

    # Check deltas
    deltas = {s["scenario_name"]: s["baseline_delta"] for s in sc_summary["scenarios"]}
    assert deltas["Scenario 1: Normal Conditions (Baseline)"] == 0
    assert deltas["Scenario 2: Road Closure (R_J1_J6)"] == -750
    assert deltas["Scenario 3: Reduced Shelter (S1)"] == -334
    assert deltas["Scenario 4: Increased Shelter (S3)"] == 100
    assert deltas["Scenario 5: Multiple Road Failures (2)"] == -1200

    # Ensure baseline network is completely unchanged
    base_net_after = client.get("/api/network").json()
    assert base_net_after == base_net_before


def test_final_audit_report_downloads_and_formatting(client):
    """Verify actual generation of JSON, CSV (roads & scenarios), and PDF."""
    client.post("/api/network/presets/presentation_demo_dataset")

    # 1. JSON
    r_json = client.get("/api/reports/json")
    assert r_json.status_code == 200
    parsed = json.loads(r_json.content)
    assert parsed["network_id"] == "presentation-demo-dataset"
    assert len(parsed["nodes"]) == 19

    # 2. CSV Roads
    r_roads = client.get("/api/reports/csv/roads")
    assert r_roads.status_code == 200
    lines = r_roads.text.strip().split("\n")
    assert lines[0].startswith("Road ID,Name,From,To")
    assert len(lines) == 27  # header + 26 roads

    # 3. CSV Scenarios
    r_scen = client.get("/api/reports/csv/scenarios")
    assert r_scen.status_code == 200
    s_lines = r_scen.text.strip().split("\n")
    assert s_lines[0].startswith("Scenario Name,Maximum Flow")
    assert len(s_lines) == 6  # header + 5 scenarios

    # 4. PDF
    r_pdf = client.get("/api/reports/pdf")
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert r_pdf.content.startswith(b"%PDF-")
    assert len(r_pdf.content) > 5000  # valid multi-page PDF document
