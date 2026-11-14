"""Algorithm comparison (Dinic vs Greedy) and performance benchmarking endpoints."""

import time
from fastapi import APIRouter, HTTPException, Query

from resq.domain.enums import GreedyRule
from resq.domain.exceptions import GraphValidationError
from resq.services.benchmark import (
    DEFAULT_SCALABILITY_TIERS,
    run_scalability_benchmark,
)
from resq.services.comparator import compare_dinic_vs_greedy

from backend.schemas.comparison import (
    BenchmarkResponse,
    BenchmarkTierResultSchema,
    EdgeComparisonDetailSchema,
    GreedyCompareRequest,
    GreedyCompareResponse,
)
from backend.state import state_manager

router = APIRouter(prefix="/api/comparison", tags=["Algorithm Comparison"])


@router.post("/greedy", response_model=GreedyCompareResponse, summary="Compare Dinic against Greedy Baseline")
def compare_greedy(payload: GreedyCompareRequest) -> GreedyCompareResponse:
    """Run head-to-head evaluation between Dinic's Maximum Flow and a Greedy heuristic."""
    net = state_manager.get_network(make_copy=True)
    try:
        res = compare_dinic_vs_greedy(
            net,
            greedy_rule=payload.rule,
            repeats=payload.repeats,
            trace=False,
        )
        state_manager.set_comparison(res)

        edge_schemas = [
            EdgeComparisonDetailSchema(
                edge_id=e.road_id,
                source_id=e.source_id,
                target_id=e.target_id,
                capacity=e.capacity,
                dinic_flow=e.dinic_flow,
                greedy_flow=e.greedy_flow,
                flow_delta=e.flow_difference,
            )
            for e in res.road_comparisons
        ]

        return GreedyCompareResponse(
            dinic_max_flow=res.dinic_max_flow,
            greedy_flow=res.greedy_flow,
            flow_difference=res.flow_difference,
            optimality_gap_pct=res.optimality_gap_pct,
            dinic_time_ms=res.dinic_time_ms,
            greedy_time_ms=res.greedy_time_ms,
            greedy_rule=res.greedy_result.rule,
            rule_explanation=res.rule_explanation,
            edges=edge_schemas,
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/benchmark", response_model=BenchmarkResponse, summary="Run live empirical scalability benchmark")
def run_benchmark(
    rule: str = Query(default="shortest_hop", description="Greedy heuristic to benchmark"),
    repeats: int = Query(default=3, ge=1, le=10, description="Timing iterations per tier"),
) -> BenchmarkResponse:
    """Measure Dinic vs Greedy execution times using time.perf_counter() across graph sizes (XS to XL)."""
    try:
        start_wall = time.perf_counter()
        report = run_scalability_benchmark(
            tiers=DEFAULT_SCALABILITY_TIERS,
            greedy_rule=rule,
            repeats=repeats,
        )
        total_time = round(time.perf_counter() - start_wall, 3)

        tier_schemas = [
            BenchmarkTierResultSchema(
                tier_name=row.tier_label,
                vertices=row.num_vertices,
                edges=row.num_edges,
                dinic_time_ms=round(row.dinic_time_ms, 4),
                greedy_time_ms=round(row.greedy_time_ms, 4),
                dinic_max_flow=row.dinic_max_flow,
                greedy_flow=row.greedy_flow,
                speedup_ratio=round(row.greedy_time_ms / max(1e-9, row.dinic_time_ms), 2),
            )
            for row in report.rows
        ]

        return BenchmarkResponse(
            total_duration_sec=total_time,
            disclaimer=report.disclaimer,
            tiers=tier_schemas,
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
