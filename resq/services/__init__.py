"""Application services for flow modeling, simulation, presets, comparisons, and reporting."""

from resq.services.benchmark import (
    DEFAULT_SCALABILITY_TIERS,
    PerformanceBenchmarkRow,
    ScalabilityBenchmarkReport,
    ScalabilityTierSpec,
    build_benchmark_dataframe,
    generate_benchmark_network,
    run_scalability_benchmark,
)
from resq.services.comparator import compare_dinic_vs_greedy, explain_greedy_rule
from resq.services.evacuation_simulator import (
    DisruptionSpec,
    FullAnalysisBundle,
    UpgradeCandidate,
    WaveStep,
    analyze_upgrade_sensitivity,
    apply_disruptions,
    run_full_evacuation_analysis,
    simulate_evacuation_waves,
)
from resq.services.network_builder import build_evacuation_network
from resq.services.pdf_report import generate_pdf_report
from resq.services.playback import PlaybackFrame, build_playback_frames
from resq.services.presets import PresetDescriptor, list_presets, load_preset_network
from resq.services.scenario_lab import (
    ScenarioEvaluation,
    build_scenario_lab_comparison_dataframe,
    evaluate_baseline_scenario,
    evaluate_increased_shelter_scenario,
    evaluate_multiple_road_failures_scenario,
    evaluate_reduced_shelter_scenario,
    evaluate_road_closure_scenario,
    generate_scenario_observations,
)
from resq.services.report_generator import (
    build_min_cut_dataframe,
    build_road_flows_dataframe,
    build_routes_dataframe,
    build_shelters_dataframe,
    build_sources_dataframe,
    generate_html_report,
    generate_markdown_report,
)
from resq.services.scenario_io import (
    export_network_to_dict,
    export_network_to_json,
    import_network_from_dict,
    import_network_from_json,
    load_network_json,
    save_network_json,
)
from resq.services.shortest_path_service import (
    FlowRouteComparisonRow,
    ShortestRoadFlowStatus,
    ShortestVsMaxFlowComparison,
    compare_shortest_path_with_max_flow,
)

__all__ = [
    "DEFAULT_SCALABILITY_TIERS",
    "DisruptionSpec",
    "FlowRouteComparisonRow",
    "FullAnalysisBundle",
    "PerformanceBenchmarkRow",
    "PlaybackFrame",
    "PresetDescriptor",
    "ScalabilityBenchmarkReport",
    "ScalabilityTierSpec",
    "ScenarioEvaluation",
    "ShortestRoadFlowStatus",
    "ShortestVsMaxFlowComparison",
    "UpgradeCandidate",
    "WaveStep",
    "analyze_upgrade_sensitivity",
    "apply_disruptions",
    "build_benchmark_dataframe",
    "build_evacuation_network",
    "build_min_cut_dataframe",
    "build_playback_frames",
    "build_road_flows_dataframe",
    "build_routes_dataframe",
    "build_scenario_lab_comparison_dataframe",
    "build_shelters_dataframe",
    "build_sources_dataframe",
    "compare_dinic_vs_greedy",
    "compare_shortest_path_with_max_flow",
    "evaluate_baseline_scenario",
    "evaluate_increased_shelter_scenario",
    "evaluate_multiple_road_failures_scenario",
    "evaluate_reduced_shelter_scenario",
    "evaluate_road_closure_scenario",
    "explain_greedy_rule",
    "export_network_to_dict",
    "export_network_to_json",
    "generate_benchmark_network",
    "generate_html_report",
    "generate_markdown_report",
    "generate_pdf_report",
    "generate_scenario_observations",
    "import_network_from_dict",
    "import_network_from_json",
    "list_presets",
    "load_network_json",
    "load_preset_network",
    "run_full_evacuation_analysis",
    "run_scalability_benchmark",
    "save_network_json",
    "simulate_evacuation_waves",
]
