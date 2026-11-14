"""What-If Scenario Lab simulation and comparison endpoints."""

from fastapi import APIRouter, HTTPException

from resq.domain.exceptions import EntityNotFoundError, GraphValidationError
from resq.domain.models import EvacuationNetwork
from resq.services.evacuation_simulator import (
    DisruptionSpec,
    apply_disruptions,
    run_full_evacuation_analysis,
)
from resq.services.scenario_lab import (
    ScenarioEvaluation,
    evaluate_baseline_scenario,
    evaluate_increased_shelter_scenario,
    evaluate_multiple_road_failures_scenario,
    evaluate_reduced_shelter_scenario,
    evaluate_road_closure_scenario,
    generate_scenario_observations,
)

from backend.mappers import scenario_to_response
from backend.schemas.scenarios import (
    CustomDisruptionRequest,
    IncreasedShelterRequest,
    MultiRoadFailureRequest,
    ReducedShelterRequest,
    RoadClosureRequest,
    ScenarioComparisonSummaryResponse,
    ScenarioEvaluationResponse,
)
from backend.state import state_manager


def run_all_standard_scenarios(net: EvacuationNetwork) -> list[ScenarioEvaluation]:
    """Evaluate Scenarios 1 through 5 on independent network copies."""
    base_ev = evaluate_baseline_scenario(net)
    evaluations: list[ScenarioEvaluation] = [base_ev]

    road_ids = list(net.roads.keys())
    cut_roads = [e.edge_id for e in base_ev.bundle.min_cut.road_bottlenecks]

    if road_ids:
        primary_road = cut_roads[0] if cut_roads else road_ids[0]
        s2 = evaluate_road_closure_scenario(net, base_ev, road_id=primary_road)
        evaluations.append(s2)

    shelter_nodes = net.shelters
    if shelter_nodes:
        target_shl_s3 = shelter_nodes[0]
        reduced_cap = max(0, target_shl_s3.shelter_capacity // 3)
        s3 = evaluate_reduced_shelter_scenario(
            net,
            base_ev,
            shelter_id=target_shl_s3.node_id,
            new_capacity=reduced_cap,
        )
        evaluations.append(s3)

        cut_shl_ids = [e.edge_id for e in base_ev.bundle.min_cut.shelter_capacity_cuts]
        target_shl_s4 = cut_shl_ids[0] if cut_shl_ids else shelter_nodes[0].node_id
        s4 = evaluate_increased_shelter_scenario(
            net,
            base_ev,
            shelter_id=target_shl_s4,
            added_capacity=500,
        )
        evaluations.append(s4)

    if road_ids:
        multi_pick = cut_roads[:2] if len(cut_roads) >= 2 else road_ids[:min(2, len(road_ids))]
        s5 = evaluate_multiple_road_failures_scenario(net, base_ev, road_ids=multi_pick)
        evaluations.append(s5)

    return evaluations


router = APIRouter(prefix="/api/scenarios", tags=["Scenario Lab"])


@router.post("/baseline", response_model=ScenarioEvaluationResponse, summary="Evaluate Scenario 1: Baseline")
def run_baseline_scenario() -> ScenarioEvaluationResponse:
    """Evaluate normal baseline evacuation conditions on an independent copy."""
    net = state_manager.get_network(make_copy=True)
    try:
        baseline_eval = evaluate_baseline_scenario(net)
        return scenario_to_response(baseline_eval, include_bundle=True)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/road-closure", response_model=ScenarioEvaluationResponse, summary="Evaluate Scenario 2: Road Closure")
def run_road_closure(payload: RoadClosureRequest) -> ScenarioEvaluationResponse:
    """Evaluate the impact of closing a single road corridor (capacity set to 0)."""
    net = state_manager.get_network(make_copy=True)
    try:
        baseline = evaluate_baseline_scenario(net)
        eval_res = evaluate_road_closure_scenario(
            net,
            baseline,
            road_id=payload.road_id,
            scenario_name=payload.scenario_name,
        )
        return scenario_to_response(eval_res, include_bundle=True)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reduced-shelter", response_model=ScenarioEvaluationResponse, summary="Evaluate Scenario 3: Reduced Shelter")
def run_reduced_shelter(payload: ReducedShelterRequest) -> ScenarioEvaluationResponse:
    """Evaluate reducing a shelter's intake capacity in an independent copy."""
    net = state_manager.get_network(make_copy=True)
    try:
        baseline = evaluate_baseline_scenario(net)
        eval_res = evaluate_reduced_shelter_scenario(
            net,
            baseline,
            shelter_id=payload.shelter_id,
            new_capacity=payload.new_capacity,
            scenario_name=payload.scenario_name,
        )
        return scenario_to_response(eval_res, include_bundle=True)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/increased-shelter", response_model=ScenarioEvaluationResponse, summary="Evaluate Scenario 4: Increased Shelter")
def run_increased_shelter(payload: IncreasedShelterRequest) -> ScenarioEvaluationResponse:
    """Evaluate expanding a shelter's intake capacity in an independent copy."""
    net = state_manager.get_network(make_copy=True)
    try:
        baseline = evaluate_baseline_scenario(net)
        eval_res = evaluate_increased_shelter_scenario(
            net,
            baseline,
            shelter_id=payload.shelter_id,
            added_capacity=payload.added_capacity,
            scenario_name=payload.scenario_name,
        )
        return scenario_to_response(eval_res, include_bundle=True)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/multi-road-failure", response_model=ScenarioEvaluationResponse, summary="Evaluate Scenario 5: Multiple Road Failures")
def run_multi_road_failure(payload: MultiRoadFailureRequest) -> ScenarioEvaluationResponse:
    """Evaluate simultaneously severing multiple road corridors."""
    net = state_manager.get_network(make_copy=True)
    try:
        baseline = evaluate_baseline_scenario(net)
        eval_res = evaluate_multiple_road_failures_scenario(
            net,
            baseline,
            road_ids=payload.road_ids,
            scenario_name=payload.scenario_name,
        )
        return scenario_to_response(eval_res, include_bundle=True)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/custom", response_model=ScenarioEvaluationResponse, summary="Evaluate custom disaster disruption")
def run_custom_disruption(payload: CustomDisruptionRequest) -> ScenarioEvaluationResponse:
    """Evaluate a custom combination of disabled roads, capacity drops, and surge demands."""
    net = state_manager.get_network(make_copy=True)
    try:
        baseline = evaluate_baseline_scenario(net)
        disruption = DisruptionSpec(
            disabled_roads=frozenset(payload.disabled_roads),
            road_capacity_factors=payload.road_capacity_factors,
            disabled_shelters=frozenset(payload.disabled_shelters),
            demand_multipliers=payload.demand_multipliers,
        )
        sim_net = apply_disruptions(net, disruption)
        bundle = run_full_evacuation_analysis(sim_net, trace=False)
        base_flow = baseline.bundle.dinic_result.max_flow
        delta = bundle.dinic_result.max_flow - base_flow
        delta_pct = (delta / base_flow * 100.0) if base_flow > 0 else 0.0

        obs = generate_scenario_observations(
            baseline=baseline,
            bundle=bundle,
            scenario_kind="custom",
        )
        eval_res = ScenarioEvaluation(
            scenario_key="scenario_custom",
            scenario_name=payload.scenario_name,
            scenario_kind="custom",
            description=f"Custom disruption overlay with {len(payload.disabled_roads)} severed roads.",
            network=sim_net,
            bundle=bundle,
            baseline_delta=delta,
            baseline_delta_pct=delta_pct,
            observations=obs,
        )
        return scenario_to_response(eval_res, include_bundle=True)
    except (GraphValidationError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/all", response_model=ScenarioComparisonSummaryResponse, summary="Run all 5 standard scenarios")
def run_all_scenarios() -> ScenarioComparisonSummaryResponse:
    """Simulate all 5 scenarios automatically and return side-by-side comparison table."""
    net = state_manager.get_network(make_copy=True)
    try:
        evaluations = run_all_standard_scenarios(net)
        state_manager.set_scenarios(evaluations)
        base_flow = evaluations[0].bundle.dinic_result.max_flow
        return ScenarioComparisonSummaryResponse(
            baseline_flow=base_flow,
            scenarios=[scenario_to_response(ev, include_bundle=False) for ev in evaluations],
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
