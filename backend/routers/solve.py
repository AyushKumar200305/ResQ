"""Algorithmic solver endpoints: Dinic max-flow, minimum-cut, full analysis, and playback."""

from fastapi import APIRouter, HTTPException, Query

from resq.algorithms.dinic import DinicSolver, solve_max_flow_dinic
from resq.algorithms.flow_builder import build_evacuation_network
from resq.algorithms.min_cut import MinCutExtractor
from resq.domain.exceptions import GraphValidationError
from resq.services.evacuation_simulator import (
    run_full_evacuation_analysis,
    simulate_evacuation_waves,
)
from resq.services.playback import build_playback_frames

from backend.mappers import (
    bundle_to_response,
    dinic_to_response,
    min_cut_to_response,
)
from backend.schemas.analysis import (
    DinicResponse,
    FullAnalysisResponse,
    MinCutResponse,
    PlaybackFrameSchema,
    PlaybackResponse,
    WaveStepSchema,
)
from backend.state import state_manager

router = APIRouter(prefix="/api/solve", tags=["DAA Solvers"])


@router.post("/dinic", response_model=DinicResponse, summary="Execute Dinic's Maximum Flow")
def run_dinic(
    trace: bool = Query(default=True, description="Record BFS levels and DFS augmentations"),
) -> DinicResponse:
    """Run Dinic's algorithm (O(V^2 E)) on the active evacuation network."""
    net = state_manager.get_network(make_copy=True)
    try:
        result = solve_max_flow_dinic(net, trace=trace)
        return dinic_to_response(result)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dinic", response_model=DinicResponse, summary="Get latest or compute Dinic flow results")
def get_dinic_results() -> DinicResponse:
    """Retrieve cached Dinic flow results, computing them if not already in cache."""
    bundle = state_manager.get_bundle()
    if bundle is not None:
        return dinic_to_response(bundle.dinic_result)
    net = state_manager.get_network(make_copy=True)
    try:
        result = solve_max_flow_dinic(net, trace=True)
        return dinic_to_response(result)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mincut", response_model=MinCutResponse, summary="Extract S*-T* Minimum Cut")
def run_min_cut() -> MinCutResponse:
    """Extract exact minimum cut partition via BFS reachability in the residual network."""
    net = state_manager.get_network(make_copy=True)
    try:
        flow_net = build_evacuation_network(net)
        dinic_res = DinicSolver().solve(
            flow_net,
            domain_network=net,
            trace=False,
            verify_invariants=True,
        )
        min_cut = MinCutExtractor().extract(
            flow_net,
            domain_network=net,
            expected_max_flow=dinic_res.max_flow,
        )
        return min_cut_to_response(min_cut)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mincut", response_model=MinCutResponse, summary="Get latest or compute Minimum Cut")
def get_min_cut_results() -> MinCutResponse:
    """Retrieve cached Minimum Cut results, computing if necessary."""
    bundle = state_manager.get_bundle()
    if bundle is not None:
        return min_cut_to_response(bundle.min_cut)
    return run_min_cut()


@router.post("/full", response_model=FullAnalysisResponse, summary="Run complete evacuation diagnostics")
def run_full_analysis(
    wave_hours: int = Query(default=8, ge=1, le=48, description="Multi-hour wave projection horizon"),
    upgrade_delta: int = Query(default=100, ge=1, description="Capacity increment for sensitivity ROI"),
) -> FullAnalysisResponse:
    """Execute full diagnostic bundle: Dinic flow, MinCut, path decomposition, waves, and upgrade ROI."""
    net = state_manager.get_network(make_copy=True)
    try:
        bundle = run_full_evacuation_analysis(
            net,
            trace=True,
            wave_hours=wave_hours,
            upgrade_delta=upgrade_delta,
        )
        state_manager.set_bundle(bundle)
        return bundle_to_response(bundle)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/trace", summary="Get detailed algorithm execution trace")
def get_algorithm_trace() -> dict[str, object]:
    """Retrieve detailed step-by-step algorithmic trace (BFS levels and DFS augmentations)."""
    net = state_manager.get_network(make_copy=True)
    try:
        result = solve_max_flow_dinic(net, trace=True)
        if not result.trace:
            return {"phases": [], "total_phases": 0, "total_augmentations": 0}

        phases_data = []
        for phase in result.trace.phases:
            aug_list = [
                {
                    "step_index": a.step_index,
                    "phase_index": a.phase_index,
                    "flow_sent": a.flow_sent,
                    "selected_path": list(a.selected_path),
                    "path_edge_labels": list(a.path_edge_labels),
                    "rerouted_via_reverse_edge": a.rerouted_via_reverse_edge,
                }
                for a in phase.augmentations
            ]
            phases_data.append(
                {
                    "phase_index": phase.phase_index,
                    "sink_level": phase.sink_level,
                    "node_levels": dict(phase.node_levels),
                    "phase_flow": phase.phase_flow_pushed,
                    "augmentations": aug_list,
                }
            )

        return {
            "algorithm": "Dinic's Maximum Flow Algorithm",
            "time_complexity": "O(V^2 E)",
            "total_phases": len(result.trace.phases),
            "total_augmentations": result.trace.total_augmentations,
            "max_flow": result.max_flow,
            "phases": phases_data,
        }
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playback", response_model=PlaybackResponse, summary="Build frame-by-frame animation state")
def get_playback_frames() -> PlaybackResponse:
    """Generate discrete animation frames from Dinic's real execution trace for step-by-step playback."""
    net = state_manager.get_network(make_copy=True)
    try:
        frames = build_playback_frames(net)
        dinic_res = solve_max_flow_dinic(net, trace=True)
        assert dinic_res.trace is not None

        converted_frames = [
            PlaybackFrameSchema(
                step_index=f.step_index,
                total_steps=f.total_steps,
                phase_index=f.phase_index,
                bfs_sink_level=f.bfs_sink_level,
                bfs_node_levels=dict(f.bfs_node_levels),
                active_path_nodes=list(f.active_path_nodes),
                active_road_ids=list(f.active_road_ids),
                rerouted_road_ids=list(f.rerouted_road_ids),
                flow_sent_this_step=f.flow_sent_this_step,
                cumulative_flow=f.cumulative_flow,
                road_flows=dict(f.road_flows),
                road_remaining=dict(f.road_remaining),
                source_evacuated=dict(f.source_evacuated),
                shelter_assigned=dict(f.shelter_assigned),
                explanation=f.explanation,
            )
            for f in frames
        ]

        return PlaybackResponse(
            total_frames=len(converted_frames),
            max_flow=dinic_res.max_flow,
            bfs_phases=dinic_res.bfs_phases,
            total_augmentations=dinic_res.useful_augmentations,
            frames=converted_frames,
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/waves", response_model=list[WaveStepSchema], summary="Simulate multi-hour evacuation waves")
def get_wave_simulation(
    hours: int = Query(default=12, ge=1, le=48, description="Number of simulation hours"),
) -> list[WaveStepSchema]:
    """Calculate hour-by-hour population clearance and shelter occupancy over time."""
    net = state_manager.get_network(make_copy=True)
    try:
        timeline = simulate_evacuation_waves(net, max_hours=hours)
        return [
            WaveStepSchema(
                hour=w.hour,
                evacuated_this_hour=w.evacuated_this_hour,
                cumulative_evacuated=w.cumulative_evacuated,
                remaining_population=w.remaining_population,
                remaining_shelter_capacity=w.remaining_shelter_capacity,
                completion_pct=w.completion_pct,
            )
            for w in timeline
        ]
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
