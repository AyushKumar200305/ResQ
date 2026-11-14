"""Page 6: Scenario Lab (5-Scenario What-If Analyzer & Saved Snapshot Comparison)."""

import pandas as pd
import streamlit as st

from resq.domain.exceptions import ResQError
from resq.services.evacuation_simulator import run_full_evacuation_analysis
from resq.services.presets import list_presets, load_preset_network
from resq.services.scenario_lab import (
    ScenarioEvaluation,
    build_scenario_lab_comparison_dataframe,
    evaluate_baseline_scenario,
    evaluate_increased_shelter_scenario,
    evaluate_multiple_road_failures_scenario,
    evaluate_reduced_shelter_scenario,
    evaluate_road_closure_scenario,
)
from resq.ui.components import (
    KpiMetric,
    build_network_figure,
    build_scenario_comparison_chart,
    build_whatif_comparison_chart,
    build_whatif_delta_chart,
    render_kpi_grid,
)
from resq.ui.state import (
    SavedScenarioRecord,
    get_active_network,
    invalidate_analysis,
    save_current_scenario,
    set_flash,
)
from resq.ui.theme import render_chart, render_table


def _ensure_baseline(suite: dict[str, ScenarioEvaluation], base_net) -> ScenarioEvaluation:
    if "scenario_1_baseline" not in suite:
        suite["scenario_1_baseline"] = evaluate_baseline_scenario(base_net)
    return suite["scenario_1_baseline"]


def _render_what_if_tab() -> None:
    """Render the 5 structured what-if scenarios, comparison table, charts, and observations."""
    net = get_active_network()
    report = net.validate()
    if not report.is_valid:
        st.error(
            "Fix network validation errors before running Scenario Lab comparisons: "
            + " | ".join(report.errors)
        )
        return

    rev = st.session_state.get("network_revision", 1)
    suite: dict[str, ScenarioEvaluation] = st.session_state.setdefault(
        "scenario_lab_suite", {}
    )

    st.caption(
        "Evaluate how road failures and shelter capacity changes affect maximum evacuation flow "
        "and minimum-cut bottlenecks. All scenarios run on independent copies — your original "
        "network is always preserved."
    )

    road_ids = list(net.roads.keys())
    shelter_nodes = net.shelters
    shelter_ids = [s.node_id for s in shelter_nodes]

    top_c1, top_c2 = st.columns([1.4, 2.2])
    with top_c1:
        if st.button(
            "Evaluate All 5 Scenarios (Quick Suite)",
            type="primary",
            width="stretch",
            key=f"lab_run_all5_{rev}",
        ):
            try:
                with st.spinner("Evaluating Scenarios 1 through 5 on independent copies..."):
                    base_ev = evaluate_baseline_scenario(net)
                    suite.clear()
                    suite[base_ev.scenario_key] = base_ev

                    if road_ids:
                        cut_roads = [
                            e.edge_id for e in base_ev.bundle.min_cut.road_bottlenecks
                        ]
                        primary_road = cut_roads[0] if cut_roads else road_ids[0]
                        s2 = evaluate_road_closure_scenario(
                            net, base_ev, road_id=primary_road
                        )
                        suite[s2.scenario_key] = s2

                        multi_pick = (
                            cut_roads[:2]
                            if len(cut_roads) >= 2
                            else road_ids[: min(2, len(road_ids))]
                        )
                        s5 = evaluate_multiple_road_failures_scenario(
                            net, base_ev, road_ids=multi_pick
                        )
                        suite[s5.scenario_key] = s5

                    if shelter_nodes:
                        target_shl_s3 = shelter_nodes[0]
                        reduced_cap = max(0, target_shl_s3.shelter_capacity // 3)
                        s3 = evaluate_reduced_shelter_scenario(
                            net,
                            base_ev,
                            shelter_id=target_shl_s3.node_id,
                            new_capacity=reduced_cap,
                        )
                        suite[s3.scenario_key] = s3

                        cut_shl_ids = [
                            e.edge_id for e in base_ev.bundle.min_cut.shelter_capacity_cuts
                        ]
                        target_shl_s4 = (
                            cut_shl_ids[0] if cut_shl_ids else shelter_nodes[0].node_id
                        )
                        s4 = evaluate_increased_shelter_scenario(
                            net,
                            base_ev,
                            shelter_id=target_shl_s4,
                            added_capacity=500,
                        )
                        suite[s4.scenario_key] = s4
            except ResQError as exc:
                st.error(str(exc))
            else:
                set_flash("success", "Evaluated Scenarios 1–5 against unmodified baseline.")
                st.rerun()

    with top_c2:
        if st.button("Clear Scenario Lab Results", key=f"lab_clear_{rev}"):
            suite.clear()
            st.rerun()

    # Individual Scenario Configuration Panels (Scenarios 1 - 5)
    with st.expander("Configure & Run Individual What-If Scenarios (1–5)", expanded=True):
        s_tab1, s_tab2, s_tab3, s_tab4, s_tab5 = st.tabs(
            [
                "1. Normal Conditions",
                "2. Road Closure",
                "3. Reduced Shelter",
                "4. Increased Shelter",
                "5. Multiple Road Failures",
            ]
        )

        with s_tab1:
            st.write("Run Dinic Maximum Flow and Minimum Cut on the original unmodified network.")
            if st.button("Run Scenario 1 (Baseline)", key=f"lab_run_s1_{rev}"):
                with st.spinner("Evaluating baseline network..."):
                    base_ev = evaluate_baseline_scenario(net)
                    suite[base_ev.scenario_key] = base_ev
                set_flash("success", "Scenario 1 (Baseline) saved.")
                st.rerun()

        with s_tab2:
            if not road_ids:
                st.info("No roads available to close.")
            else:
                sel_r = st.selectbox(
                    "Select Road to Close (Capacity = 0)",
                    options=road_ids,
                    format_func=lambda rid: (
                        f"{rid}: {net.roads[rid].source_id} -> {net.roads[rid].target_id} "
                        f"(cap {net.roads[rid].capacity:,})"
                    ),
                    key=f"lab_s2_road_{rev}",
                )
                if st.button("Run Scenario 2 (Road Closure)", key=f"lab_run_s2_{rev}"):
                    try:
                        with st.spinner(f"Simulating closure of {sel_r}..."):
                            base_ev = _ensure_baseline(suite, net)
                            ev2 = evaluate_road_closure_scenario(net, base_ev, road_id=sel_r)
                            suite[ev2.scenario_key] = ev2
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        set_flash("success", f"Evaluated Scenario 2 (Closed {sel_r}).")
                        st.rerun()

        with s_tab3:
            if not shelter_ids:
                st.info("No shelters available.")
            else:
                sel_s3 = st.selectbox(
                    "Select Shelter to Reduce",
                    options=shelter_ids,
                    format_func=lambda sid: (
                        f"{sid} — {net.nodes[sid].name} (current cap {net.nodes[sid].shelter_capacity:,})"
                    ),
                    key=f"lab_s3_shl_{rev}",
                )
                cur_cap3 = net.get_node(sel_s3).shelter_capacity
                if cur_cap3 == 0:
                    st.info(
                        f"Shelter '{sel_s3}' already has capacity 0 and cannot be reduced further."
                    )
                    new_cap3 = 0
                else:
                    new_cap3 = int(
                        st.slider(
                            "Reduced Shelter Capacity",
                            min_value=0,
                            max_value=cur_cap3,
                            value=cur_cap3 // 3,
                            step=max(1, min(50, cur_cap3)),
                            key=f"lab_s3_cap_{rev}_{sel_s3}",
                        )
                    )
                if st.button(
                    "Run Scenario 3 (Reduced Shelter)",
                    disabled=(cur_cap3 == 0),
                    key=f"lab_run_s3_{rev}",
                ):
                    try:
                        with st.spinner(f"Evaluating reduced capacity for {sel_s3}..."):
                            base_ev = _ensure_baseline(suite, net)
                            ev3 = evaluate_reduced_shelter_scenario(
                                net, base_ev, shelter_id=sel_s3, new_capacity=new_cap3
                            )
                            suite[ev3.scenario_key] = ev3
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        set_flash("success", f"Evaluated Scenario 3 ({sel_s3} -> {new_cap3:,}).")
                        st.rerun()

        with s_tab4:
            if not shelter_ids:
                st.info("No shelters available.")
            else:
                sel_s4 = st.selectbox(
                    "Select Shelter to Expand",
                    options=shelter_ids,
                    format_func=lambda sid: (
                        f"{sid} — {net.nodes[sid].name} (current cap {net.nodes[sid].shelter_capacity:,})"
                    ),
                    key=f"lab_s4_shl_{rev}",
                )
                add_cap4 = int(
                    st.number_input(
                        "Additional Shelter Capacity (+Beds)",
                        min_value=50,
                        max_value=5000,
                        value=500,
                        step=50,
                        key=f"lab_s4_add_{rev}_{sel_s4}",
                    )
                )
                if st.button("Run Scenario 4 (Increased Shelter)", key=f"lab_run_s4_{rev}"):
                    try:
                        with st.spinner(f"Evaluating expansion of {sel_s4}..."):
                            base_ev = _ensure_baseline(suite, net)
                            ev4 = evaluate_increased_shelter_scenario(
                                net, base_ev, shelter_id=sel_s4, added_capacity=add_cap4
                            )
                            suite[ev4.scenario_key] = ev4
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        set_flash("success", f"Evaluated Scenario 4 ({sel_s4} +{add_cap4:,}).")
                        st.rerun()

        with s_tab5:
            if not road_ids:
                st.info("No roads available.")
            else:
                default_multi = road_ids[: min(2, len(road_ids))]
                sel_r5 = st.multiselect(
                    "Select Multiple Roads to Close Simultaneously",
                    options=road_ids,
                    default=default_multi,
                    format_func=lambda rid: (
                        f"{rid}: {net.roads[rid].source_id} -> {net.roads[rid].target_id}"
                    ),
                    key=f"lab_s5_roads_{rev}",
                )
                if st.button("Run Scenario 5 (Multiple Failures)", key=f"lab_run_s5_{rev}"):
                    try:
                        with st.spinner("Evaluating simultaneous multi-road failure..."):
                            base_ev = _ensure_baseline(suite, net)
                            ev5 = evaluate_multiple_road_failures_scenario(
                                net, base_ev, road_ids=sel_r5
                            )
                            suite[ev5.scenario_key] = ev5
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        set_flash(
                            "success",
                            f"Evaluated Scenario 5 ({len(sel_r5)} roads closed).",
                        )
                        st.rerun()

    if not suite:
        st.info(
            "Click **Evaluate All 5 Scenarios (Quick Suite)** or run any individual scenario above "
            "to generate the comparative table, charts, and rule-based observations."
        )
        return

    ordered_keys = [
        "scenario_1_baseline",
        "scenario_2_road_closure",
        "scenario_3_reduced_shelter",
        "scenario_4_increased_shelter",
        "scenario_5_multi_failure",
    ]
    evaluations = [suite[k] for k in ordered_keys if k in suite]

    st.markdown(
        '<div class="resq-section-title">Scenario Comparison Matrix</div>',
        unsafe_allow_html=True,
    )
    comp_df = build_scenario_lab_comparison_dataframe(evaluations)
    render_table(comp_df)

    ch1, ch2 = st.columns(2, gap="medium")
    with ch1:
        render_chart(build_whatif_comparison_chart(evaluations), key="lab_whatif_bar")
    with ch2:
        render_chart(build_whatif_delta_chart(evaluations), key="lab_whatif_delta")

    st.markdown(
        '<div class="resq-section-title">Rule-Based Observations & Bottleneck Impact</div>',
        unsafe_allow_html=True,
    )
    for ev in evaluations:
        with st.container(border=True):
            st.markdown(f"**{ev.scenario_name}** — _{ev.description}_")
            for obs in ev.observations:
                st.markdown(f"- {obs}")

    insp_key = st.selectbox(
        "Inspect Network Topology & Bottlenecks for Scenario",
        options=[ev.scenario_key for ev in evaluations],
        format_func=lambda k: suite[k].scenario_name,
        key=f"lab_inspect_sel_{rev}",
    )
    insp_ev = suite[insp_key]
    d = insp_ev.bundle.dinic_result
    mc = insp_ev.bundle.min_cut
    render_kpi_grid(
        [
            KpiMetric("Maximum Flow", f"{d.max_flow:,}", "Dinic optimal", "info"),
            KpiMetric(
                "People Unallocated",
                f"{d.unmet_demand:,}",
                f"{d.evacuation_rate * 100:.1f}% evacuated",
                "safe" if d.unmet_demand == 0 else "crit",
            ),
            KpiMetric(
                "Minimum Cut Capacity",
                f"{mc.total_cut_capacity:,}",
                f"{len(mc.road_bottlenecks)} road bottlenecks",
                "warn" if mc.road_bottlenecks else "safe",
            ),
            KpiMetric(
                "Change from Baseline",
                f"{insp_ev.baseline_delta:+,}",
                f"{insp_ev.baseline_delta_pct:+.1f}% vs. Scenario 1",
                "safe"
                if insp_ev.baseline_delta > 0
                else ("crit" if insp_ev.baseline_delta < 0 else "neutral"),
            ),
        ]
    )
    render_chart(
        build_network_figure(
            insp_ev.network, bundle=insp_ev.bundle, mode="flow", height=440
        ),
        key=f"lab_insp_plot_{rev}_{insp_key}",
    )


def _render_saved_snapshots_tab() -> None:
    """Render user-saved scenario snapshots and built-in preset comparison."""
    saved_map: dict[str, SavedScenarioRecord] = st.session_state["saved_scenarios"]

    c1, c2, c3 = st.columns([2.0, 1.2, 1.4], vertical_alignment="bottom")
    with c1:
        custom_name = st.text_input(
            "Snapshot Label for Current Workspace",
            placeholder="e.g., Baseline Before Mitigation",
            key="scn_save_label",
        )
    with c2:
        if st.button(
            "Save Current Scenario",
            type="primary",
            width="stretch",
            key="scn_save_btn",
        ):
            ok, msg = save_current_scenario(custom_name)
            set_flash("success" if ok else "error", msg)
            st.rerun()
    with c3:
        if st.button(
            "Load Built-in Presets into Lab",
            width="stretch",
            key="scn_seed_presets",
        ):
            with st.spinner("Evaluating built-in disaster presets for comparison..."):
                for p in list_presets():
                    if p.key not in saved_map:
                        p_net = load_preset_network(p.key)
                        p_bundle = run_full_evacuation_analysis(
                            p_net, trace=False, wave_hours=8, upgrade_delta=100
                        )
                        saved_map[p.key] = SavedScenarioRecord(
                            scenario_id=p.key,
                            label=p.title,
                            saved_at="Preset",
                            network=p_net,
                            bundle=p_bundle,
                        )
            set_flash("success", "Loaded built-in presets into Scenario Lab.")
            st.rerun()

    if not saved_map:
        st.info(
            "No snapshots saved yet. Save the current workspace above or click "
            "**Load Built-in Presets into Lab**."
        )
        return

    for rec in saved_map.values():
        if rec.bundle is None and rec.network.validate().is_valid:
            rec.bundle = run_full_evacuation_analysis(
                rec.network, trace=False, wave_hours=8, upgrade_delta=100
            )

    all_ids = list(saved_map.keys())
    existing_sel = st.session_state.get("scn_compare_multi")
    if isinstance(existing_sel, list):
        filtered_sel = [sid for sid in existing_sel if sid in saved_map]
        if len(filtered_sel) != len(existing_sel):
            st.session_state["scn_compare_multi"] = filtered_sel
    selected_ids = st.multiselect(
        "Select Saved Scenarios to Compare",
        options=all_ids,
        default=all_ids[: min(4, len(all_ids))],
        format_func=lambda sid: saved_map[sid].label,
        key="scn_compare_multi",
    )

    if selected_ids:
        records = [saved_map[sid] for sid in selected_ids]
        render_chart(build_scenario_comparison_chart(records), key="scn_comp_chart")

        matrix_rows = []
        for rec in records:
            b = rec.bundle
            if b is None:
                matrix_rows.append(
                    {
                        "Scenario": rec.label,
                        "Saved": rec.saved_at,
                        "Population": rec.network.total_population,
                        "Shelter Cap": rec.network.total_shelter_capacity,
                        "Max Flow": "Invalid Graph",
                        "Unallocated": "-",
                        "Completion (%)": "-",
                        "Road Cuts": "-",
                        "Shelter Cuts": "-",
                    }
                )
            else:
                d = b.dinic_result
                mc = b.min_cut
                matrix_rows.append(
                    {
                        "Scenario": rec.label,
                        "Saved": rec.saved_at,
                        "Population": d.total_population,
                        "Shelter Cap": d.total_shelter_capacity,
                        "Max Flow": d.max_flow,
                        "Unallocated": d.unmet_demand,
                        "Completion (%)": round(d.evacuation_rate * 100.0, 1),
                        "Road Cuts": ", ".join(e.edge_id for e in mc.road_bottlenecks)
                        or "None",
                        "Shelter Cuts": ", ".join(
                            e.edge_id for e in mc.shelter_capacity_cuts
                        )
                        or "None",
                    }
                )
        render_table(pd.DataFrame(matrix_rows))

    st.markdown(
        '<div class="resq-section-title">Manage Stored Snapshots</div>',
        unsafe_allow_html=True,
    )
    m_col1, m_col2, m_col3 = st.columns([2.0, 1.0, 1.0], vertical_alignment="bottom")
    with m_col1:
        target_sid = st.selectbox(
            "Target Snapshot",
            options=all_ids,
            format_func=lambda sid: f"{saved_map[sid].label} ({saved_map[sid].saved_at})",
            key="scn_manage_sel",
        )
    with m_col2:
        if st.button("Activate in Workspace", width="stretch", key="scn_activate_btn"):
            chosen = saved_map[target_sid]
            st.session_state["active_network"] = chosen.network.copy()
            invalidate_analysis()
            if chosen.bundle is not None:
                st.session_state["analysis_bundle"] = chosen.bundle
                st.session_state["analysis_timestamp"] = chosen.saved_at
            set_flash("success", f"Loaded '{chosen.label}' into active workspace.")
            st.rerun()
    with m_col3:
        if st.button("Delete Snapshot", width="stretch", key="scn_delete_btn"):
            removed = saved_map.pop(target_sid)
            set_flash("warning", f"Removed scenario '{removed.label}' from Scenario Lab.")
            st.rerun()


def render_scenario_lab_page() -> None:
    """Render the Scenario Lab 5-Scenario What-If Analyzer and Saved Snapshots."""
    tab_whatif, tab_snapshots = st.tabs(
        ["What-If Scenario Suite (1–5)", "Saved Snapshots & Presets"]
    )
    with tab_whatif:
        _render_what_if_tab()
    with tab_snapshots:
        _render_saved_snapshots_tab()
