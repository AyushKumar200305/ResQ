"""Page 1: Overview Dashboard."""

import pandas as pd
import streamlit as st

from resq.domain.enums import GreedyRule
from resq.services.comparator import compare_dinic_vs_greedy
from resq.services.report_generator import (
    build_min_cut_dataframe,
    build_shelters_dataframe,
    build_sources_dataframe,
)
from resq.ui.components import (
    KpiMetric,
    build_bottleneck_road_capacities_chart,
    build_dinic_vs_greedy_summary_chart,
    build_evacuated_vs_remaining_chart,
    build_max_flow_by_scenario_chart,
    build_network_figure,
    build_road_utilization_chart,
    build_shelter_intake_chart,
    build_shelter_utilization_chart,
    build_source_evacuation_chart,
    render_kpi_grid,
    render_pending_analysis_guard,
)
from resq.ui.state import (
    get_active_network,
    get_analysis_bundle,
    get_comparison_result,
)
from resq.ui.theme import render_chart, render_table


def render_overview_page() -> None:
    """Render the emergency-management Overview Dashboard."""
    net = get_active_network()
    bundle = get_analysis_bundle()
    report = net.validate()

    total_pop = net.total_population
    total_shelter = net.total_shelter_capacity
    num_sources = len(net.affected_areas)
    num_shelters = len(net.shelters)

    if bundle is not None:
        d = bundle.dinic_result
        mc = bundle.min_cut
        crit_count = len(mc.road_bottlenecks) + len(mc.shelter_capacity_cuts)
        completion_pct = d.evacuation_rate * 100.0

        flow_val_str = f"{d.max_flow:,}"
        flow_sub = f"Dinic runtime {d.execution_time_ms:.3f} ms · {d.bfs_phases} BFS phases"
        flow_tone = "safe" if d.unmet_demand == 0 else "info"

        unmet_str = f"{d.unmet_demand:,}"
        unmet_sub = "All evacuees routed" if d.unmet_demand == 0 else "Capacity-constrained"
        unmet_tone = "safe" if d.unmet_demand == 0 else "crit"

        pct_str = f"{completion_pct:.1f}%"
        pct_sub = f"{d.max_flow:,} of {total_pop:,} evacuees"
        pct_tone = "safe" if completion_pct >= 99.9 else ("warn" if completion_pct >= 70.0 else "crit")

        bottleneck_str = f"{crit_count}"
        bottleneck_sub = (
            f"{len(mc.road_bottlenecks)} roads · {len(mc.shelter_capacity_cuts)} shelters"
        )
        bottleneck_tone = "safe" if crit_count == 0 else "crit"
    else:
        flow_val_str = "Not analyzed"
        flow_sub = "Run Analysis to compute max flow"
        flow_tone = "neutral"

        unmet_str = "Not analyzed"
        unmet_sub = "Pending Dinic evaluation"
        unmet_tone = "neutral"

        pct_str = "Not analyzed"
        pct_sub = "Pending Dinic evaluation"
        pct_tone = "neutral"

        bottleneck_str = "Not analyzed"
        bottleneck_sub = "Pending Minimum Cut extraction"
        bottleneck_tone = "neutral"

    # Row 1: Capacity & Evacuation Throughput (8 required Overview metrics)
    render_kpi_grid(
        [
            KpiMetric(
                label="Affected Population",
                value=f"{total_pop:,}",
                subtext="Total demand across sources",
                tone="warn" if total_pop > 0 else "neutral",
            ),
            KpiMetric(
                label="Available Shelter Capacity",
                value=f"{total_shelter:,}",
                subtext=(
                    "Sufficient aggregate beds"
                    if total_shelter >= total_pop
                    else f"Deficit of {total_pop - total_shelter:,} beds"
                ),
                tone="safe" if total_shelter >= total_pop else "crit",
            ),
            KpiMetric(
                label="Maximum Evacuation Flow",
                value=flow_val_str,
                subtext=flow_sub,
                tone=flow_tone,
            ),
            KpiMetric(
                label="People Remaining Unallocated",
                value=unmet_str,
                subtext=unmet_sub,
                tone=unmet_tone,
            ),
        ]
    )
    render_kpi_grid(
        [
            KpiMetric(
                label="Evacuation Completion",
                value=pct_str,
                subtext=pct_sub,
                tone=pct_tone,
            ),
            KpiMetric(
                label="Critical Bottlenecks",
                value=bottleneck_str,
                subtext=bottleneck_sub,
                tone=bottleneck_tone,
            ),
            KpiMetric(
                label="Affected Areas (Sources)",
                value=f"{num_sources}",
                subtext=f"{len(net.junctions)} intermediate junctions",
                tone="info" if num_sources > 0 else "crit",
            ),
            KpiMetric(
                label="Available Shelters",
                value=f"{num_shelters}",
                subtext=f"{len(net.roads)} directed road corridors",
                tone="safe" if num_shelters > 0 else "crit",
            ),
        ]
    )

    if not report.is_valid:
        st.error("Network configuration errors: " + " | ".join(report.errors))
    elif report.warnings:
        st.warning("Operational advisories: " + " | ".join(report.warnings))

    if bundle is None and report.is_valid:
        render_pending_analysis_guard("Overview telemetry", "overview")

    # Network Topology / Flow Visualization
    st.markdown('<div class="resq-section-title">Evacuation Network Schematic</div>', unsafe_allow_html=True)
    col_opt1, col_opt2 = st.columns([3, 1])
    with col_opt2:
        show_labels = st.checkbox("Show Corridor Labels", value=True, key="ov_labels")
    with col_opt1:
        if bundle is not None:
            view_mode = st.radio(
                "Overlay Mode",
                options=["flow", "min_cut", "topology"],
                format_func=lambda m: {
                    "flow": "Utilization & Flow",
                    "min_cut": "Min-Cut Partition (A/B)",
                    "topology": "Base Capacity",
                }[m],
                horizontal=True,
                key="ov_map_mode",
            )
        else:
            view_mode = "topology"
            st.caption("Showing base directed road capacities. Run Analysis to overlay flows and bottlenecks.")

    fig = build_network_figure(
        net,
        bundle=bundle,
        mode=view_mode,
        height=490,
        show_edge_labels=show_labels,
    )
    render_chart(fig, key="overview_network_plot")

    if bundle is not None:
        comp = get_comparison_result()
        if comp is None:
            comp = compare_dinic_vs_greedy(
                net, greedy_rule=GreedyRule.SHORTEST_HOP, repeats=1, trace=False
            )

        tab_analytics, tab_tables = st.tabs(
            ["Analytics Dashboard (6 Core Charts)", "Entity & Bottleneck Tables"]
        )
        with tab_analytics:
            st.caption(
                "Comprehensive visual diagnostics generated directly from Dinic Maximum Flow, "
                "Minimum Cut extraction, Scenario Lab / Saved Scenarios, and Greedy baseline runs."
            )
            a1, a2 = st.columns(2, gap="medium")
            with a1:
                render_chart(
                    build_max_flow_by_scenario_chart(
                        bundle,
                        lab_suite=st.session_state.get("scenario_lab_suite"),
                        saved_scenarios=st.session_state.get("saved_scenarios"),
                    ),
                    key="ov_an_scn",
                )
            with a2:
                render_chart(
                    build_evacuated_vs_remaining_chart(bundle), key="ov_an_evac_rem"
                )

            a3, a4 = st.columns(2, gap="medium")
            with a3:
                render_chart(
                    build_shelter_utilization_chart(bundle), key="ov_an_shl_util"
                )
            with a4:
                render_chart(
                    build_dinic_vs_greedy_summary_chart(comp), key="ov_an_dinic_greedy"
                )

            a5, a6 = st.columns(2, gap="medium")
            with a5:
                render_chart(
                    build_road_utilization_chart(bundle), key="ov_an_road_util"
                )
            with a6:
                render_chart(
                    build_bottleneck_road_capacities_chart(bundle),
                    key="ov_an_bottleneck_cap",
                )

        with tab_tables:
            c1, c2 = st.columns(2)
            with c1:
                render_chart(build_source_evacuation_chart(bundle), key="ov_src_chart")
            with c2:
                render_chart(build_shelter_intake_chart(bundle), key="ov_shl_chart")

            t1, t2 = st.columns(2)
            with t1:
                st.markdown(
                    '<div class="resq-section-title">Source Area Status</div>',
                    unsafe_allow_html=True,
                )
                render_table(build_sources_dataframe(bundle))
            with t2:
                st.markdown(
                    '<div class="resq-section-title">Critical Minimum-Cut Edges</div>',
                    unsafe_allow_html=True,
                )
                cut_df = build_min_cut_dataframe(bundle)
                if cut_df.empty:
                    st.caption("No cut edges detected.")
                else:
                    render_table(cut_df)

            st.markdown(
                '<div class="resq-section-title">Shelter Allocation Summary</div>',
                unsafe_allow_html=True,
            )
            render_table(build_shelters_dataframe(bundle))
    else:
        st.markdown(
            '<div class="resq-section-title">Current Network Inventory (Pre-Analysis)</div>',
            unsafe_allow_html=True,
        )
        inv1, inv2 = st.columns(2)
        with inv1:
            node_rows = [
                {
                    "ID": n.node_id,
                    "Name": n.name,
                    "Role": n.node_type.value.replace("_", " ").title(),
                    "Population": n.population,
                    "Shelter Cap": n.shelter_capacity,
                }
                for n in net.nodes.values()
            ]
            render_table(pd.DataFrame(node_rows))
        with inv2:
            road_rows = [
                {
                    "Road ID": r.road_id,
                    "From": r.source_id,
                    "To": r.target_id,
                    "Capacity": r.capacity,
                    "Active": "Yes" if r.is_active else "Closed",
                }
                for r in net.roads.values()
            ]
            render_table(pd.DataFrame(road_rows))
