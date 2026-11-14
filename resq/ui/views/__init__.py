"""Streamlit view modules for the ResQ navigation pages."""

from resq.ui.views.about import render_about_resq_page
from resq.ui.views.algo_compare import render_algorithm_comparison_page
from resq.ui.views.bottleneck import render_bottleneck_analysis_page
from resq.ui.views.builder import render_network_builder_page
from resq.ui.views.flow_analysis import render_flow_analysis_page
from resq.ui.views.overview import render_overview_page
from resq.ui.views.reports import render_reports_page
from resq.ui.views.scenario_lab import render_scenario_lab_page
from resq.ui.views.shortest_path import render_shortest_path_page
from resq.ui.views.simulation import render_live_simulation_page

__all__ = [
    "render_about_resq_page",
    "render_algorithm_comparison_page",
    "render_bottleneck_analysis_page",
    "render_flow_analysis_page",
    "render_live_simulation_page",
    "render_network_builder_page",
    "render_overview_page",
    "render_reports_page",
    "render_scenario_lab_page",
    "render_shortest_path_page",
]
