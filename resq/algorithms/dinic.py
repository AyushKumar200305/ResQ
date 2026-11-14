"""From-scratch implementation of Dinic's Maximum Flow algorithm.

Time complexity on general directed graphs: O(V^2 E), using:
- O(V + E) BFS to construct the residual level graph each phase.
- O(V * E) blocking flow per phase via DFS with current-edge pointer optimization.
"""

from collections import deque
import time

from resq.algorithms.residual_graph import EdgeKind, FlowEdge, FlowNetwork
from resq.algorithms.telemetry import extract_flow_telemetry
from resq.domain.models import EvacuationNetwork
from resq.domain.results import (
    AugmentationStepTrace,
    DinicPhaseTrace,
    DinicResult,
    DinicTrace,
    ResidualUpdateTrace,
)
from resq.algorithms.flow_builder import build_evacuation_network


class DinicSolver:
    """Dinic's Maximum Flow solver operating directly on a FlowNetwork residual graph."""

    def solve(
        self,
        flow_network: FlowNetwork,
        *,
        domain_network: EvacuationNetwork | None = None,
        trace: bool = False,
        reset: bool = True,
        verify_invariants: bool = True,
    ) -> DinicResult:
        """Execute Dinic's algorithm on `flow_network` and return structured flow metrics.

        Args:
            flow_network: Augmented FlowNetwork with Super-Source and Super-Sink.
            domain_network: Optional domain EvacuationNetwork for enriching node/road names.
            trace: When True, records per-phase BFS levels and DFS augmenting path steps.
                Disabled by default so standard benchmarking pays zero trace overhead.
            reset: When True, resets flows/residuals to original capacities before solving.
            verify_invariants: When True, validates capacity & flow conservation invariants
                after timing completes.
        """
        if reset:
            flow_network.reset_flows()

        n = flow_network.num_nodes
        source = flow_network.super_source_idx
        sink = flow_network.super_sink_idx
        adj = flow_network.adj
        node_ids = flow_network.node_ids

        total_out_bound = sum(edge.residual_capacity for edge in adj[source])
        inf_bound = total_out_bound if total_out_bound > 0 else 1

        max_flow = 0
        bfs_phases = 0
        bfs_calls = 0
        dfs_attempts = 0
        useful_augmentations = 0
        dfs_edge_scans = 0

        phase_traces: list[DinicPhaseTrace] = []
        global_step_idx = 0
        reverse_rerouting_steps = 0

        start_ns = time.perf_counter_ns()

        while True:
            levels = self._build_level_graph(adj, n, source)
            bfs_calls += 1
            sink_level = levels[sink]

            if sink_level == -1:
                if trace:
                    phase_traces.append(
                        DinicPhaseTrace(
                            phase_index=bfs_calls,
                            sink_reachable=False,
                            sink_level=None,
                            node_levels={
                                node_ids[idx]: lvl
                                for idx, lvl in enumerate(levels)
                                if lvl != -1
                            },
                            augmentations=(),
                            phase_flow_pushed=0,
                            cumulative_flow=max_flow,
                        )
                    )
                break

            bfs_phases += 1
            ptr = [0] * n
            phase_flow = 0
            phase_augmentations: list[AugmentationStepTrace] = []

            while True:
                dfs_attempts += 1
                pushed, path_steps, scans = self._dfs_augment_one_path(
                    adj,
                    levels,
                    ptr,
                    source,
                    sink,
                    inf_bound,
                )
                dfs_edge_scans += scans
                if pushed == 0:
                    break

                useful_augmentations += 1
                phase_flow += pushed
                max_flow += pushed

                if trace:
                    global_step_idx += 1
                    aug_trace = self._apply_and_record_path(
                        flow_network,
                        path_steps,
                        pushed,
                        step_index=global_step_idx,
                        phase_index=bfs_phases,
                    )
                    if aug_trace.rerouted_via_reverse_edge:
                        reverse_rerouting_steps += 1
                    phase_augmentations.append(aug_trace)
                else:
                    for u_idx, edge_idx in path_steps:
                        flow_network.push_flow(u_idx, edge_idx, pushed)

            if trace:
                phase_traces.append(
                    DinicPhaseTrace(
                        phase_index=bfs_phases,
                        sink_reachable=True,
                        sink_level=sink_level,
                        node_levels={
                            node_ids[idx]: lvl
                            for idx, lvl in enumerate(levels)
                            if lvl != -1
                        },
                        augmentations=tuple(phase_augmentations),
                        phase_flow_pushed=phase_flow,
                        cumulative_flow=max_flow,
                    )
                )

        end_ns = time.perf_counter_ns()
        elapsed_ns = end_ns - start_ns

        if verify_invariants:
            flow_network.verify_flow_invariants()

        dinic_trace = (
            DinicTrace(
                phases=tuple(phase_traces),
                total_phases_with_flow=bfs_phases,
                total_augmentations=useful_augmentations,
                reverse_rerouting_steps=reverse_rerouting_steps,
            )
            if trace
            else None
        )

        return self._build_result(
            flow_network=flow_network,
            domain_network=domain_network,
            max_flow=max_flow,
            bfs_phases=bfs_phases,
            bfs_calls=bfs_calls,
            dfs_attempts=dfs_attempts,
            useful_augmentations=useful_augmentations,
            dfs_edge_scans=dfs_edge_scans,
            elapsed_ns=elapsed_ns,
            trace=dinic_trace,
        )

    @staticmethod
    def _build_level_graph(
        adj: list[list[FlowEdge]],
        num_nodes: int,
        source: int,
    ) -> list[int]:
        """Construct shortest-hop residual levels via BFS starting at Super-Source."""
        levels = [-1] * num_nodes
        levels[source] = 0
        queue = deque([source])

        while queue:
            u = queue.popleft()
            next_level = levels[u] + 1
            for edge in adj[u]:
                if edge.residual_capacity > 0 and levels[edge.to] == -1:
                    levels[edge.to] = next_level
                    queue.append(edge.to)

        return levels

    @staticmethod
    def _dfs_augment_one_path(
        adj: list[list[FlowEdge]],
        levels: list[int],
        ptr: list[int],
        source: int,
        sink: int,
        inf_bound: int,
    ) -> tuple[int, list[tuple[int, int]], int]:
        """Iterative DFS with current-edge pointer optimization finding one level-graph path."""
        stack: list[tuple[int, int]] = [(source, inf_bound)]
        path_steps: list[tuple[int, int]] = []
        scans = 0

        while stack:
            u, flow_in = stack[-1]
            if u == sink:
                return flow_in, path_steps, scans

            u_adj = adj[u]
            edge_count = len(u_adj)
            target_level = levels[u] + 1
            i = ptr[u]
            advanced = False

            while i < edge_count:
                scans += 1
                edge = u_adj[i]
                if edge.residual_capacity > 0 and levels[edge.to] == target_level:
                    ptr[u] = i
                    next_flow = (
                        flow_in
                        if flow_in < edge.residual_capacity
                        else edge.residual_capacity
                    )
                    path_steps.append((u, i))
                    stack.append((edge.to, next_flow))
                    advanced = True
                    break
                i += 1

            if not advanced:
                ptr[u] = edge_count
                stack.pop()
                if path_steps:
                    parent_u, _ = path_steps.pop()
                    ptr[parent_u] += 1

        return 0, [], scans

    @staticmethod
    def _apply_and_record_path(
        flow_network: FlowNetwork,
        path_steps: list[tuple[int, int]],
        pushed: int,
        *,
        step_index: int,
        phase_index: int,
    ) -> AugmentationStepTrace:
        """Push flow along the selected path and capture exact residual updates."""
        adj = flow_network.adj
        node_ids = flow_network.node_ids

        selected_nodes: list[str] = [node_ids[flow_network.super_source_idx]]
        edge_labels: list[str] = []
        updates: list[ResidualUpdateTrace] = []
        used_reverse_any = False

        for u_idx, edge_idx in path_steps:
            edge = adj[u_idx][edge_idx]
            partner = adj[edge.to][edge.rev]

            fwd_edge = edge if edge.is_forward else partner
            rev_edge = partner if edge.is_forward else edge
            used_reverse = not edge.is_forward
            if used_reverse:
                used_reverse_any = True

            fwd_before = fwd_edge.residual_capacity
            rev_before = rev_edge.residual_capacity

            flow_network.push_flow(u_idx, edge_idx, pushed)

            fwd_after = fwd_edge.residual_capacity
            rev_after = rev_edge.residual_capacity

            selected_nodes.append(node_ids[edge.to])
            if edge.edge_kind == EdgeKind.SUPER_SOURCE:
                label = f"S*->{edge.target_node_id}"
            elif edge.edge_kind == EdgeKind.SUPER_SINK:
                label = f"{edge.source_node_id}->T*"
            elif used_reverse:
                label = f"REV({edge.edge_id}:{edge.source_node_id}->{edge.target_node_id})"
            else:
                label = edge.edge_id
            edge_labels.append(label)

            updates.append(
                ResidualUpdateTrace(
                    edge_id=edge.edge_id,
                    edge_kind=edge.edge_kind.value,
                    traversed_from=node_ids[u_idx],
                    traversed_to=node_ids[edge.to],
                    used_reverse_edge=used_reverse,
                    flow_delta=pushed,
                    forward_residual_before=fwd_before,
                    forward_residual_after=fwd_after,
                    reverse_residual_before=rev_before,
                    reverse_residual_after=rev_after,
                )
            )

        return AugmentationStepTrace(
            step_index=step_index,
            phase_index=phase_index,
            selected_path=tuple(selected_nodes),
            path_edge_labels=tuple(edge_labels),
            flow_sent=pushed,
            edge_updates=tuple(updates),
            rerouted_via_reverse_edge=used_reverse_any,
        )

    @staticmethod
    def _build_result(
        *,
        flow_network: FlowNetwork,
        domain_network: EvacuationNetwork | None,
        max_flow: int,
        bfs_phases: int,
        bfs_calls: int,
        dfs_attempts: int,
        useful_augmentations: int,
        dfs_edge_scans: int,
        elapsed_ns: int,
        trace: DinicTrace | None,
    ) -> DinicResult:
        """Assemble structured road, source, and shelter telemetry from FlowNetwork."""
        telemetry = extract_flow_telemetry(
            flow_network,
            achieved_flow=max_flow,
            domain_network=domain_network,
        )

        return DinicResult(
            max_flow=max_flow,
            total_population=telemetry.total_population,
            total_shelter_capacity=telemetry.total_shelter_capacity,
            unmet_demand=telemetry.unmet_demand,
            evacuation_rate=telemetry.evacuation_rate,
            road_flows=telemetry.road_flows,
            source_evacuations=telemetry.source_evacuations,
            shelter_intakes=telemetry.shelter_intakes,
            bfs_phases=bfs_phases,
            bfs_calls=bfs_calls,
            dfs_attempts=dfs_attempts,
            useful_augmentations=useful_augmentations,
            dfs_edge_scans=dfs_edge_scans,
            execution_time_ns=elapsed_ns,
            execution_time_ms=elapsed_ns / 1_000_000.0,
            trace=trace,
        )


def solve_max_flow_dinic(
    network: EvacuationNetwork,
    *,
    trace: bool = False,
) -> DinicResult:
    """Build the Super-Source/Super-Sink FlowNetwork and solve with Dinic's algorithm."""
    flow_network = build_evacuation_network(network)
    solver = DinicSolver()
    return solver.solve(
        flow_network,
        domain_network=network,
        trace=trace,
        reset=False,
        verify_invariants=True,
    )
