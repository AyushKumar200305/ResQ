"""End-to-end Streamlit AppTest verification across all ResQ pages and main controls."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from resq.ui.state import PAGES

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


def _assert_no_errors(at: AppTest) -> None:
    assert not at.exception, f"Uncaught Streamlit exception: {at.exception}"


def test_app_boots_with_demo_network_and_no_misleading_preanalysis() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    _assert_no_errors(at)

    assert at.session_state["active_page"] == "Overview"
    assert at.session_state["active_network"].network_id == "metro-flood-baseline"
    # No analysis executed yet -> bundle must be None (no fabricated results)
    assert at.session_state["analysis_bundle"] is None
    assert any("Pending Analysis" in md.value or "Not analyzed" in md.value for md in at.markdown)


def test_main_controls_and_navigation_across_all_nine_pages() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    _assert_no_errors(at)

    # 1. Run Analysis from command bar
    at.button(key="cmd_run_analysis").click().run()
    _assert_no_errors(at)
    assert at.session_state["analysis_bundle"] is not None
    assert at.session_state["analysis_bundle"].dinic_result.max_flow == 2250

    # 2. Save Scenario from command bar
    at.button(key="cmd_save_scenario").click().run()
    _assert_no_errors(at)
    assert len(at.session_state["saved_scenarios"]) == 1

    # 3. Navigate across all 9 pages via sidebar radio
    for page in PAGES:
        at.sidebar.radio(key="nav_radio").set_value(page).run()
        _assert_no_errors(at)
        assert at.session_state["active_page"] == page

    # 4. Build Network button navigates to Network Builder
    at.button(key="cmd_build_net").click().run()
    _assert_no_errors(at)
    assert at.session_state["active_page"] == "Network Builder"

    # 5. Export Results button navigates to Reports
    at.button(key="cmd_export_results").click().run()
    _assert_no_errors(at)
    assert at.session_state["active_page"] == "Reports"

    # 6. Reset clears analysis_bundle cleanly without erasing network
    at.button(key="cmd_reset").click().run()
    _assert_no_errors(at)
    assert at.session_state["analysis_bundle"] is None

    # 7. Load Demo Network restores preset cleanly
    at.button(key="cmd_load_demo").click().run()
    _assert_no_errors(at)
    assert at.session_state["active_network"].network_id == "metro-flood-baseline"
    assert at.session_state["analysis_bundle"] is None


def test_network_builder_clear_and_validation_flow() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    _assert_no_errors(at)

    at.button(key="cmd_run_analysis").click().run()
    assert at.session_state["analysis_bundle"] is not None

    # Jump to Network Builder and clear to blank graph
    at.button(key="cmd_build_net").click().run()
    _assert_no_errors(at)
    at.button(key="builder_clear_blank").click().run()
    _assert_no_errors(at)

    assert len(at.session_state["active_network"].nodes) == 0
    assert at.session_state["analysis_bundle"] is None

    # Attempting to run analysis on empty network shows friendly error, not exception
    at.button(key="builder_run").click().run()
    _assert_no_errors(at)
    assert at.session_state["analysis_bundle"] is None
    assert len(at.error) > 0


def test_algorithm_comparison_greedy_trap_and_live_simulation_flows() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    _assert_no_errors(at)

    # Navigate to Algorithm Comparison and run built-in Greedy Trap + Scalability Benchmark
    at.sidebar.radio(key="nav_radio").set_value("Algorithm Comparison").run()
    _assert_no_errors(at)
    at.button(key="cmp_load_trap").click().run()
    _assert_no_errors(at)

    comp = at.session_state["comparison_result"]
    assert comp is not None
    assert comp.dinic_max_flow == 2000
    assert comp.greedy_flow == 1000
    assert comp.flow_difference == 1000

    at.button(key="bench_run_btn").click().run()
    _assert_no_errors(at)
    assert at.session_state["scalability_report"] is not None
    assert len(at.session_state["scalability_report"].rows) == 5

    # Navigate to Scenario Lab and test both 5-Scenario What-If Suite & Preset Archive
    at.sidebar.radio(key="nav_radio").set_value("Scenario Lab").run()
    _assert_no_errors(at)
    rev = at.session_state["network_revision"]
    at.button(key=f"lab_run_all5_{rev}").click().run()
    _assert_no_errors(at)
    assert len(at.session_state["scenario_lab_suite"]) == 5

    at.button(key="scn_seed_presets").click().run()
    _assert_no_errors(at)
    assert len(at.session_state["saved_scenarios"]) == 4

    # Navigate to Live Simulation and exercise Step-by-Step Playback controls
    at.sidebar.radio(key="nav_radio").set_value("Live Simulation").run()
    _assert_no_errors(at)

    # Ensure active network is analyzed first, then test Start -> Pause -> Next -> Prev -> Reset
    at.button(key="cmd_run_analysis").click().run()
    _assert_no_errors(at)
    assert at.session_state["playback_step"] == 0
    assert at.session_state["playback_playing"] is False

    at.button(key="pb_start").click().run()
    _assert_no_errors(at)
    assert at.session_state["playback_playing"] is True
    assert at.session_state["playback_step"] == 1

    at.button(key="pb_pause").click().run()
    _assert_no_errors(at)
    assert at.session_state["playback_playing"] is False
    assert at.session_state["playback_step"] == 1

    at.button(key="pb_next").click().run()
    _assert_no_errors(at)
    assert at.session_state["playback_step"] == 2

    at.button(key="pb_prev").click().run()
    _assert_no_errors(at)
    assert at.session_state["playback_step"] == 1

    at.button(key="pb_reset").click().run()
    _assert_no_errors(at)
    assert at.session_state["playback_step"] == 0
    assert at.session_state["playback_playing"] is False


def test_shortest_path_dijkstra_page_workflow() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    _assert_no_errors(at)

    at.sidebar.radio(key="nav_radio").set_value("Shortest Path (Dijkstra)").run()
    _assert_no_errors(at)
    assert at.session_state["dijkstra_result"] is None

    # Calculate Dijkstra Shortest Path on selected (A1 -> S1)
    at.button(key="sp_calc_btn").click().run()
    _assert_no_errors(at)
    res = at.session_state["dijkstra_result"]
    assert res is not None
    assert res.reachable is True
    assert res.shortest_route is not None
    assert res.shortest_route.total_distance == pytest.approx(7.2)
    assert res.alternative_route is not None
    assert res.alternative_route.total_distance == pytest.approx(10.0)

    # Run Max-Flow & Compare from within the page
    at.button(key="sp_compare_dinic_btn").click().run()
    _assert_no_errors(at)
    assert at.session_state["analysis_bundle"] is not None
    assert at.session_state["analysis_bundle"].dinic_result.max_flow == 2250


def test_scenario_lab_zero_shelter_guard_snapshot_delete_and_reports_exports() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    _assert_no_errors(at)

    # Modify a shelter to capacity 0 in builder (tests Scenario 3 zero-range slider guard!)
    net = at.session_state["active_network"].copy()
    net.edit_node("S3", shelter_capacity=0)
    at.session_state["active_network"] = net
    at.session_state["network_revision"] += 1

    at.sidebar.radio(key="nav_radio").set_value("Scenario Lab").run()
    _assert_no_errors(at)

    # Select S3 in Scenario 3 dropdown -> must NOT throw StreamlitAPIException
    rev = at.session_state["network_revision"]
    at.selectbox(key=f"lab_s3_shl_{rev}").set_value("S3").run()
    _assert_no_errors(at)

    # Seed presets & delete one snapshot cleanly
    at.button(key="scn_seed_presets").click().run()
    _assert_no_errors(at)
    assert len(at.session_state["saved_scenarios"]) == 4
    at.button(key="scn_delete_btn").click().run()
    _assert_no_errors(at)
    assert len(at.session_state["saved_scenarios"]) == 3

    # Run primary analysis and inspect Bottleneck, Flow Analysis, Reports, and About ResQ pages
    at.button(key="cmd_run_analysis").click().run()
    _assert_no_errors(at)
    for page in ("Flow Analysis", "Bottleneck Analysis", "About ResQ", "Reports"):
        at.sidebar.radio(key="nav_radio").set_value(page).run()
        _assert_no_errors(at)

    # Verify Reports page has all 8 export download widgets cleanly instantiated
    assert len(at.get("download_button")) == 8

    # Verify Overview Analytics Dashboard (6 charts) & Reports (PDF + CSVs) render cleanly
    at.sidebar.radio(key="nav_radio").set_value("Overview").run()
    _assert_no_errors(at)
    at.sidebar.radio(key="nav_radio").set_value("Reports").run()
    _assert_no_errors(at)
