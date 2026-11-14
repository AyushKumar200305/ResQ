"""Comprehensive DAA examiner verification: topologies, mathematical monotonicity, and full software checks."""

import importlib
from pathlib import Path
import pkgutil
import random

from streamlit.testing.v1 import AppTest

import resq
from resq import (
    DinicSolver,
    EvacuationNetwork,
    NodeType,
    build_evacuation_network,
    export_network_to_json,
    import_network_from_json,
    solve_max_flow_and_min_cut,
    solve_max_flow_dinic,
)
from resq.services import (
    build_min_cut_dataframe,
    build_road_flows_dataframe,
    build_routes_dataframe,
    build_scenario_lab_comparison_dataframe,
    evaluate_baseline_scenario,
    evaluate_road_closure_scenario,
    generate_pdf_report,
)

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


def _verify_all_axioms(net: EvacuationNetwork) -> tuple[int, int]:
    """Assert capacity bounds, flow conservation, source==sink, and max_flow==min_cut."""
    flow_net = build_evacuation_network(net)
    dinic_res = DinicSolver().solve(
        flow_net, domain_network=net, trace=True, reset=False, verify_invariants=True
    )
    flow_net.verify_flow_invariants()

    from resq import extract_min_cut

    min_cut = extract_min_cut(
        flow_net, domain_network=net, expected_max_flow=dinic_res.max_flow
    )

    for detail in dinic_res.road_flows.values():
        assert 0 <= detail.flow <= detail.original_capacity
        assert detail.remaining_capacity == detail.original_capacity - detail.flow

    source_total = sum(s.evacuated for s in dinic_res.source_evacuations.values())
    sink_total = sum(t.assigned_flow for t in dinic_res.shelter_intakes.values())
    assert source_total == dinic_res.max_flow
    assert sink_total == dinic_res.max_flow
    assert dinic_res.max_flow == min_cut.total_cut_capacity
    return dinic_res.max_flow, min_cut.total_cut_capacity


def _build_ten_examiner_networks() -> dict[str, tuple[EvacuationNetwork, int]]:
    """Construct all 10 required test networks with exact hand-calculated expected flows."""
    cases: dict[str, tuple[EvacuationNetwork, int]] = {}

    # 1. Very small manually verifiable graph
    g1 = EvacuationNetwork(network_id="g1-tiny", name="Tiny 3-Node")
    g1.add_node("A1", "Source", NodeType.AFFECTED_AREA, population=50)
    g1.add_node("J1", "Bridge", NodeType.JUNCTION)
    g1.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=40)
    g1.add_road("R1", "A1", "J1", 35)
    g1.add_road("R2", "J1", "S1", 60)
    cases["very_small"] = (g1, 35)

    # 2. Multiple-source graph
    g2 = EvacuationNetwork(network_id="g2-multi-src", name="Multiple Sources")
    g2.add_node("A1", "North", NodeType.AFFECTED_AREA, population=100)
    g2.add_node("A2", "Central", NodeType.AFFECTED_AREA, population=150)
    g2.add_node("A3", "South", NodeType.AFFECTED_AREA, population=80)
    g2.add_node("J1", "Hub", NodeType.JUNCTION)
    g2.add_node("S1", "Mega Shelter", NodeType.SHELTER, shelter_capacity=500)
    g2.add_road("R1", "A1", "J1", 90)
    g2.add_road("R2", "A2", "J1", 120)
    g2.add_road("R3", "A3", "J1", 80)
    g2.add_road("R4", "J1", "S1", 260)
    cases["multiple_source"] = (g2, 260)

    # 3. Multiple-shelter graph
    g3 = EvacuationNetwork(network_id="g3-multi-shl", name="Multiple Shelters")
    g3.add_node("A1", "Metro Core", NodeType.AFFECTED_AREA, population=600)
    g3.add_node("J1", "Split", NodeType.JUNCTION)
    g3.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=200)
    g3.add_node("S2", "Shelter 2", NodeType.SHELTER, shelter_capacity=250)
    g3.add_node("S3", "Shelter 3", NodeType.SHELTER, shelter_capacity=100)
    g3.add_road("R0", "A1", "J1", 700)
    g3.add_road("R1", "J1", "S1", 300)
    g3.add_road("R2", "J1", "S2", 300)
    g3.add_road("R3", "J1", "S3", 300)
    cases["multiple_shelter"] = (g3, 550)

    # 4. Disconnected graph
    g4 = EvacuationNetwork(network_id="g4-disconn", name="Disconnected")
    g4.add_node("A1", "Isolated Zone", NodeType.AFFECTED_AREA, population=300)
    g4.add_node("J1", "Dead End", NodeType.JUNCTION)
    g4.add_node("J2", "Orphan Hub", NodeType.JUNCTION)
    g4.add_node("S1", "Unreachable Shelter", NodeType.SHELTER, shelter_capacity=300)
    g4.add_road("R1", "A1", "J1", 250)
    g4.add_road("R2", "J2", "S1", 250)
    cases["disconnected"] = (g4, 0)

    # 5. Zero-capacity graph
    g5 = EvacuationNetwork(network_id="g5-zero", name="Zero Capacity")
    g5.add_node("A1", "Zone", NodeType.AFFECTED_AREA, population=100)
    g5.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=100)
    g5.add_road("R1", "A1", "S1", 0)
    cases["zero_capacity"] = (g5, 0)

    # 6. Graph with parallel edges
    g6 = EvacuationNetwork(network_id="g6-parallel", name="Parallel Corridors")
    g6.add_node("A1", "Zone", NodeType.AFFECTED_AREA, population=300)
    g6.add_node("S1", "Shelter", NodeType.SHELTER, shelter_capacity=300)
    g6.add_road("R_EXP", "A1", "S1", 120)
    g6.add_road("R_AUX", "A1", "S1", 80)
    g6.add_road("R_SVC", "A1", "S1", 50)
    cases["parallel_edges"] = (g6, 250)

    # 7. Graph with shared bottlenecks
    g7 = EvacuationNetwork(network_id="g7-shared", name="Shared Bottleneck Bridge")
    g7.add_node("A1", "West Zone", NodeType.AFFECTED_AREA, population=250)
    g7.add_node("A2", "East Zone", NodeType.AFFECTED_AREA, population=250)
    g7.add_node("J_IN", "Bridge Entry", NodeType.JUNCTION)
    g7.add_node("J_OUT", "Bridge Exit", NodeType.JUNCTION)
    g7.add_node("S1", "North Safe", NodeType.SHELTER, shelter_capacity=300)
    g7.add_node("S2", "South Safe", NodeType.SHELTER, shelter_capacity=300)
    g7.add_road("R1", "A1", "J_IN", 250)
    g7.add_road("R2", "A2", "J_IN", 250)
    g7.add_road("R_BRIDGE", "J_IN", "J_OUT", 180)
    g7.add_road("R3", "J_OUT", "S1", 250)
    g7.add_road("R4", "J_OUT", "S2", 250)
    cases["shared_bottleneck"] = (g7, 180)

    # 8. Graph requiring reverse-edge rerouting
    g8 = EvacuationNetwork(network_id="g8-reroute", name="Reverse Edge Reroute")
    g8.add_node("A", "Zone A", NodeType.AFFECTED_AREA, population=20)
    for j in ("J0", "J1", "J2", "J3", "J4", "J5"):
        g8.add_node(j, j, NodeType.JUNCTION)
    g8.add_node("S", "Shelter", NodeType.SHELTER, shelter_capacity=20)
    g8.add_road("R_A_J1", "A", "J1", 10)
    g8.add_road("R_J1_J4", "J1", "J4", 10)
    g8.add_road("R_J4_S", "J4", "S", 10)
    g8.add_road("R_A_J0", "A", "J0", 10)
    g8.add_road("R_J0_J2", "J0", "J2", 10)
    g8.add_road("R_J2_J4", "J2", "J4", 10)
    g8.add_road("R_J1_J3", "J1", "J3", 10)
    g8.add_road("R_J3_J5", "J3", "J5", 10)
    g8.add_road("R_J5_S", "J5", "S", 10)
    cases["reverse_rerouting"] = (g8, 20)

    # 9. Graph with a shelter-capacity bottleneck
    g9 = EvacuationNetwork(network_id="g9-shelter-cap", name="Shelter Bottleneck")
    g9.add_node("A1", "Zone", NodeType.AFFECTED_AREA, population=500)
    g9.add_node("S1", "Small Shelter", NodeType.SHELTER, shelter_capacity=150)
    g9.add_road("R1", "A1", "S1", 400)
    cases["shelter_bottleneck"] = (g9, 150)

    # 10. Graph with a road-closure scenario
    g10 = g6.copy(new_network_id="g10-closure", new_name="Road Closure Variant")
    g10.edit_road("R_EXP", capacity=0, is_active=False)
    cases["road_closure"] = (g10, 130)

    return cases


def test_examiner_ten_network_topologies_and_axioms() -> None:
    cases = _build_ten_examiner_networks()
    assert len(cases) == 10

    for name, (net, expected_flow) in cases.items():
        observed_flow, observed_cut = _verify_all_axioms(net)
        assert observed_flow == expected_flow, f"Failed flow on topology '{name}'"
        assert observed_cut == expected_flow, f"Failed min-cut on topology '{name}'"

    # Verify specific structural semantics on key topologies
    _, mc_par = solve_max_flow_and_min_cut(cases["parallel_edges"][0])
    assert {e.edge_id for e in mc_par.road_bottlenecks} == {"R_EXP", "R_AUX", "R_SVC"}

    _, mc_shared = solve_max_flow_and_min_cut(cases["shared_bottleneck"][0])
    assert [e.edge_id for e in mc_shared.road_bottlenecks] == ["R_BRIDGE"]

    res_rev = solve_max_flow_dinic(cases["reverse_rerouting"][0], trace=True)
    assert res_rev.trace is not None and res_rev.trace.reverse_rerouting_steps >= 1

    _, mc_shl = solve_max_flow_and_min_cut(cases["shelter_bottleneck"][0])
    assert [e.edge_id for e in mc_shl.shelter_capacity_cuts] == ["S1"]
    assert mc_shl.road_bottlenecks == ()


def test_mathematical_monotonicity_invariants() -> None:
    """Verify monotonicity across road closures, demand drops, shelter drops, and upgrades."""
    cases = _build_ten_examiner_networks()
    rng = random.Random(777)

    for case_name, (base_net, _) in cases.items():
        base_flow, _ = _verify_all_axioms(base_net)

        # 1. Closing any road cannot increase max flow
        for road_id in base_net.roads:
            closed = base_net.copy()
            closed.edit_road(road_id, capacity=0, is_active=False)
            new_flow, _ = _verify_all_axioms(closed)
            assert new_flow <= base_flow, (
                f"Closing {road_id} in {case_name} increased flow {base_flow} -> {new_flow}"
            )

        # 2. Reducing any source population cannot increase max flow
        for area in base_net.affected_areas:
            reduced_pop = base_net.copy()
            reduced_pop.edit_node(area.node_id, population=area.population // 2)
            new_flow, _ = _verify_all_axioms(reduced_pop)
            assert new_flow <= base_flow, (
                f"Reducing pop on {area.node_id} in {case_name} increased flow"
            )

        # 3. Reducing any shelter capacity cannot increase max flow
        for shelter in base_net.shelters:
            reduced_shl = base_net.copy()
            reduced_shl.edit_node(
                shelter.node_id, shelter_capacity=shelter.shelter_capacity // 2
            )
            new_flow, _ = _verify_all_axioms(reduced_shl)
            assert new_flow <= base_flow, (
                f"Reducing shelter {shelter.node_id} in {case_name} increased flow"
            )

        # 4. Increasing capacities (road, population, shelter) cannot reduce max flow
        upgraded = base_net.copy()
        for road_id, road in base_net.roads.items():
            if road.is_active:
                upgraded.edit_road(road_id, capacity=road.capacity + rng.randint(10, 100))
        for area in base_net.affected_areas:
            upgraded.edit_node(area.node_id, population=area.population + 50)
        for shelter in base_net.shelters:
            upgraded.edit_node(
                shelter.node_id, shelter_capacity=shelter.shelter_capacity + 50
            )
        up_flow, _ = _verify_all_axioms(upgraded)
        assert up_flow >= base_flow, (
            f"Increasing capacities in {case_name} reduced flow {base_flow} -> {up_flow}"
        )


def test_all_resq_submodules_import_without_missing_or_broken_modules() -> None:
    """Walk every package under resq/ and verify clean importability."""
    discovered = []
    for module_info in pkgutil.walk_packages(resq.__path__, prefix="resq."):
        imported = importlib.import_module(module_info.name)
        assert imported is not None
        discovered.append(module_info.name)
    assert len(discovered) >= 20


def test_end_to_end_streamlit_builder_forms_exports_and_state_persistence() -> None:
    """Exercise actual Network Builder forms, editing, deletion, analysis, and exports via AppTest."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    assert not at.exception

    # Navigate to Network Builder and clear to blank network
    at.button(key="cmd_build_net").click().run()
    assert not at.exception
    at.button(key="builder_clear_blank").click().run()
    assert not at.exception
    assert len(at.session_state["active_network"].nodes) == 0

    # Add Affected Area via Add Node form
    rev = at.session_state["network_revision"]
    at.selectbox(key=f"add_node_type_{rev}").set_value("affected_area").run()
    # Inside Add Node tab form: find text inputs & number inputs in form
    form_key = f"add_node_form_{rev}_affected_area"
    # Populate inputs inside form by matching label
    for ti in at.text_input:
        if ti.label == "Unique Node ID":
            ti.input("A1")
        elif ti.label == "Display Name":
            ti.input("Zone Alpha")
    for ni in at.number_input:
        if ni.label == "Affected Population (Evacuees)":
            ni.set_value(200)
    # Submit Add Node form button
    next(
        b for b in at.button if b.label == "Add Node" and form_key in b.key
    ).click().run()
    assert not at.exception
    assert "A1" in at.session_state["active_network"].nodes

    # Add Shelter via Add Node form
    rev = at.session_state["network_revision"]
    at.selectbox(key=f"add_node_type_{rev}").set_value("shelter").run()
    form_key_shl = f"add_node_form_{rev}_shelter"
    for ti in at.text_input:
        if ti.label == "Unique Node ID":
            ti.input("S1")
        elif ti.label == "Display Name":
            ti.input("Shelter One")
    for ni in at.number_input:
        if ni.label == "Shelter Capacity (Beds)":
            ni.set_value(250)
    next(
        b for b in at.button if b.label == "Add Node" and form_key_shl in b.key
    ).click().run()
    assert not at.exception
    assert "S1" in at.session_state["active_network"].nodes

    # Connect A1 -> S1 via Add Road form
    rev = at.session_state["network_revision"]
    road_form_key = f"add_road_form_{rev}"
    at.text_input(key=f"add_road_id_{rev}").input("R_MAIN")
    at.text_input(key=f"add_road_name_{rev}").input("Alpha Causeway")
    at.selectbox(key=f"add_road_src_{rev}").set_value("A1")
    at.selectbox(key=f"add_road_dst_{rev}").set_value("S1")
    at.number_input(key=f"add_road_cap_{rev}").set_value(180)
    next(
        b for b in at.button if b.label == "Connect Road" and road_form_key in b.key
    ).click().run()
    assert not at.exception
    assert "R_MAIN" in at.session_state["active_network"].roads

    # Edit A1 population via Edit Node form (200 -> 300)
    rev = at.session_state["network_revision"]
    at.selectbox(key=f"edit_node_sel_{rev}").set_value("A1").run()
    edit_node_form_key = f"edit_node_form_{rev}_A1_affected_area"
    at.number_input(key=f"edit_node_pop_{rev}_A1").set_value(300)
    next(
        b for b in at.button if b.label == "Save Node Changes" and edit_node_form_key in b.key
    ).click().run()
    assert not at.exception
    assert at.session_state["active_network"].get_node("A1").population == 300

    # Edit R_MAIN capacity via Edit Road form (180 -> 210)
    rev = at.session_state["network_revision"]
    at.selectbox(key=f"edit_road_sel_{rev}").set_value("R_MAIN").run()
    edit_road_form_key = f"edit_road_form_{rev}_R_MAIN"
    at.number_input(key=f"edit_road_cap_{rev}_R_MAIN").set_value(210)
    next(
        b for b in at.button if b.label == "Save Road Changes" and edit_road_form_key in b.key
    ).click().run()
    assert not at.exception
    assert at.session_state["active_network"].get_road("R_MAIN").capacity == 210

    # Run Analysis from Builder and verify session_state persists across pages
    at.button(key="builder_run").click().run()
    assert not at.exception
    bundle = at.session_state["analysis_bundle"]
    assert bundle is not None
    assert bundle.dinic_result.max_flow == 210
    assert bundle.min_cut.total_cut_capacity == 210

    # Navigate to Overview, Flow Analysis, Bottleneck Analysis, Reports — state persists!
    for page in ("Overview", "Flow Analysis", "Bottleneck Analysis", "Reports"):
        at.sidebar.radio(key="nav_radio").set_value(page).run()
        assert not at.exception
        assert at.session_state["analysis_bundle"].dinic_result.max_flow == 210

    # Verify JSON, CSV, and PDF exports on the constructed network
    net = at.session_state["active_network"]
    restored = import_network_from_json(export_network_to_json(net))
    assert restored.to_dict() == net.to_dict()
    assert not build_road_flows_dataframe(bundle).empty
    assert not build_min_cut_dataframe(bundle).empty
    assert not build_routes_dataframe(bundle).empty

    s1 = evaluate_baseline_scenario(net)
    s2 = evaluate_road_closure_scenario(net, s1, road_id="R_MAIN")
    scn_df = build_scenario_lab_comparison_dataframe([s1, s2])
    assert scn_df["Maximum Flow"].tolist() == [210, 0]

    pdf_bytes = generate_pdf_report(bundle, scenario_evaluations=[s1, s2])
    assert pdf_bytes.startswith(b"%PDF-")

    # Return to Network Builder and test Delete Road & Delete Node
    at.button(key="cmd_build_net").click().run()
    assert not at.exception
    rev = at.session_state["network_revision"]
    at.button(key=f"del_road_btn_{rev}_R_MAIN").click().run()
    assert not at.exception
    assert "R_MAIN" not in at.session_state["active_network"].roads
    assert at.session_state["analysis_bundle"] is None  # invalidated on deletion

    rev = at.session_state["network_revision"]
    at.button(key=f"del_node_btn_{rev}_A1").click().run()
    assert not at.exception
    assert "A1" not in at.session_state["active_network"].nodes
