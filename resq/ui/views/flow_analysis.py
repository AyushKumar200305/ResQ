"""Page 4: Flow Analysis (Dinic's Maximum Flow, Routes, and Phase Trace)."""

import pandas as pd
import streamlit as st

from resq.services.report_generator import (
    build_road_flows_dataframe,
    build_routes_dataframe,
    build_shelters_dataframe,
    build_sources_dataframe,
)
from resq.ui.components import (
    KpiMetric,
    build_dinic_phases_chart,
    build_network_figure,
    render_kpi_grid,
    render_pending_analysis_guard,
)
from resq.ui.state import get_analysis_bundle
from resq.ui.theme import render_chart, render_table


def render_flow_analysis_page() -> None:
    """Render detailed Dinic Maximum Flow telemetry, route decomposition, and BFS phases."""
    bundle = get_analysis_bundle()
    if bundle is None:
        render_pending_analysis_guard("Flow Analysis", "flow")
        return

    d = bundle.dinic_result
    render_kpi_grid(
        [
            KpiMetric(
                label="Dinic Maximum Flow",
                value=f"{d.max_flow:,}",
                subtext=f"{d.evacuation_rate * 100:.1f}% of affected population",
                tone="safe" if d.unmet_demand == 0 else "info",
            ),
            KpiMetric(
                label="BFS Level Phases",
                value=f"{d.bfs_phases}",
                subtext=f"{d.bfs_calls} total BFS checks",
                tone="info",
            ),
            KpiMetric(
                label="Useful Augmentations",
                value=f"{d.useful_augmentations}",
                subtext=f"{d.dfs_attempts} DFS path attempts · {d.dfs_edge_scans} scans",
                tone="neutral",
            ),
            KpiMetric(
                label="Solver Execution Time",
                value=f"{d.execution_time_ms:.3f} ms",
                subtext=f"{d.execution_time_ns:,} ns",
                tone="safe",
            ),
        ]
    )

    st.markdown(
        '<div class="resq-section-title">Corridor Flow Utilization Map</div>',
        unsafe_allow_html=True,
    )
    render_chart(
        build_network_figure(bundle.network, bundle=bundle, mode="flow", height=440),
        key="flow_analysis_map",
    )

    tab_roads, tab_routes, tab_entities, tab_trace = st.tabs(
        [
            "Road Flows & Residuals",
            f"Evacuation Routes ({len(bundle.routes)})",
            "Sources & Shelters",
            "Dinic BFS/DFS Trace",
        ]
    )

    with tab_roads:
        render_table(build_road_flows_dataframe(bundle))

    with tab_routes:
        routes_df = build_routes_dataframe(bundle)
        if routes_df.empty:
            st.info("No positive-flow evacuation routes were found on this topology.")
        else:
            st.caption(
                f"Decomposed {len(bundle.routes)} source-to-shelter evacuation routes "
                f"accounting for {sum(r.flow for r in bundle.routes):,} total evacuees."
            )
            render_table(routes_df)

    with tab_entities:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Affected Area Dispatch**")
            render_table(build_sources_dataframe(bundle))
        with c2:
            st.markdown("**Shelter Intake Allocation**")
            render_table(build_shelters_dataframe(bundle))

    with tab_trace:
        if d.trace is None:
            st.info("Detailed execution trace was disabled for this run.")
        else:
            render_chart(build_dinic_phases_chart(d), key="flow_dinic_phases_chart")
            st.caption(
                f"Total active BFS phases: {d.trace.total_phases_with_flow} | "
                f"Augmenting steps: {d.trace.total_augmentations} | "
                f"Reverse-edge rerouting steps: {d.trace.reverse_rerouting_steps}"
            )

            phase_options = list(range(len(d.trace.phases)))
            selected_idx = st.selectbox(
                "Inspect BFS Phase",
                options=phase_options,
                format_func=lambda idx: (
                    f"Phase {d.trace.phases[idx].phase_index} — "
                    + (
                        f"Sink Level {d.trace.phases[idx].sink_level} | Flow +{d.trace.phases[idx].phase_flow_pushed:,}"
                        if d.trace.phases[idx].sink_reachable
                        else "Sink Unreachable (Terminated)"
                    )
                ),
                key="flow_trace_phase_sel",
            )
            phase = d.trace.phases[selected_idx]

            p_col1, p_col2 = st.columns([1.0, 1.5])
            with p_col1:
                st.markdown("**Reachable Vertex Levels**")
                lvl_df = pd.DataFrame(
                    [
                        {"Vertex": vid, "BFS Level": lvl}
                        for vid, lvl in phase.node_levels.items()
                    ]
                )
                render_table(lvl_df, height=260)
            with p_col2:
                st.markdown("**DFS Augmenting Paths & Residual Updates**")
                if not phase.augmentations:
                    st.caption("No paths augmented in this phase (sink unreachable).")
                else:
                    aug_rows = [
                        {
                            "Step": step.step_index,
                            "Path": " -> ".join(step.selected_path),
                            "Flow Sent": step.flow_sent,
                            "Reverse Edge Reroute": "Yes" if step.rerouted_via_reverse_edge else "No",
                        }
                        for step in phase.augmentations
                    ]
                    render_table(pd.DataFrame(aug_rows), height=200)

                    step_idx = st.selectbox(
                        "Inspect Residual Edge Updates for Step",
                        options=list(range(len(phase.augmentations))),
                        format_func=lambda i: (
                            f"Step {phase.augmentations[i].step_index}: "
                            f"+{phase.augmentations[i].flow_sent:,} along "
                            f"{' -> '.join(phase.augmentations[i].selected_path)}"
                        ),
                        key=f"flow_step_sel_{selected_idx}",
                    )
                    chosen_step = phase.augmentations[step_idx]
                    upd_df = pd.DataFrame(
                        [
                            {
                                "Edge ID": u.edge_id,
                                "Direction": f"{u.traversed_from} -> {u.traversed_to}",
                                "Reverse Edge": "Yes" if u.used_reverse_edge else "No",
                                "Fwd Res (Before -> After)": f"{u.forward_residual_before:,} -> {u.forward_residual_after:,}",
                                "Rev Res (Before -> After)": f"{u.reverse_residual_before:,} -> {u.reverse_residual_after:,}",
                            }
                            for u in chosen_step.edge_updates
                        ]
                    )
                    render_table(upd_df)
