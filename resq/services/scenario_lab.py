"""Rule-based What-If Scenario Lab engine preserving the original network."""

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from resq.domain.enums import NodeType
from resq.domain.exceptions import EntityNotFoundError, GraphValidationError
from resq.domain.models import EvacuationNetwork
from resq.services.evacuation_simulator import (
    FullAnalysisBundle,
    run_full_evacuation_analysis,
)


@dataclass(frozen=True, slots=True)
class ScenarioEvaluation:
    """Complete Dinic + Min-Cut evaluation and rule-based observations for one scenario."""

    scenario_key: str
    scenario_name: str
    scenario_kind: str
    description: str
    network: EvacuationNetwork
    bundle: FullAnalysisBundle
    baseline_delta: int
    baseline_delta_pct: float
    observations: tuple[str, ...]


def generate_scenario_observations(
    *,
    baseline: ScenarioEvaluation | None,
    bundle: FullAnalysisBundle,
    scenario_kind: str,
    context: dict[str, object] | None = None,
) -> tuple[str, ...]:
    """Generate deterministic rule-based observations from actual calculated values."""
    ctx = context or {}
    d = bundle.dinic_result
    mc = bundle.min_cut
    notes: list[str] = []

    base_flow = baseline.bundle.dinic_result.max_flow if baseline is not None else d.max_flow
    base_cut_roads = (
        {e.edge_id for e in baseline.bundle.min_cut.road_bottlenecks}
        if baseline is not None
        else set()
    )
    cand_cut_roads = {e.edge_id for e in mc.road_bottlenecks}
    delta = d.max_flow - base_flow

    if scenario_kind == "baseline":
        notes.append(
            f"Baseline established: maximum evacuation flow is {d.max_flow:,} out of "
            f"{d.total_population:,} affected people ({d.evacuation_rate * 100:.1f}% completion)."
        )
    elif scenario_kind == "road_closure":
        road_id = str(ctx.get("road_id", ""))
        if delta < 0:
            notes.append(
                f"Closing Road {road_id} reduced maximum evacuation flow by {abs(delta):,} "
                f"(from {base_flow:,} to {d.max_flow:,})."
            )
        else:
            notes.append(
                f"Closing Road {road_id} did not reduce maximum evacuation flow ({d.max_flow:,}); "
                "parallel or alternate corridors absorbed the redirected flow."
            )
        new_cuts = sorted(cand_cut_roads - base_cut_roads)
        if new_cuts:
            notes.append(
                f"New limiting road bottlenecks emerged after closing {road_id}: {', '.join(new_cuts)}."
            )
    elif scenario_kind == "reduced_shelter":
        shelter_id = str(ctx.get("shelter_id", ""))
        new_cap = int(ctx.get("new_capacity", 0))  # type: ignore[arg-type]
        cut_shelter_ids = {e.edge_id for e in mc.shelter_capacity_cuts}
        is_limiting = shelter_id in cut_shelter_ids

        if is_limiting and delta < 0:
            notes.append(
                f"Reducing Shelter {shelter_id} to {new_cap:,} beds made it a limiting factor in "
                f"the minimum cut, dropping maximum flow by {abs(delta):,} (to {d.max_flow:,})."
            )
        elif is_limiting:
            notes.append(
                f"Shelter {shelter_id} is now saturated at its reduced minimum-cut limit ({new_cap:,} beds), "
                f"though total network flow remained {d.max_flow:,}."
            )
        elif delta < 0:
            notes.append(
                f"Reducing Shelter {shelter_id} to {new_cap:,} beds reduced total flow by {abs(delta):,}."
            )
        else:
            notes.append(
                f"Reducing Shelter {shelter_id} to {new_cap:,} beds did not make it a global bottleneck "
                f"(max flow remained {d.max_flow:,})."
            )
    elif scenario_kind == "increased_shelter":
        shelter_id = str(ctx.get("shelter_id", ""))
        added_cap = int(ctx.get("added_capacity", 0))  # type: ignore[arg-type]
        new_cap = int(ctx.get("new_capacity", 0))  # type: ignore[arg-type]

        if delta > 0:
            notes.append(
                f"Increasing Shelter {shelter_id} capacity by +{added_cap:,} (to {new_cap:,}) improved "
                f"maximum evacuation flow by +{delta:,} (from {base_flow:,} to {d.max_flow:,})."
            )
        elif mc.road_bottlenecks:
            road_list = ", ".join(e.edge_id for e in mc.road_bottlenecks)
            notes.append(
                f"Increasing Shelter {shelter_id} capacity to {new_cap:,} did not improve total flow "
                f"({d.max_flow:,}) because road bottlenecks remain the limiting connection ({road_list})."
            )
        elif d.unmet_demand == 0:
            notes.append(
                f"Increasing Shelter {shelter_id} capacity to {new_cap:,} did not change total flow "
                f"({d.max_flow:,}) because 100% of the affected population is already evacuated."
            )
        else:
            notes.append(
                f"Increasing Shelter {shelter_id} capacity to {new_cap:,} did not improve total flow "
                f"({d.max_flow:,}) due to downstream corridor or sibling-shelter constraints."
            )
    elif scenario_kind == "multi_road_failure":
        road_ids = [str(r) for r in ctx.get("road_ids", ())]  # type: ignore[attr-defined]
        joined = ", ".join(road_ids)
        if d.max_flow == 0 and d.total_population > 0:
            notes.append(
                f"Closing roads ({joined}) simultaneously severed all source-to-shelter paths, "
                "reducing maximum evacuation flow to 0."
            )
        elif delta < 0:
            notes.append(
                f"Simultaneously closing {len(road_ids)} roads ({joined}) reduced maximum evacuation "
                f"flow by {abs(delta):,} (from {base_flow:,} to {d.max_flow:,})."
            )
        else:
            notes.append(
                f"Simultaneously closing {len(road_ids)} roads ({joined}) did not reduce total flow "
                f"({d.max_flow:,}); redundant paths maintained throughput."
            )

    if d.unmet_demand > 0:
        notes.append(
            f"The network has insufficient capacity to evacuate the entire affected population "
            f"({d.unmet_demand:,} people remain unallocated)."
        )
    else:
        notes.append(
            f"All {d.total_population:,} affected people can be fully evacuated."
        )

    return tuple(notes)


def evaluate_baseline_scenario(base_network: EvacuationNetwork) -> ScenarioEvaluation:
    """Scenario 1: Evaluate the unmodified base network as baseline without mutating it."""
    snapshot = base_network.copy(
        new_network_id=f"{base_network.network_id}-baseline",
        new_name="Scenario 1: Normal Conditions (Baseline)",
    )
    bundle = run_full_evacuation_analysis(snapshot, trace=False, wave_hours=8, upgrade_delta=100)
    observations = generate_scenario_observations(
        baseline=None,
        bundle=bundle,
        scenario_kind="baseline",
    )
    return ScenarioEvaluation(
        scenario_key="scenario_1_baseline",
        scenario_name="Scenario 1: Normal Conditions (Baseline)",
        scenario_kind="baseline",
        description="Original unperturbed road capacities and shelter intakes.",
        network=snapshot,
        bundle=bundle,
        baseline_delta=0,
        baseline_delta_pct=0.0,
        observations=observations,
    )


def evaluate_road_closure_scenario(
    base_network: EvacuationNetwork,
    baseline: ScenarioEvaluation,
    *,
    road_id: str,
    scenario_name: str | None = None,
) -> ScenarioEvaluation:
    """Scenario 2: Close a single road by setting its capacity to 0 in an independent copy."""
    if road_id not in base_network.roads:
        raise EntityNotFoundError(f"Road '{road_id}' does not exist in network.")

    copy_net = base_network.copy(
        new_network_id=f"{base_network.network_id}-close-{road_id}",
        new_name=scenario_name or f"Scenario 2: Road Closure ({road_id})",
    )
    copy_net.edit_road(road_id, capacity=0, is_active=False)

    bundle = run_full_evacuation_analysis(copy_net, trace=False, wave_hours=8, upgrade_delta=100)
    base_flow = baseline.bundle.dinic_result.max_flow
    delta = bundle.dinic_result.max_flow - base_flow
    delta_pct = (delta / base_flow * 100.0) if base_flow > 0 else 0.0

    observations = generate_scenario_observations(
        baseline=baseline,
        bundle=bundle,
        scenario_kind="road_closure",
        context={"road_id": road_id},
    )
    orig_road = base_network.get_road(road_id)
    return ScenarioEvaluation(
        scenario_key="scenario_2_road_closure",
        scenario_name=copy_net.name,
        scenario_kind="road_closure",
        description=(
            f"Closed Road {road_id} ({orig_road.source_id} -> {orig_road.target_id}, "
            f"original cap {orig_road.capacity:,}) by setting capacity to 0."
        ),
        network=copy_net,
        bundle=bundle,
        baseline_delta=delta,
        baseline_delta_pct=delta_pct,
        observations=observations,
    )


def evaluate_reduced_shelter_scenario(
    base_network: EvacuationNetwork,
    baseline: ScenarioEvaluation,
    *,
    shelter_id: str,
    new_capacity: int,
    scenario_name: str | None = None,
) -> ScenarioEvaluation:
    """Scenario 3: Reduce a selected shelter's capacity in an independent copy."""
    if shelter_id not in base_network.nodes:
        raise EntityNotFoundError(f"Shelter '{shelter_id}' does not exist in network.")
    orig_node = base_network.get_node(shelter_id)
    if orig_node.node_type != NodeType.SHELTER:
        raise GraphValidationError(f"Node '{shelter_id}' is not a shelter.")
    if isinstance(new_capacity, bool) or not isinstance(new_capacity, int) or new_capacity < 0:
        raise GraphValidationError(
            f"new_capacity must be a non-negative integer, got {new_capacity!r}."
        )
    if new_capacity > orig_node.shelter_capacity:
        raise GraphValidationError(
            f"Reduced shelter capacity ({new_capacity}) cannot exceed original capacity "
            f"({orig_node.shelter_capacity})."
        )

    copy_net = base_network.copy(
        new_network_id=f"{base_network.network_id}-red-{shelter_id}",
        new_name=scenario_name or f"Scenario 3: Reduced Shelter ({shelter_id})",
    )
    copy_net.edit_node(shelter_id, shelter_capacity=new_capacity)

    bundle = run_full_evacuation_analysis(copy_net, trace=False, wave_hours=8, upgrade_delta=100)
    base_flow = baseline.bundle.dinic_result.max_flow
    delta = bundle.dinic_result.max_flow - base_flow
    delta_pct = (delta / base_flow * 100.0) if base_flow > 0 else 0.0

    observations = generate_scenario_observations(
        baseline=baseline,
        bundle=bundle,
        scenario_kind="reduced_shelter",
        context={"shelter_id": shelter_id, "new_capacity": new_capacity},
    )
    return ScenarioEvaluation(
        scenario_key="scenario_3_reduced_shelter",
        scenario_name=copy_net.name,
        scenario_kind="reduced_shelter",
        description=(
            f"Reduced Shelter {shelter_id} ({orig_node.name}) capacity from "
            f"{orig_node.shelter_capacity:,} to {new_capacity:,}."
        ),
        network=copy_net,
        bundle=bundle,
        baseline_delta=delta,
        baseline_delta_pct=delta_pct,
        observations=observations,
    )


def evaluate_increased_shelter_scenario(
    base_network: EvacuationNetwork,
    baseline: ScenarioEvaluation,
    *,
    shelter_id: str,
    added_capacity: int,
    scenario_name: str | None = None,
) -> ScenarioEvaluation:
    """Scenario 4: Increase a selected shelter's capacity in an independent copy."""
    if shelter_id not in base_network.nodes:
        raise EntityNotFoundError(f"Shelter '{shelter_id}' does not exist in network.")
    orig_node = base_network.get_node(shelter_id)
    if orig_node.node_type != NodeType.SHELTER:
        raise GraphValidationError(f"Node '{shelter_id}' is not a shelter.")
    if isinstance(added_cap := added_capacity, bool) or not isinstance(added_cap, int) or added_cap < 1:
        raise GraphValidationError(
            f"added_capacity must be an integer >= 1, got {added_capacity!r}."
        )

    new_cap = orig_node.shelter_capacity + added_cap
    copy_net = base_network.copy(
        new_network_id=f"{base_network.network_id}-inc-{shelter_id}",
        new_name=scenario_name or f"Scenario 4: Increased Shelter ({shelter_id})",
    )
    copy_net.edit_node(shelter_id, shelter_capacity=new_cap)

    bundle = run_full_evacuation_analysis(copy_net, trace=False, wave_hours=8, upgrade_delta=100)
    base_flow = baseline.bundle.dinic_result.max_flow
    delta = bundle.dinic_result.max_flow - base_flow
    delta_pct = (delta / base_flow * 100.0) if base_flow > 0 else 0.0

    observations = generate_scenario_observations(
        baseline=baseline,
        bundle=bundle,
        scenario_kind="increased_shelter",
        context={
            "shelter_id": shelter_id,
            "added_capacity": added_cap,
            "new_capacity": new_cap,
        },
    )
    return ScenarioEvaluation(
        scenario_key="scenario_4_increased_shelter",
        scenario_name=copy_net.name,
        scenario_kind="increased_shelter",
        description=(
            f"Increased Shelter {shelter_id} ({orig_node.name}) capacity by +{added_cap:,} "
            f"(from {orig_node.shelter_capacity:,} to {new_cap:,})."
        ),
        network=copy_net,
        bundle=bundle,
        baseline_delta=delta,
        baseline_delta_pct=delta_pct,
        observations=observations,
    )


def evaluate_multiple_road_failures_scenario(
    base_network: EvacuationNetwork,
    baseline: ScenarioEvaluation,
    *,
    road_ids: Sequence[str],
    scenario_name: str | None = None,
) -> ScenarioEvaluation:
    """Scenario 5: Close multiple roads simultaneously (capacity = 0) in an independent copy."""
    clean_ids = list(dict.fromkeys(road_ids))
    if not clean_ids:
        raise GraphValidationError("Select at least one road for multiple road failures.")
    for rid in clean_ids:
        if rid not in base_network.roads:
            raise EntityNotFoundError(f"Road '{rid}' does not exist in network.")

    copy_net = base_network.copy(
        new_network_id=f"{base_network.network_id}-multi-fail",
        new_name=scenario_name or f"Scenario 5: Multiple Road Failures ({len(clean_ids)})",
    )
    for rid in clean_ids:
        copy_net.edit_road(rid, capacity=0, is_active=False)

    bundle = run_full_evacuation_analysis(copy_net, trace=False, wave_hours=8, upgrade_delta=100)
    base_flow = baseline.bundle.dinic_result.max_flow
    delta = bundle.dinic_result.max_flow - base_flow
    delta_pct = (delta / base_flow * 100.0) if base_flow > 0 else 0.0

    observations = generate_scenario_observations(
        baseline=baseline,
        bundle=bundle,
        scenario_kind="multi_road_failure",
        context={"road_ids": tuple(clean_ids)},
    )
    return ScenarioEvaluation(
        scenario_key="scenario_5_multi_failure",
        scenario_name=copy_net.name,
        scenario_kind="multi_road_failure",
        description=f"Simultaneously closed roads: {', '.join(clean_ids)} (capacity set to 0).",
        network=copy_net,
        bundle=bundle,
        baseline_delta=delta,
        baseline_delta_pct=delta_pct,
        observations=observations,
    )


def build_scenario_lab_comparison_dataframe(
    evaluations: Sequence[ScenarioEvaluation],
) -> pd.DataFrame:
    """Build the standardized Prompt 7 comparison table across evaluated scenarios."""
    rows = []
    for ev in evaluations:
        d = ev.bundle.dinic_result
        mc = ev.bundle.min_cut
        if ev.scenario_kind == "baseline":
            change_str = "Baseline (0)"
        else:
            change_str = f"{ev.baseline_delta:+,} ({ev.baseline_delta_pct:+.1f}%)"

        rows.append(
            {
                "Scenario Name": ev.scenario_name,
                "Maximum Flow": d.max_flow,
                "People Left Unallocated": d.unmet_demand,
                "Evacuation Percentage": round(d.evacuation_rate * 100.0, 1),
                "Minimum Cut Capacity": mc.total_cut_capacity,
                "Number of Bottleneck Roads": len(mc.road_bottlenecks),
                "Change from Baseline": change_str,
            }
        )
    return pd.DataFrame(rows)
