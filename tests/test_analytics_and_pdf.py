"""Unit tests for Analytics Dashboard charts, scalability benchmarks, and PDF report export."""

from resq import EvacuationNetwork, GreedyRule, NodeType, compare_dinic_vs_greedy
from resq.services import (
    DEFAULT_SCALABILITY_TIERS,
    build_benchmark_dataframe,
    evaluate_baseline_scenario,
    evaluate_road_closure_scenario,
    generate_pdf_report,
    load_preset_network,
    run_full_evacuation_analysis,
    run_scalability_benchmark,
)
from resq.ui.components import (
    build_bottleneck_road_capacities_chart,
    build_dinic_vs_greedy_summary_chart,
    build_evacuated_vs_remaining_chart,
    build_max_flow_by_scenario_chart,
    build_road_utilization_chart,
    build_scalability_benchmark_chart,
    build_shelter_utilization_chart,
)


def test_six_analytics_charts_render_from_real_results() -> None:
    net = load_preset_network("metro_flood_baseline")
    bundle = run_full_evacuation_analysis(net, trace=True)
    comp = compare_dinic_vs_greedy(net, greedy_rule=GreedyRule.SHORTEST_HOP)
    s1 = evaluate_baseline_scenario(net)
    s2 = evaluate_road_closure_scenario(net, s1, road_id="R_J1_J4")
    suite = {s1.scenario_key: s1, s2.scenario_key: s2}

    charts = [
        build_max_flow_by_scenario_chart(bundle, lab_suite=suite),
        build_shelter_utilization_chart(bundle),
        build_road_utilization_chart(bundle),
        build_dinic_vs_greedy_summary_chart(comp),
        build_evacuated_vs_remaining_chart(bundle),
        build_bottleneck_road_capacities_chart(bundle),
    ]
    for fig in charts:
        assert len(fig.data) >= 1


def test_scalability_benchmark_measures_real_perf_counter_across_tiers() -> None:
    tiers = DEFAULT_SCALABILITY_TIERS[:4]
    report = run_scalability_benchmark(
        tiers, greedy_rule=GreedyRule.SHORTEST_HOP, repeats=2
    )
    assert len(report.rows) == 4
    assert "time.perf_counter()" in report.disclaimer
    assert "hardware" in report.disclaimer.lower()

    prev_v = 0
    prev_e = 0
    for row in report.rows:
        assert row.num_vertices > prev_v
        assert row.num_edges > prev_e
        assert row.dinic_time_ms >= 0.0
        assert row.greedy_time_ms >= 0.0
        assert 0 <= row.greedy_flow <= row.dinic_max_flow
        prev_v = row.num_vertices
        prev_e = row.num_edges

    df = build_benchmark_dataframe(report)
    assert list(df.columns) == [
        "Tier",
        "Vertices (|V|)",
        "Directed Roads (|E|)",
        "Dinic Time (ms)",
        "Greedy Time (ms)",
        "Dinic Max Flow",
        "Greedy Flow",
        "Optimality Gap",
    ]
    scale_fig = build_scalability_benchmark_chart(report)
    assert len(scale_fig.data) == 2


def test_pdf_report_generation_valid_bytes_and_handles_edge_cases() -> None:
    net = load_preset_network("metro_flood_baseline")
    bundle = run_full_evacuation_analysis(net, trace=True)
    comp = compare_dinic_vs_greedy(net, greedy_rule=GreedyRule.SHORTEST_HOP)
    s1 = evaluate_baseline_scenario(net)
    s2 = evaluate_road_closure_scenario(net, s1, road_id="R_J1_J4")

    pdf_bytes = generate_pdf_report(
        bundle,
        comparison=comp,
        scenario_evaluations=[s1, s2],
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2500

    # Also test Unicode dashes/arrows & zero-flow network in PDF generator
    edge_net = EvacuationNetwork(
        network_id="unicode-edge",
        name="Sector Alpha — Bridge → Campus",
    )
    edge_net.add_node("A1", "Zone — West", NodeType.AFFECTED_AREA, population=100)
    edge_net.add_node("S1", "Shelter → Safe", NodeType.SHELTER, shelter_capacity=100)
    edge_bundle = run_full_evacuation_analysis(edge_net, trace=True)
    edge_pdf = generate_pdf_report(edge_bundle)
    assert edge_pdf.startswith(b"%PDF-")
