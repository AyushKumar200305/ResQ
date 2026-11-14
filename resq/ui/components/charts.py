"""Standardized dark-theme Plotly charts for ResQ analytics views."""

import plotly.graph_objects as go

from resq.domain.results import AlgorithmComparisonResult, DinicResult
from resq.services.evacuation_simulator import (
    FullAnalysisBundle,
    UpgradeCandidate,
    WaveStep,
)
from resq.ui.state import SavedScenarioRecord
from resq.ui.theme import (
    COLOR_CRIT,
    COLOR_IDLE,
    COLOR_INFO,
    COLOR_SAFE,
    COLOR_WARN,
    apply_plotly_dark_theme,
)


def build_source_evacuation_chart(bundle: FullAnalysisBundle) -> go.Figure:
    """Stacked bar chart of Evacuated vs. Unallocated population per affected area."""
    details = list(bundle.dinic_result.source_evacuations.values())
    labels = [f"{d.node_id} ({d.name})" for d in details]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Evacuated",
            x=labels,
            y=[d.evacuated for d in details],
            marker_color=COLOR_SAFE,
        )
    )
    fig.add_trace(
        go.Bar(
            name="Unallocated",
            x=labels,
            y=[d.unmet_demand for d in details],
            marker_color=COLOR_CRIT,
        )
    )
    fig.update_layout(barmode="stack", yaxis_title="People")
    return apply_plotly_dark_theme(fig, height=340, title="Source Evacuation vs. Unallocated Demand")


def build_shelter_intake_chart(bundle: FullAnalysisBundle) -> go.Figure:
    """Stacked bar chart of Assigned Flow vs. Remaining Capacity per shelter."""
    details = list(bundle.dinic_result.shelter_intakes.values())
    labels = [f"{d.node_id} ({d.name})" for d in details]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Assigned Flow",
            x=labels,
            y=[d.assigned_flow for d in details],
            marker_color=COLOR_INFO,
        )
    )
    fig.add_trace(
        go.Bar(
            name="Remaining Capacity",
            x=labels,
            y=[d.remaining_capacity for d in details],
            marker_color=COLOR_IDLE,
        )
    )
    fig.update_layout(barmode="stack", yaxis_title="Capacity (People)")
    return apply_plotly_dark_theme(fig, height=340, title="Shelter Intake & Remaining Capacity")


def build_dinic_phases_chart(dinic_result: DinicResult) -> go.Figure:
    """Bar + cumulative line chart across Dinic BFS level-graph phases."""
    fig = go.Figure()
    if dinic_result.trace is None:
        return apply_plotly_dark_theme(fig, height=320, title="Dinic Phase Progress")

    active_phases = [p for p in dinic_result.trace.phases if p.sink_reachable]
    phase_labels = [f"Phase {p.phase_index} (L={p.sink_level})" for p in active_phases]

    fig.add_trace(
        go.Bar(
            name="Phase Blocking Flow",
            x=phase_labels,
            y=[p.phase_flow_pushed for p in active_phases],
            marker_color=COLOR_INFO,
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Cumulative Flow",
            x=phase_labels,
            y=[p.cumulative_flow for p in active_phases],
            mode="lines+markers",
            line=dict(color=COLOR_SAFE, width=2.5),
            marker=dict(size=7),
        )
    )
    fig.update_layout(yaxis_title="Flow Units")
    return apply_plotly_dark_theme(fig, height=320, title="Flow Augmented per Dinic BFS Phase")


def build_wave_timeline_chart(wave_timeline: tuple[WaveStep, ...] | list[WaveStep]) -> go.Figure:
    """Line chart showing multi-hour cumulative evacuations vs. remaining population."""
    hours = [f"Hr {w.hour}" for w in wave_timeline]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            name="Cumulative Evacuated",
            x=hours,
            y=[w.cumulative_evacuated for w in wave_timeline],
            mode="lines+markers",
            line=dict(color=COLOR_SAFE, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(34, 197, 94, 0.10)",
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Remaining Population",
            x=hours,
            y=[w.remaining_population for w in wave_timeline],
            mode="lines+markers",
            line=dict(color=COLOR_WARN, width=2.2, dash="dash"),
        )
    )
    fig.update_layout(yaxis_title="People")
    return apply_plotly_dark_theme(
        fig, height=340, title="Multi-Hour Wave Evacuation Projection"
    )


def build_upgrade_roi_chart(candidates: tuple[UpgradeCandidate, ...] | list[UpgradeCandidate]) -> go.Figure:
    """Horizontal bar chart ranking marginal flow gain from upgrading min-cut bottlenecks."""
    top = list(candidates)[:10]
    top.reverse()
    fig = go.Figure(
        go.Bar(
            x=[c.marginal_flow_gain for c in top],
            y=[c.label for c in top],
            orientation="h",
            marker_color=[
                COLOR_SAFE if c.marginal_flow_gain > 0 else COLOR_IDLE for c in top
            ],
            text=[f"+{c.marginal_flow_gain:,}" for c in top],
            textposition="outside",
        )
    )
    fig.update_layout(xaxis_title="Additional Evacuees Enabled")
    return apply_plotly_dark_theme(
        fig, height=max(260, 60 + 36 * len(top)), title="Bottleneck Upgrade Sensitivity Gain"
    )


def _build_grouped_evacuation_bar(
    labels: list[str],
    max_flows: list[int],
    unmet: list[int],
    title: str,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(name="Max Evacuation Flow", x=labels, y=max_flows, marker_color=COLOR_SAFE)
    )
    fig.add_trace(
        go.Bar(name="People Left Unallocated", x=labels, y=unmet, marker_color=COLOR_CRIT)
    )
    fig.update_layout(barmode="group", yaxis_title="People")
    return apply_plotly_dark_theme(fig, height=360, title=title)


def build_scenario_comparison_chart(records: list[SavedScenarioRecord]) -> go.Figure:
    """Grouped bar chart comparing Max Flow vs. Unallocated Evacuees across scenarios."""
    return _build_grouped_evacuation_bar(
        labels=[r.label for r in records],
        max_flows=[r.bundle.dinic_result.max_flow if r.bundle else 0 for r in records],
        unmet=[r.bundle.dinic_result.unmet_demand if r.bundle else 0 for r in records],
        title="Scenario Evacuation Performance",
    )


def build_whatif_comparison_chart(evaluations) -> go.Figure:
    """Grouped bar chart for Scenario Lab 5-scenario what-if comparison."""
    return _build_grouped_evacuation_bar(
        labels=[e.scenario_name for e in evaluations],
        max_flows=[e.bundle.dinic_result.max_flow for e in evaluations],
        unmet=[e.bundle.dinic_result.unmet_demand for e in evaluations],
        title="What-If Scenarios: Max Flow vs. Unallocated Population",
    )


def build_whatif_delta_chart(evaluations) -> go.Figure:
    """Diverging bar chart showing net evacuation flow change from baseline."""
    labels = [e.scenario_name for e in evaluations]
    deltas = [e.baseline_delta for e in evaluations]
    colors = [
        COLOR_SAFE if d > 0 else (COLOR_CRIT if d < 0 else COLOR_IDLE)
        for d in deltas
    ]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=deltas,
            marker_color=colors,
            text=[f"{d:+,}" for d in deltas],
            textposition="outside",
        )
    )
    fig.update_layout(yaxis_title="Flow Delta vs. Baseline")
    return apply_plotly_dark_theme(
        fig, height=360, title="Net Change in Maximum Flow from Baseline"
    )


def build_algorithm_comparison_chart(comparison: AlgorithmComparisonResult) -> go.Figure:
    """Grouped bar chart comparing Dinic optimal flow vs. Greedy baseline across roads."""
    roads = list(comparison.road_comparisons)
    labels = [rc.road_id for rc in roads]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Dinic Optimal Flow",
            x=labels,
            y=[rc.dinic_flow for rc in roads],
            marker_color=COLOR_INFO,
        )
    )
    fig.add_trace(
        go.Bar(
            name=f"Greedy ({comparison.greedy_result.rule})",
            x=labels,
            y=[rc.greedy_flow for rc in roads],
            marker_color=COLOR_WARN,
        )
    )
    fig.update_layout(barmode="group", yaxis_title="Flow Units")
    return apply_plotly_dark_theme(
        fig, height=360, title="Road Flow Allocation: Dinic vs. Greedy Baseline"
    )


def build_road_utilization_chart(bundle: FullAnalysisBundle) -> go.Figure:
    """Horizontal bar chart showing road-wise capacity utilization percentage."""
    cut_ids = {e.edge_id for e in bundle.min_cut.road_bottlenecks}
    non_cut_sat = set(bundle.min_cut.saturated_non_cut_roads)

    roads = sorted(
        bundle.dinic_result.road_flows.values(),
        key=lambda r: (r.utilization_ratio, r.flow, r.road_id),
    )
    labels = [f"{r.road_id} ({r.source_id}->{r.target_id})" for r in roads]
    pcts = [round(r.utilization_ratio * 100.0, 1) for r in roads]
    colors = []
    for r in roads:
        if r.road_id in cut_ids:
            colors.append(COLOR_CRIT)
        elif r.road_id in non_cut_sat or r.utilization_ratio >= 0.75:
            colors.append(COLOR_WARN)
        elif r.flow > 0:
            colors.append(COLOR_INFO)
        else:
            colors.append(COLOR_IDLE)

    fig = go.Figure(
        go.Bar(
            x=pcts,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{r.flow:,}/{r.original_capacity:,} ({p:.0f}%)" for r, p in zip(roads, pcts)],
            textposition="outside",
            showlegend=False,
        )
    )
    fig.update_layout(
        xaxis_title="Capacity Utilization (%)",
        xaxis=dict(range=[0, 125]),
    )
    return apply_plotly_dark_theme(
        fig,
        height=max(320, 48 + 28 * len(roads)),
        title="Road-Wise Capacity Utilization (%)",
    )


def build_shelter_utilization_chart(bundle: FullAnalysisBundle) -> go.Figure:
    """Horizontal bar chart showing shelter-wise occupancy percentage and intake."""
    cut_shl = {e.edge_id for e in bundle.min_cut.shelter_capacity_cuts}
    shelters = sorted(
        bundle.dinic_result.shelter_intakes.values(),
        key=lambda s: (
            (s.assigned_flow / s.shelter_capacity) if s.shelter_capacity > 0 else 0.0
        ),
    )
    labels = [f"{s.node_id} ({s.name})" for s in shelters]
    pcts = [
        round((s.assigned_flow / s.shelter_capacity * 100.0), 1)
        if s.shelter_capacity > 0
        else 0.0
        for s in shelters
    ]
    colors = [
        COLOR_CRIT
        if s.node_id in cut_shl
        else (COLOR_WARN if p >= 80.0 else COLOR_SAFE)
        for s, p in zip(shelters, pcts)
    ]

    fig = go.Figure(
        go.Bar(
            x=pcts,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{s.assigned_flow:,}/{s.shelter_capacity:,} ({p:.0f}%)" for s, p in zip(shelters, pcts)],
            textposition="outside",
            showlegend=False,
        )
    )
    fig.update_layout(
        xaxis_title="Shelter Utilization (%)",
        xaxis=dict(range=[0, 125]),
    )
    return apply_plotly_dark_theme(
        fig,
        height=max(260, 70 + 38 * len(shelters)),
        title="Shelter-Wise Capacity Utilization (%)",
    )


def build_evacuated_vs_remaining_chart(bundle: FullAnalysisBundle) -> go.Figure:
    """Donut chart showing aggregate people evacuated versus remaining unallocated."""
    d = bundle.dinic_result
    fig = go.Figure(
        go.Pie(
            labels=["Evacuated", "Remaining Unallocated"],
            values=[d.max_flow, d.unmet_demand],
            hole=0.58,
            marker=dict(colors=[COLOR_SAFE, COLOR_CRIT]),
            textinfo="label+percent+value",
        )
    )
    return apply_plotly_dark_theme(
        fig, height=340, title="People Evacuated vs. Remaining Unallocated"
    )


def build_bottleneck_road_capacities_chart(bundle: FullAnalysisBundle) -> go.Figure:
    """Bar chart showing Minimum-Cut bottleneck road capacities vs. saturated non-cut roads."""
    road_cuts = list(bundle.min_cut.road_bottlenecks)
    fig = go.Figure()
    if road_cuts:
        fig.add_trace(
            go.Bar(
                name="Minimum-Cut Road Capacity",
                x=[f"{e.edge_id} ({e.source_id}->{e.target_id})" for e in road_cuts],
                y=[e.original_capacity for e in road_cuts],
                marker_color=COLOR_CRIT,
                text=[f"{e.original_capacity:,}" for e in road_cuts],
                textposition="outside",
            )
        )
    else:
        fig.add_annotation(
            text="No physical road edges in Minimum Cut (source demand or shelter caps govern flow).",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
    fig.update_layout(yaxis_title="Bottleneck Capacity")
    return apply_plotly_dark_theme(
        fig, height=340, title="Minimum-Cut Bottleneck Road Capacities"
    )


def build_dinic_vs_greedy_summary_chart(comparison: AlgorithmComparisonResult) -> go.Figure:
    """Bar chart comparing Dinic optimal total flow against Greedy baseline total flow."""
    fig = go.Figure(
        go.Bar(
            x=["Dinic's Maximum Flow", f"Greedy ({comparison.greedy_result.rule})"],
            y=[comparison.dinic_max_flow, comparison.greedy_flow],
            marker_color=[COLOR_SAFE, COLOR_WARN],
            text=[f"{comparison.dinic_max_flow:,}", f"{comparison.greedy_flow:,}"],
            textposition="outside",
        )
    )
    fig.update_layout(yaxis_title="Total Evacuation Flow")
    return apply_plotly_dark_theme(
        fig, height=340, title="Dinic vs. Greedy Total Evacuation Flow"
    )


def build_max_flow_by_scenario_chart(
    bundle: FullAnalysisBundle,
    lab_suite: dict | None = None,
    saved_scenarios: dict | None = None,
) -> go.Figure:
    """Bar chart of Maximum Flow across Scenario Lab / saved scenarios (or active baseline)."""
    labels: list[str] = []
    flows: list[int] = []
    colors: list[str] = []

    if lab_suite:
        for ev in lab_suite.values():
            labels.append(ev.scenario_name)
            flows.append(ev.bundle.dinic_result.max_flow)
            colors.append(
                COLOR_SAFE if ev.baseline_delta >= 0 else COLOR_CRIT
            )
    elif saved_scenarios:
        for rec in saved_scenarios.values():
            if rec.bundle is not None:
                labels.append(rec.label)
                flows.append(rec.bundle.dinic_result.max_flow)
                colors.append(COLOR_INFO)

    if not labels:
        labels = [bundle.network.name]
        flows = [bundle.dinic_result.max_flow]
        colors = [COLOR_INFO]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=flows,
            marker_color=colors,
            text=[f"{v:,}" for v in flows],
            textposition="outside",
        )
    )
    fig.update_layout(yaxis_title="Maximum Evacuation Flow")
    return apply_plotly_dark_theme(fig, height=340, title="Maximum Flow by Scenario")


def build_scalability_benchmark_chart(benchmark_report) -> go.Figure:
    """Line chart comparing Dinic vs. Greedy runtime (ms) across generated network sizes."""
    rows = benchmark_report.rows
    x_labels = [f"{r.tier_label}<br>(|E|={r.num_edges})" for r in rows]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            name="Dinic Execution Time (ms)",
            x=x_labels,
            y=[r.dinic_time_ms for r in rows],
            mode="lines+markers",
            line=dict(color=COLOR_INFO, width=2.8),
            marker=dict(size=8),
        )
    )
    fig.add_trace(
        go.Scatter(
            name=f"Greedy ({benchmark_report.greedy_rule}) Time (ms)",
            x=x_labels,
            y=[r.greedy_time_ms for r in rows],
            mode="lines+markers",
            line=dict(color=COLOR_WARN, width=2.4, dash="dash"),
            marker=dict(size=8),
        )
    )
    fig.update_layout(yaxis_title="Execution Time (ms)")
    return apply_plotly_dark_theme(
        fig,
        height=360,
        title="Scalability Benchmark: Execution Time vs. Network Size",
    )
