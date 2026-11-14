"""Unit tests for path decomposition, simulation services, presets, and reports."""

import pytest

from resq import (
    EvacuationNetwork,
    GreedyRule,
    NodeType,
    compare_dinic_vs_greedy,
)
from resq.services import (
    DisruptionSpec,
    apply_disruptions,
    list_presets,
    load_preset_network,
    run_full_evacuation_analysis,
    simulate_evacuation_waves,
)


def test_presets_load_and_solve_cleanly() -> None:
    presets = list_presets()
    assert len(presets) == 4
    for preset in presets:
        net = load_preset_network(preset.key)
        assert net.validate().is_valid
        bundle = run_full_evacuation_analysis(net, trace=True, wave_hours=6)
        assert bundle.dinic_result.max_flow == bundle.min_cut.total_cut_capacity
        assert sum(route.flow for route in bundle.routes) == bundle.dinic_result.max_flow

    greedy_trap = load_preset_network("greedy_trap_benchmark")
    comp = compare_dinic_vs_greedy(greedy_trap, greedy_rule=GreedyRule.SHORTEST_HOP)
    assert comp.dinic_max_flow == 2000
    assert comp.greedy_flow == 1000


def test_apply_disruptions_does_not_mutate_base_network() -> None:
    base = load_preset_network("metro_flood_baseline")
    orig_cap = base.get_road("R_J1_J4").capacity
    orig_pop = base.get_node("A1").population

    disruption = DisruptionSpec(
        disabled_roads=frozenset({"R_J1_J4"}),
        road_capacity_factors={"R_J2_J4": 0.5},
        disabled_shelters=frozenset({"S3"}),
        demand_multipliers={"A1": 1.2},
    )
    sim_net = apply_disruptions(base, disruption)

    assert base.get_road("R_J1_J4").is_active is True
    assert base.get_road("R_J1_J4").capacity == orig_cap
    assert base.get_node("A1").population == orig_pop
    assert base.get_node("S3").shelter_capacity == 900

    assert sim_net.get_road("R_J1_J4").is_active is False
    assert sim_net.get_road("R_J2_J4").capacity == 225
    assert sim_net.get_node("S3").shelter_capacity == 0
    assert sim_net.get_node("A1").population == int(round(orig_pop * 1.2))


def test_wave_simulation_clears_demand_across_hours() -> None:
    net = EvacuationNetwork(network_id="wave-test", name="Wave Test")
    net.add_node("A1", "Zone A", NodeType.AFFECTED_AREA, population=900)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=1000)
    net.add_road("R1", "A1", "S1", 300)

    timeline = simulate_evacuation_waves(net, max_hours=5)
    assert len(timeline) == 5
    assert timeline[0].evacuated_this_hour == 300
    assert timeline[1].cumulative_evacuated == 600
    assert timeline[2].cumulative_evacuated == 900
    assert timeline[2].remaining_population == 0
    assert timeline[2].completion_pct == pytest.approx(100.0)
    assert timeline[3].evacuated_this_hour == 0


def test_path_decomposition_and_upgrade_sensitivity_accuracy(
    sample_evacuation_network: EvacuationNetwork,
) -> None:
    # Constrain R1 and R3 so clear road bottlenecks appear
    constrained = sample_evacuation_network.copy()
    constrained.edit_road("R1", capacity=200)
    constrained.edit_road("R3", capacity=250)

    bundle = run_full_evacuation_analysis(constrained, upgrade_delta=100)
    assert sum(r.flow for r in bundle.routes) == bundle.dinic_result.max_flow

    # Every upgrade candidate's marginal gain must match actual re-solved max flow
    assert len(bundle.upgrade_candidates) > 0
    for cand in bundle.upgrade_candidates:
        assert cand.new_max_flow - cand.base_max_flow == cand.marginal_flow_gain
        assert cand.marginal_flow_gain >= 0


def test_report_generation_and_plotly_network_figures() -> None:
    from resq.services import (
        build_min_cut_dataframe,
        build_road_flows_dataframe,
        build_routes_dataframe,
        build_shelters_dataframe,
        build_sources_dataframe,
        generate_html_report,
        generate_markdown_report,
    )
    from resq.ui.components import build_network_figure

    net = load_preset_network("metro_flood_baseline")
    bundle = run_full_evacuation_analysis(net, trace=True, wave_hours=6)
    comp = compare_dinic_vs_greedy(net, greedy_rule=GreedyRule.SHORTEST_HOP)

    assert len(build_road_flows_dataframe(bundle)) == len(net.roads)
    assert len(build_sources_dataframe(bundle)) == len(net.affected_areas)
    assert len(build_shelters_dataframe(bundle)) == len(net.shelters)
    assert not build_routes_dataframe(bundle).empty
    assert not build_min_cut_dataframe(bundle).empty

    md = generate_markdown_report(bundle, comp)
    html_out = generate_html_report(bundle, comp)
    assert "Metro River Basin Flood" in md
    assert "Dinic vs. Greedy" in md
    assert "<!DOCTYPE html>" in html_out

    for mode in ("topology", "flow", "min_cut", "diff"):
        fig = build_network_figure(net, bundle=bundle, mode=mode, comparison=comp)
        assert len(fig.data) > 0


def test_playback_frames_match_dinic_and_render_plotly_styles() -> None:
    from resq.services import build_playback_frames
    from resq.ui.components import build_network_figure

    # Use greedy_trap_benchmark which specifically triggers Dinic reverse-edge rerouting
    net = load_preset_network("greedy_trap_benchmark")
    bundle = run_full_evacuation_analysis(net, trace=True)
    frames = build_playback_frames(net, bundle.dinic_result)

    assert len(frames) == bundle.dinic_result.useful_augmentations + 1
    assert frames[0].step_index == 0
    assert frames[0].cumulative_flow == 0
    assert all(v == 0 for v in frames[0].road_flows.values())

    # Every intermediate frame obeys road capacity bounds
    for frame in frames:
        for rid, flw in frame.road_flows.items():
            assert 0 <= flw <= net.get_road(rid).effective_capacity
            assert frame.road_remaining[rid] == net.get_road(rid).effective_capacity - flw

    # At least one step must show reverse rerouting on R_J1_J4
    assert any("R_J1_J4" in frame.rerouted_road_ids for frame in frames)

    # Final playback frame must exactly match DinicResult
    final = frames[-1]
    assert final.cumulative_flow == bundle.dinic_result.max_flow == 2000
    for rid, detail in bundle.dinic_result.road_flows.items():
        assert final.road_flows[rid] == detail.flow
        assert final.road_remaining[rid] == detail.remaining_capacity
    for aid, src_detail in bundle.dinic_result.source_evacuations.items():
        assert final.source_evacuated[aid] == src_detail.evacuated
    for sid, shl_detail in bundle.dinic_result.shelter_intakes.items():
        assert final.shelter_assigned[sid] == shl_detail.assigned_flow

    # Verify Plotly playback figure and node/road legend styles
    pb_fig = build_network_figure(
        net,
        bundle=bundle,
        mode="playback",
        playback_frame=frames[1],
    )
    legend_names = {trace.name for trace in pb_fig.data if trace.showlegend}
    assert {"Affected Area", "Junction", "Shelter", "Normal Road", "Active Step Path"} <= legend_names

    # Verify required node colors: Red for Affected Area, Blue for Junction, Green for Shelter
    node_colors = {
        trace.name: trace.marker.color
        for trace in pb_fig.data
        if trace.name in ("Affected Area", "Junction", "Shelter")
    }
    assert node_colors["Affected Area"] == "#EF4444"
    assert node_colors["Junction"] == "#3B82F6"
    assert node_colors["Shelter"] == "#22C55E"


def test_zero_flow_and_long_id_reports_generate_cleanly() -> None:
    from resq.services import generate_html_report, generate_pdf_report

    net = EvacuationNetwork(
        network_id="edge/case:zero-flow",
        name="Zero Flow & Long ID Test",
    )
    net.add_node("AREA_ZERO_POP_LONG", "Zero Pop Source", NodeType.AFFECTED_AREA, population=0)
    net.add_node("SHELTER_LONG_NAME_ID", "Long Standby Shelter", NodeType.SHELTER, shelter_capacity=0)
    net.add_road("VERY_LONG_CORRIDOR_IDENTIFIER_01", "AREA_ZERO_POP_LONG", "SHELTER_LONG_NAME_ID", 0, distance=0.0)

    bundle = run_full_evacuation_analysis(net, trace=True, wave_hours=3)
    html_out = generate_html_report(bundle)
    assert "Source Demand Limit" in html_out
    assert "Empty DataFrame" not in html_out

    pdf_bytes = generate_pdf_report(bundle)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # Zero-road valid topology -> HTML report handles empty road table gracefully
    no_roads_net = EvacuationNetwork(network_id="no-roads", name="No Roads Graph")
    no_roads_net.add_node("A1", "Isolated Area", NodeType.AFFECTED_AREA, population=50)
    no_roads_net.add_node("S1", "Isolated Shelter", NodeType.SHELTER, shelter_capacity=50)
    no_roads_bundle = run_full_evacuation_analysis(no_roads_net, trace=False, wave_hours=2)
    no_roads_html = generate_html_report(no_roads_bundle)
    assert "No directed road corridors present in this network." in no_roads_html
    assert "Empty DataFrame" not in no_roads_html
