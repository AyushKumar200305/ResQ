"""Pydantic schemas for algorithm comparison (Dinic vs Greedy) and empirical benchmarks."""

from typing import Any
from pydantic import BaseModel, Field


class GreedyCompareRequest(BaseModel):
    """Parameters for Dinic vs Greedy comparison."""

    rule: str = Field(default="shortest_hop", description="Greedy heuristic: 'shortest_hop', 'widest_path', or 'lexicographic_dfs'")
    repeats: int = Field(default=3, ge=1, le=20, description="Repetitions for median timing calculation")


class EdgeComparisonDetailSchema(BaseModel):
    """Road-by-road flow allocation comparison."""

    edge_id: str
    source_id: str
    target_id: str
    capacity: int
    dinic_flow: int
    greedy_flow: int
    flow_delta: int


class GreedyCompareResponse(BaseModel):
    """Head-to-head comparison between Dinic and Greedy."""

    dinic_max_flow: int
    greedy_flow: int
    flow_difference: int
    optimality_gap_pct: float
    dinic_time_ms: float
    greedy_time_ms: float
    greedy_rule: str
    rule_explanation: str
    edges: list[EdgeComparisonDetailSchema]


class BenchmarkTierResultSchema(BaseModel):
    """Performance metrics on one synthetic network tier."""

    tier_name: str
    vertices: int
    edges: int
    dinic_time_ms: float
    greedy_time_ms: float
    dinic_max_flow: int
    greedy_flow: int
    speedup_ratio: float


class BenchmarkResponse(BaseModel):
    """Empirical scalability benchmark results using live time.perf_counter()."""

    total_duration_sec: float
    disclaimer: str
    tiers: list[BenchmarkTierResultSchema]
