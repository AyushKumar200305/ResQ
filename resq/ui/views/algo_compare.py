"""Page 7: Algorithm Comparison & Multi-Size Scalability Performance Benchmark."""

import pandas as pd
import streamlit as st

from resq.domain.enums import GreedyRule
from resq.domain.exceptions import ResQError
from resq.services.benchmark import (
    DEFAULT_SCALABILITY_TIERS,
    ScalabilityBenchmarkReport,
    build_benchmark_dataframe,
    run_scalability_benchmark,
)
from resq.services.comparator import compare_dinic_vs_greedy
from resq.ui.components import (
    KpiMetric,
    build_algorithm_comparison_chart,
    build_dinic_vs_greedy_summary_chart,
    build_network_figure,
    build_scalability_benchmark_chart,
    render_kpi_grid,
)
from resq.ui.state import (
    get_active_network,
    get_analysis_bundle,
    get_comparison_result,
    load_demo_network,
    run_primary_analysis,
    set_comparison_result,
    set_flash,
)
from resq.ui.theme import render_chart, render_table


def _render_active_comparison_tab() -> None:
    net = get_active_network()
    report = net.validate()
    if not report.is_valid:
        st.error("Network validation failed: " + " | ".join(report.errors))
        return

    pending_rule = st.session_state.pop("_pending_cmp_greedy_rule", None)
    if pending_rule is not None:
        st.session_state["cmp_greedy_rule"] = pending_rule

    c1, c2, c3, c4 = st.columns([1.6, 1.2, 1.3, 1.5], vertical_alignment="bottom")
    with c1:
        rule_val = st.selectbox(
            "Greedy Route-Selection Rule",
            options=[r.value for r in GreedyRule],
            format_func=lambda v: {
                "shortest_hop": "Shortest-Hop Forward BFS",
                "widest_path": "Widest-Path Bottleneck Greedy",
                "lexicographic_dfs": "Lexicographic Forward DFS",
            }[v],
            key="cmp_greedy_rule",
        )
    with c2:
        repeats = int(
            st.selectbox(
                "Timing Repeats (Median)",
                options=[1, 5, 10, 25],
                index=1,
                key="cmp_repeats",
            )
        )
    with c3:
        if st.button(
            "Run Algorithm Benchmark",
            type="primary",
            width="stretch",
            key="cmp_run_btn",
        ):
            try:
                with st.spinner("Benchmarking Dinic vs. Greedy on isolated FlowNetworks..."):
                    if get_analysis_bundle() is None:
                        run_primary_analysis(trace=True)
                    comp = compare_dinic_vs_greedy(
                        net,
                        greedy_rule=rule_val,
                        repeats=repeats,
                        trace=True,
                    )
            except ResQError as exc:
                st.error(str(exc))
            else:
                set_comparison_result(comp)
                set_flash(
                    "success",
                    f"Benchmark complete: Dinic={comp.dinic_max_flow:,} vs. Greedy={comp.greedy_flow:,}.",
                )
                st.rerun()
    with c4:
        if st.button("Load Greedy-Trap Benchmark", width="stretch", key="cmp_load_trap"):
            ok, msg = load_demo_network("greedy_trap_benchmark")
            if ok:
                run_primary_analysis(trace=True)
                comp = compare_dinic_vs_greedy(
                    get_active_network(),
                    greedy_rule=GreedyRule.SHORTEST_HOP,
                    repeats=5,
                    trace=True,
                )
                set_comparison_result(comp)
                st.session_state["_pending_cmp_greedy_rule"] = GreedyRule.SHORTEST_HOP.value
            set_flash("info" if ok else "error", msg)
            st.rerun()

    comp = get_comparison_result()
    if comp is None:
        st.info(
            "Select a deterministic Greedy rule and click **Run Algorithm Benchmark** to compare "
            "flow optimality, execution time, and edge allocations against Dinic's algorithm — or "
            "click **Load Greedy-Trap Benchmark** to observe a canonical suboptimality gap."
        )
        return

    render_kpi_grid(
        [
            KpiMetric(
                label="Dinic Optimal Flow",
                value=f"{comp.dinic_max_flow:,}",
                subtext=f"{comp.dinic_result.bfs_phases} BFS phases · {comp.dinic_result.useful_augmentations} paths",
                tone="safe",
            ),
            KpiMetric(
                label="Greedy Baseline Flow",
                value=f"{comp.greedy_flow:,}",
                subtext=f"Rule: {comp.greedy_result.rule} · {comp.greedy_result.augmentations} paths",
                tone="safe" if comp.flow_difference == 0 else "warn",
            ),
            KpiMetric(
                label="Flow Optimality Gap",
                value=f"{comp.flow_difference:,}",
                subtext=f"{comp.optimality_gap_pct:.1f}% evacuees lost without residual rerouting",
                tone="safe" if comp.flow_difference == 0 else "crit",
            ),
            KpiMetric(
                label="Runtime (Dinic / Greedy)",
                value=f"{comp.dinic_time_ms:.3f} / {comp.greedy_time_ms:.3f} ms",
                subtext=f"Median of {comp.benchmark_repeats} run(s) · Ratio {comp.relative_speed_ratio:.2f}x",
                tone="info",
            ),
        ]
    )

    st.info(f"**Why Greedy Behavior Varies:** {comp.rule_explanation}")

    col_sum, col_chart = st.columns([0.85, 1.15], gap="medium")
    with col_sum:
        render_chart(build_dinic_vs_greedy_summary_chart(comp), key="cmp_summary_chart")
    with col_chart:
        render_chart(build_algorithm_comparison_chart(comp), key="cmp_bar_chart")

    st.markdown(
        '<div class="resq-section-title">Edge Flow Difference Map (Blue: Dinic > Greedy | Amber: Greedy > Dinic)</div>',
        unsafe_allow_html=True,
    )
    bundle = get_analysis_bundle()
    render_chart(
        build_network_figure(
            net,
            bundle=bundle,
            mode="diff",
            comparison=comp,
            height=410,
        ),
        key="cmp_diff_map",
    )

    st.markdown(
        '<div class="resq-section-title">Per-Corridor Allocation Comparison</div>',
        unsafe_allow_html=True,
    )
    diff_rows = [
        {
            "Road ID": rc.road_id,
            "Corridor": f"{rc.source_id} -> {rc.target_id}",
            "Capacity": rc.capacity,
            "Dinic Flow": rc.dinic_flow,
            "Greedy Flow": rc.greedy_flow,
            "Delta (Dinic - Greedy)": rc.flow_difference,
        }
        for rc in comp.road_comparisons
    ]
    render_table(pd.DataFrame(diff_rows))


def _render_scalability_tab() -> None:
    st.caption(
        "Generate multi-layer evacuation networks of increasing scale and measure actual execution "
        "time using Python's time.perf_counter() for both Dinic's Maximum Flow and the Greedy baseline."
    )

    s1, s2, s3 = st.columns([1.4, 1.2, 1.4], vertical_alignment="bottom")
    with s1:
        bench_rule = st.selectbox(
            "Greedy Baseline Rule",
            options=[r.value for r in GreedyRule],
            format_func=lambda v: {
                "shortest_hop": "Shortest-Hop Forward BFS",
                "widest_path": "Widest-Path Bottleneck Greedy",
                "lexicographic_dfs": "Lexicographic Forward DFS",
            }[v],
            key="bench_rule_sel",
        )
    with s2:
        bench_repeats = int(
            st.selectbox(
                "Runs per Size Tier (Median)",
                options=[1, 3, 5],
                index=1,
                key="bench_repeats_sel",
            )
        )
    with s3:
        if st.button(
            "Run Performance Benchmark",
            type="primary",
            width="stretch",
            key="bench_run_btn",
        ):
            with st.spinner("Generating benchmark topologies and timing Dinic vs. Greedy..."):
                bench_report = run_scalability_benchmark(
                    DEFAULT_SCALABILITY_TIERS,
                    greedy_rule=bench_rule,
                    repeats=bench_repeats,
                )
            st.session_state["scalability_report"] = bench_report
            set_flash("success", "Scalability benchmark complete across 5 network sizes.")
            st.rerun()

    bench_report: ScalabilityBenchmarkReport | None = st.session_state.get(
        "scalability_report"
    )
    if bench_report is None:
        st.info(
            "Click **Run Performance Benchmark** to evaluate 5 generated topologies "
            "(12 to 180 domain vertices) with `time.perf_counter()`."
        )
        return

    st.warning(f"**Measurement Disclaimer:** {bench_report.disclaimer}")
    render_chart(build_scalability_benchmark_chart(bench_report), key="bench_scale_chart")

    st.markdown(
        '<div class="resq-section-title">Measured Execution Times & Flow Outcomes</div>',
        unsafe_allow_html=True,
    )
    render_table(build_benchmark_dataframe(bench_report))


def render_algorithm_comparison_page() -> None:
    """Render Active Algorithm Comparison and Multi-Size Scalability Benchmarking."""
    tab_active, tab_scale = st.tabs(
        ["Active Network Comparison", "Performance & Scalability Analysis"]
    )
    with tab_active:
        _render_active_comparison_tab()
    with tab_scale:
        _render_scalability_tab()
