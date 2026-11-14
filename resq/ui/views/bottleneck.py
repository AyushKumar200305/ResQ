"""Page 5: Bottleneck Analysis (Minimum Cut Extraction & Upgrade Sensitivity)."""

import pandas as pd
import streamlit as st

from resq.services.evacuation_simulator import analyze_upgrade_sensitivity
from resq.ui.components import (
    KpiMetric,
    build_network_figure,
    build_upgrade_roi_chart,
    render_kpi_grid,
    render_pending_analysis_guard,
)
from resq.ui.state import get_analysis_bundle
from resq.ui.theme import render_chart, render_table


def render_bottleneck_analysis_page() -> None:
    """Render Minimum Cut partitioning, bottleneck categorization, and upgrade sensitivity."""
    bundle = get_analysis_bundle()
    if bundle is None:
        render_pending_analysis_guard("Bottleneck Analysis", "bottleneck")
        return

    mc = bundle.min_cut
    render_kpi_grid(
        [
            KpiMetric(
                label="Max-Flow = Min-Cut",
                value=f"{mc.total_cut_capacity:,}",
                subtext=f"Verified equal to Max Flow ({mc.max_flow:,})",
                tone="safe",
            ),
            KpiMetric(
                label="Road Cut Capacity",
                value=f"{mc.road_cut_capacity:,}",
                subtext=f"{len(mc.road_bottlenecks)} physical road bottleneck(s)",
                tone="crit" if mc.road_bottlenecks else "safe",
            ),
            KpiMetric(
                label="Shelter Cut Capacity",
                value=f"{mc.shelter_cut_capacity:,}",
                subtext=f"{len(mc.shelter_capacity_cuts)} shelter limit(s)",
                tone="warn" if mc.shelter_capacity_cuts else "neutral",
            ),
            KpiMetric(
                label="Source Demand Cut",
                value=f"{mc.super_source_cut_capacity:,}",
                subtext=f"{len(mc.super_source_cuts)} source(s) fully served at cap",
                tone="info",
            ),
        ]
    )

    st.markdown(
        '<div class="resq-section-title">Minimum Cut Partition Visualization (A vs. B)</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Blue-ringed vertices belong to Reachable Partition A (connected to Super-Source in the "
        "residual graph). Slate vertices belong to Unreachable Partition B. Crimson edges cross A -> B "
        "and define the exact Minimum Cut."
    )
    render_chart(
        build_network_figure(bundle.network, bundle=bundle, mode="min_cut", height=440),
        key="bottleneck_min_cut_map",
    )

    p1, p2 = st.columns(2)
    with p1:
        st.markdown(
            f"**Reachable Partition A ({len(mc.reachable_domain_nodes)} domain nodes)**"
        )
        st.code(", ".join(mc.reachable_domain_nodes) or "(Super-Source only)")
    with p2:
        st.markdown(
            f"**Unreachable Partition B ({len(mc.unreachable_domain_nodes)} domain nodes)**"
        )
        st.code(", ".join(mc.unreachable_domain_nodes) or "(None)")

    tab_roads, tab_shelters, tab_sources, tab_noncut = st.tabs(
        [
            f"Road Bottlenecks ({len(mc.road_bottlenecks)})",
            f"Shelter Limits ({len(mc.shelter_capacity_cuts)})",
            f"Source Demand Limits ({len(mc.super_source_cuts)})",
            f"Saturated Non-Cut Roads ({len(mc.saturated_non_cut_roads)})",
        ]
    )

    with tab_roads:
        if not mc.road_bottlenecks:
            st.info("No physical road corridors lie across the minimum cut.")
        else:
            render_table(
                pd.DataFrame(
                    [
                        {
                            "Road ID": e.edge_id,
                            "Label": e.label,
                            "From (A)": e.source_id,
                            "To (B)": e.target_id,
                            "Cut Capacity": e.original_capacity,
                            "Flow": e.flow,
                            "Active": "Yes" if e.is_active else "Closed",
                        }
                        for e in mc.road_bottlenecks
                    ]
                )
            )

    with tab_shelters:
        if not mc.shelter_capacity_cuts:
            st.info("No shelter intake edges are binding in the minimum cut.")
        else:
            render_table(
                pd.DataFrame(
                    [
                        {
                            "Shelter ID": e.edge_id,
                            "Label": e.label,
                            "Shelter Capacity": e.original_capacity,
                            "Assigned Flow": e.flow,
                        }
                        for e in mc.shelter_capacity_cuts
                    ]
                )
            )

    with tab_sources:
        if not mc.super_source_cuts:
            st.info("No affected-area source demand edge is in the minimum cut.")
        else:
            render_table(
                pd.DataFrame(
                    [
                        {
                            "Source ID": e.edge_id,
                            "Label": e.label,
                            "Affected Population": e.original_capacity,
                            "Evacuated Flow": e.flow,
                        }
                        for e in mc.super_source_cuts
                    ]
                )
            )

    with tab_noncut:
        st.caption(
            "These roads carry 100% of their capacity (residual = 0), yet BOTH endpoints lie in "
            "the same partition (A or B). Expanding them alone may not increase global max flow unless "
            "true minimum-cut bottlenecks are relieved."
        )
        if not mc.saturated_non_cut_roads:
            st.info("No saturated non-cut roads exist on this network.")
        else:
            rows = []
            for rid in mc.saturated_non_cut_roads:
                rf = bundle.dinic_result.road_flows[rid]
                rows.append(
                    {
                        "Road ID": rid,
                        "Corridor": f"{rf.source_id} -> {rf.target_id}",
                        "Capacity": rf.original_capacity,
                        "Flow": rf.flow,
                    }
                )
            render_table(pd.DataFrame(rows))

    # Upgrade sensitivity analysis
    st.markdown(
        '<div class="resq-section-title">Mitigation & Capacity Upgrade Sensitivity</div>',
        unsafe_allow_html=True,
    )
    delta_step = st.select_slider(
        "Test Capacity Expansion Increment (+units)",
        options=[50, 100, 200, 300, 500],
        value=100,
        key="bottleneck_delta_slider",
    )
    candidates = (
        bundle.upgrade_candidates
        if delta_step == 100
        else analyze_upgrade_sensitivity(
            bundle.network, bundle.dinic_result.max_flow, mc, delta_capacity=delta_step
        )
    )
    if not candidates:
        st.info(
            "No expandable road or shelter cut bottlenecks detected (all source demand is already fully served)."
        )
    else:
        render_chart(build_upgrade_roi_chart(candidates), key="bottleneck_roi_chart")
        render_table(
            pd.DataFrame(
                [
                    {
                        "Mitigation Target": c.label,
                        "Type": c.target_kind.title(),
                        "Current Cap": c.current_capacity,
                        "Added Cap": f"+{c.added_capacity:,}",
                        "New Max Flow": c.new_max_flow,
                        "Marginal Gain": f"+{c.marginal_flow_gain:,}",
                        "Efficiency (Gain/Unit)": round(c.gain_per_unit, 2),
                    }
                    for c in candidates
                ]
            )
        )
