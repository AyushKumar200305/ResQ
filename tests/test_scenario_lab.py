"""Unit tests for Scenario Lab 5-scenario evaluations and rule-based observations."""

import pytest

from resq import EvacuationNetwork, GraphValidationError, NodeType
from resq.services import (
    build_scenario_lab_comparison_dataframe,
    evaluate_baseline_scenario,
    evaluate_increased_shelter_scenario,
    evaluate_multiple_road_failures_scenario,
    evaluate_reduced_shelter_scenario,
    evaluate_road_closure_scenario,
    load_preset_network,
)


def test_scenarios_1_to_5_preserve_original_and_compute_accurate_deltas() -> None:
    base = load_preset_network("metro_flood_baseline")
    before_dict = base.to_dict()

    # Scenario 1: Baseline
    s1 = evaluate_baseline_scenario(base)
    assert s1.bundle.dinic_result.max_flow == 2250
    assert s1.baseline_delta == 0

    # Scenario 2: Road closure on min-cut bridge R_J1_J4 (cap 750)
    s2 = evaluate_road_closure_scenario(base, s1, road_id="R_J1_J4")
    assert s2.network.get_road("R_J1_J4").capacity == 0
    assert s2.network.get_road("R_J1_J4").is_active is False
    assert s2.bundle.dinic_result.max_flow < s1.bundle.dinic_result.max_flow
    assert s2.baseline_delta < 0
    assert any("Closing Road R_J1_J4 reduced" in obs for obs in s2.observations)

    # Scenario 3: Reduced shelter capacity making S1 a limiting factor
    s3 = evaluate_reduced_shelter_scenario(base, s1, shelter_id="S1", new_capacity=200)
    assert s3.network.get_node("S1").shelter_capacity == 200
    assert any(e.edge_id == "S1" for e in s3.bundle.min_cut.shelter_capacity_cuts)
    assert s3.baseline_delta < 0
    assert any("limiting factor" in obs for obs in s3.observations)

    # Scenario 4: Increasing shelter S1 on a road-bottlenecked network produces 0 gain
    s4 = evaluate_increased_shelter_scenario(base, s1, shelter_id="S1", added_capacity=500)
    assert s4.network.get_node("S1").shelter_capacity == 1800
    assert s4.baseline_delta == 0
    assert any("did not improve total flow" in obs for obs in s4.observations)

    # Scenario 5: Multiple simultaneous road failures severing all cross-river bridges
    s5 = evaluate_multiple_road_failures_scenario(
        base,
        s1,
        road_ids=["R_J1_J4", "R_J2_J4", "R_J2_J5", "R_J3_J5"],
    )
    assert s5.bundle.dinic_result.max_flow == 0
    assert s5.baseline_delta == -2250
    assert any("severed all source-to-shelter paths" in obs for obs in s5.observations)

    # Original network must remain untouched
    assert base.to_dict() == before_dict

    # Comparison DataFrame columns match Prompt 7 spec
    df = build_scenario_lab_comparison_dataframe([s1, s2, s3, s4, s5])
    assert list(df.columns) == [
        "Scenario Name",
        "Maximum Flow",
        "People Left Unallocated",
        "Evacuation Percentage",
        "Minimum Cut Capacity",
        "Number of Bottleneck Roads",
        "Change from Baseline",
    ]
    assert len(df) == 5


def test_scenario_4_improves_flow_when_shelter_was_the_bottleneck() -> None:
    net = EvacuationNetwork(network_id="shelter-bound", name="Shelter-Bound Grid")
    net.add_node("A1", "Zone 1", NodeType.AFFECTED_AREA, population=500)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=200)
    net.add_road("R1", "A1", "S1", 500)

    s1 = evaluate_baseline_scenario(net)
    assert s1.bundle.dinic_result.max_flow == 200

    s4 = evaluate_increased_shelter_scenario(net, s1, shelter_id="S1", added_capacity=150)
    assert s4.bundle.dinic_result.max_flow == 350
    assert s4.baseline_delta == 150
    assert any("improved maximum evacuation flow by +150" in obs for obs in s4.observations)


def test_scenario_validation_guards() -> None:
    base = load_preset_network("metro_flood_baseline")
    s1 = evaluate_baseline_scenario(base)

    with pytest.raises(GraphValidationError):
        evaluate_reduced_shelter_scenario(base, s1, shelter_id="S1", new_capacity=9999)

    with pytest.raises(GraphValidationError):
        evaluate_multiple_road_failures_scenario(base, s1, road_ids=[])


def test_presentation_demo_dataset_scenarios_and_invariants() -> None:
    """Validate that the Prompt 4 College Presentation Demonstration network satisfies all scenario invariants."""
    base = load_preset_network("presentation_demo_dataset")
    assert len(base.nodes) == 19
    assert len(base.roads) == 26
    assert base.total_population == 5500
    assert base.total_shelter_capacity == 5100

    # Scenario 1: Baseline
    s1 = evaluate_baseline_scenario(base)
    assert s1.bundle.dinic_result.max_flow == 4350
    assert s1.bundle.min_cut.total_cut_capacity == 4350
    assert s1.baseline_delta == 0
    assert len(s1.bundle.min_cut.road_bottlenecks) == 4
    assert any(sc.edge_id == "S3" for sc in s1.bundle.min_cut.shelter_capacity_cuts)

    # Scenario 2: Main Road Closed (North Ridgeway Bridge R_J1_J6, cap 750)
    s2 = evaluate_road_closure_scenario(base, s1, road_id="R_J1_J6")
    assert s2.bundle.dinic_result.max_flow == 3600
    assert s2.baseline_delta == -750

    # Scenario 3: Reduced Shelter Capacity (S1 reduced to 400)
    s3 = evaluate_reduced_shelter_scenario(base, s1, shelter_id="S1", new_capacity=400)
    assert s3.bundle.dinic_result.max_flow == 3950
    assert s3.baseline_delta == -400
    assert any("limiting factor" in obs for obs in s3.observations)

    # Scenario 4: Increased Shelter Capacity (S3 increased by 300)
    # S3 was saturated at 1500 in baseline, so increasing capacity improves flow
    s4 = evaluate_increased_shelter_scenario(base, s1, shelter_id="S3", added_capacity=300)
    assert s4.bundle.dinic_result.max_flow == 4450
    assert s4.baseline_delta == 100

    # Scenario 5: Multiple Road Failures (R_J1_J6 and R_J7_J10)
    s5 = evaluate_multiple_road_failures_scenario(base, s1, road_ids=["R_J1_J6", "R_J7_J10"])
    assert s5.bundle.dinic_result.max_flow == 3000
    assert s5.baseline_delta == -1350

    # Comparison DataFrame
    df = build_scenario_lab_comparison_dataframe([s1, s2, s3, s4, s5])
    assert len(df) == 5

