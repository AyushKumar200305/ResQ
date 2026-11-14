"""Reusable UI components for ResQ Streamlit views."""

from resq.ui.components.charts import (
    build_algorithm_comparison_chart,
    build_bottleneck_road_capacities_chart,
    build_dinic_phases_chart,
    build_dinic_vs_greedy_summary_chart,
    build_evacuated_vs_remaining_chart,
    build_max_flow_by_scenario_chart,
    build_road_utilization_chart,
    build_scalability_benchmark_chart,
    build_scenario_comparison_chart,
    build_shelter_intake_chart,
    build_shelter_utilization_chart,
    build_source_evacuation_chart,
    build_upgrade_roi_chart,
    build_wave_timeline_chart,
    build_whatif_comparison_chart,
    build_whatif_delta_chart,
)
from resq.ui.components.kpi_bar import (
    KpiMetric,
    render_control_header,
    render_kpi_grid,
    render_pending_analysis_guard,
)
from resq.ui.components.network_plot import build_network_figure

__all__ = [
    "KpiMetric",
    "build_algorithm_comparison_chart",
    "build_bottleneck_road_capacities_chart",
    "build_dinic_phases_chart",
    "build_dinic_vs_greedy_summary_chart",
    "build_evacuated_vs_remaining_chart",
    "build_max_flow_by_scenario_chart",
    "build_network_figure",
    "build_road_utilization_chart",
    "build_scalability_benchmark_chart",
    "build_scenario_comparison_chart",
    "build_shelter_intake_chart",
    "build_shelter_utilization_chart",
    "build_source_evacuation_chart",
    "build_upgrade_roi_chart",
    "build_wave_timeline_chart",
    "build_whatif_comparison_chart",
    "build_whatif_delta_chart",
    "render_control_header",
    "render_kpi_grid",
    "render_pending_analysis_guard",
]
