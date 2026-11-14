"""Scalability and runtime performance benchmarking across varying network sizes."""

from dataclasses import dataclass
import platform
import random
import time
from typing import Sequence

import pandas as pd

from resq.algorithms.dinic import DinicSolver
from resq.algorithms.flow_builder import build_evacuation_network
from resq.algorithms.greedy import GreedySolver
from resq.domain.enums import GreedyRule, NodeType
from resq.domain.exceptions import GraphValidationError
from resq.domain.models import EvacuationNetwork


@dataclass(frozen=True, slots=True)
class ScalabilityTierSpec:
    """Topology size specification for synthetic scalability benchmarking."""

    label: str
    num_sources: int
    junction_layers: int
    junctions_per_layer: int
    num_shelters: int
    cross_links_per_layer: int


DEFAULT_SCALABILITY_TIERS: tuple[ScalabilityTierSpec, ...] = (
    ScalabilityTierSpec("XS (12V)", 2, 2, 4, 2, 2),
    ScalabilityTierSpec("S (28V)", 3, 3, 7, 4, 5),
    ScalabilityTierSpec("M (56V)", 4, 4, 12, 4, 10),
    ScalabilityTierSpec("L (104V)", 6, 6, 15, 8, 16),
    ScalabilityTierSpec("XL (180V)", 8, 8, 20, 12, 24),
)


@dataclass(frozen=True, slots=True)
class PerformanceBenchmarkRow:
    """Measured runtime and flow results for one generated network size."""

    tier_label: str
    num_vertices: int
    num_edges: int
    augmented_vertices: int
    augmented_edges: int
    dinic_time_ms: float
    greedy_time_ms: float
    dinic_max_flow: int
    greedy_flow: int
    flow_gap: int


@dataclass(frozen=True, slots=True)
class ScalabilityBenchmarkReport:
    """Complete multi-size benchmark results measured via time.perf_counter()."""

    greedy_rule: str
    repeats: int
    rows: tuple[PerformanceBenchmarkRow, ...]
    disclaimer: str


def generate_benchmark_network(
    spec: ScalabilityTierSpec,
    *,
    seed: int = 42,
) -> EvacuationNetwork:
    """Deterministically generate a layered multi-source/shelter benchmark graph."""
    rng = random.Random(seed)
    net = EvacuationNetwork(
        network_id=f"bench-{spec.label.lower().replace(' ', '-')}",
        name=f"Benchmark Grid ({spec.label})",
    )

    sources: list[str] = []
    for i in range(spec.num_sources):
        nid = f"SRC_{i}"
        net.add_node(
            nid,
            f"Area {i}",
            NodeType.AFFECTED_AREA,
            population=rng.randint(400, 1000),
        )
        sources.append(nid)

    layers: list[list[str]] = []
    for l_idx in range(spec.junction_layers):
        layer_nodes: list[str] = []
        for j_idx in range(spec.junctions_per_layer):
            nid = f"J_{l_idx}_{j_idx}"
            net.add_node(nid, nid, NodeType.JUNCTION)
            layer_nodes.append(nid)
        layers.append(layer_nodes)

    shelters: list[str] = []
    for i in range(spec.num_shelters):
        nid = f"SHL_{i}"
        net.add_node(
            nid,
            f"Shelter {i}",
            NodeType.SHELTER,
            shelter_capacity=rng.randint(450, 1100),
        )
        shelters.append(nid)

    road_counter = 0

    def _connect(u: str, v: str, cap: int) -> None:
        nonlocal road_counter
        road_counter += 1
        net.add_road(f"R_{road_counter}", u, v, cap)

    # Connect sources to first junction layer (or directly to shelters if 0 layers)
    first_targets = layers[0] if layers else shelters
    for s_idx, src_id in enumerate(sources):
        for offset in range(min(3, len(first_targets))):
            tgt = first_targets[(s_idx + offset) % len(first_targets)]
            _connect(src_id, tgt, rng.randint(250, 650))

    # Connect successive junction layers + intra-layer cross-links
    for l_idx in range(len(layers)):
        cur_layer = layers[l_idx]
        if l_idx + 1 < len(layers):
            nxt_layer = layers[l_idx + 1]
            for j_idx, u in enumerate(cur_layer):
                for offset in range(min(3, len(nxt_layer))):
                    v = nxt_layer[(j_idx + offset) % len(nxt_layer)]
                    _connect(u, v, rng.randint(150, 550))

        # Add deterministic intra-layer cross-links so Greedy can encounter reroute traps
        if len(cur_layer) >= 2:
            for k in range(min(spec.cross_links_per_layer, len(cur_layer) - 1)):
                u = cur_layer[k]
                v = cur_layer[(k + 1) % len(cur_layer)]
                if u != v and not net.get_roads_between(u, v):
                    _connect(u, v, rng.randint(100, 400))

    # Connect final junction layer to shelters
    if layers:
        last_layer = layers[-1]
        for j_idx, u in enumerate(last_layer):
            for offset in range(min(2, len(shelters))):
                shl_id = shelters[(j_idx + offset) % len(shelters)]
                _connect(u, shl_id, rng.randint(200, 650))

    return net


def run_scalability_benchmark(
    tiers: Sequence[ScalabilityTierSpec] = DEFAULT_SCALABILITY_TIERS,
    *,
    greedy_rule: GreedyRule | str = GreedyRule.SHORTEST_HOP,
    repeats: int = 3,
    seed: int = 42,
) -> ScalabilityBenchmarkReport:
    """Measure Dinic vs. Greedy execution times using time.perf_counter() across graph sizes."""
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise GraphValidationError(f"repeats must be >= 1, got {repeats!r}.")
    parsed_rule = GreedyRule.parse(greedy_rule)

    dinic_solver = DinicSolver()
    greedy_solver = GreedySolver()
    rows: list[PerformanceBenchmarkRow] = []

    for idx, tier in enumerate(tiers):
        net = generate_benchmark_network(tier, seed=seed + idx)
        dinic_flow_net = build_evacuation_network(net)
        greedy_flow_net = build_evacuation_network(net)

        dinic_times_ms: list[float] = []
        greedy_times_ms: list[float] = []
        dinic_max = 0
        greedy_max = 0

        for _ in range(repeats):
            dinic_flow_net.reset_flows()
            t0 = time.perf_counter()
            d_res = dinic_solver.solve(
                dinic_flow_net,
                domain_network=net,
                trace=False,
                reset=False,
                verify_invariants=False,
            )
            t1 = time.perf_counter()
            dinic_times_ms.append((t1 - t0) * 1000.0)
            dinic_max = d_res.max_flow

            greedy_flow_net.reset_flows()
            g0 = time.perf_counter()
            g_res = greedy_solver.solve(
                greedy_flow_net,
                domain_network=net,
                rule=parsed_rule,
                trace=False,
                reset=False,
                verify_invariants=False,
            )
            g1 = time.perf_counter()
            greedy_times_ms.append((g1 - g0) * 1000.0)
            greedy_max = g_res.max_flow

        dinic_times_ms.sort()
        greedy_times_ms.sort()
        mid = repeats // 2
        dinic_med = dinic_times_ms[mid]
        greedy_med = greedy_times_ms[mid]

        rows.append(
            PerformanceBenchmarkRow(
                tier_label=tier.label,
                num_vertices=len(net.nodes),
                num_edges=len(net.roads),
                augmented_vertices=dinic_flow_net.num_nodes,
                augmented_edges=dinic_flow_net.num_forward_edges,
                dinic_time_ms=dinic_med,
                greedy_time_ms=greedy_med,
                dinic_max_flow=dinic_max,
                greedy_flow=greedy_max,
                flow_gap=dinic_max - greedy_max,
            )
        )

    disclaimer = (
        f"Measured live with time.perf_counter() (median of {repeats} uninstrumented run(s) per "
        f"tier on {platform.system()} / Python {platform.python_version()}). Actual execution times "
        "depend on host hardware, background CPU load, and graph topology/density."
    )

    return ScalabilityBenchmarkReport(
        greedy_rule=parsed_rule.value,
        repeats=repeats,
        rows=tuple(rows),
        disclaimer=disclaimer,
    )


def build_benchmark_dataframe(report: ScalabilityBenchmarkReport) -> pd.DataFrame:
    """Convert ScalabilityBenchmarkReport rows into a display/export DataFrame."""
    return pd.DataFrame(
        [
            {
                "Tier": r.tier_label,
                "Vertices (|V|)": r.num_vertices,
                "Directed Roads (|E|)": r.num_edges,
                "Dinic Time (ms)": round(r.dinic_time_ms, 4),
                "Greedy Time (ms)": round(r.greedy_time_ms, 4),
                "Dinic Max Flow": r.dinic_max_flow,
                "Greedy Flow": r.greedy_flow,
                "Optimality Gap": r.flow_gap,
            }
            for r in report.rows
        ]
    )
