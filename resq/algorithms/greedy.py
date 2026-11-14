"""Deterministic forward-only Greedy flow baseline for algorithmic comparison.

Unlike Dinic's Maximum Flow, this baseline uses its own independent FlowNetwork
and NEVER traverses backward residual edges (`not edge.is_forward`). Once flow
is committed to a route under the active selection rule, it cannot be rerouted.
"""

from collections import deque
import heapq
import time

from resq.algorithms.residual_graph import EdgeKind, FlowEdge, FlowNetwork
from resq.algorithms.telemetry import extract_flow_telemetry
from resq.domain.enums import GreedyRule
from resq.domain.models import EvacuationNetwork
from resq.domain.results import GreedyResult, GreedyStepDetail
from resq.algorithms.flow_builder import build_evacuation_network


class GreedySolver:
    """Forward-only deterministic greedy augmenting-path baseline."""

    def solve(
        self,
        flow_network: FlowNetwork,
        *,
        domain_network: EvacuationNetwork | None = None,
        rule: GreedyRule | str = GreedyRule.SHORTEST_HOP,
        trace: bool = False,
        reset: bool = True,
        verify_invariants: bool = True,
    ) -> GreedyResult:
        """Run greedy forward-only flow augmentation until no forward S*->T* path exists."""
        parsed_rule = GreedyRule.parse(rule)
        if reset:
            flow_network.reset_flows()

        n = flow_network.num_nodes
        source = flow_network.super_source_idx
        sink = flow_network.super_sink_idx
        adj = flow_network.adj
        node_ids = flow_network.node_ids

        # Deterministic forward-edge adjacency sorted by (target_node_id, edge_id).
        sorted_forward_adj: list[list[tuple[int, FlowEdge]]] = [
            sorted(
                ((idx, edge) for idx, edge in enumerate(adj[u]) if edge.is_forward),
                key=lambda item: (item[1].target_node_id, item[1].edge_id),
            )
            for u in range(n)
        ]

        total_out_bound = sum(edge.residual_capacity for _, edge in sorted_forward_adj[source])
        inf_bound = total_out_bound if total_out_bound > 0 else 1

        greedy_flow = 0
        augmentations = 0
        paths_explored = 0
        steps: list[GreedyStepDetail] = []

        start_ns = time.perf_counter_ns()

        while True:
            paths_explored += 1
            if parsed_rule == GreedyRule.SHORTEST_HOP:
                path_steps, bottleneck = self._find_shortest_hop_forward_path(
                    adj, sorted_forward_adj, n, source, sink, inf_bound
                )
            elif parsed_rule == GreedyRule.WIDEST_PATH:
                path_steps, bottleneck = self._find_widest_forward_path(
                    adj, sorted_forward_adj, n, source, sink, inf_bound
                )
            else:
                path_steps, bottleneck = self._find_lexicographic_dfs_forward_path(
                    adj, sorted_forward_adj, n, source, sink, inf_bound
                )

            if bottleneck == 0:
                break

            augmentations += 1
            greedy_flow += bottleneck

            for u_idx, edge_idx in path_steps:
                flow_network.push_flow(u_idx, edge_idx, bottleneck)

            if trace:
                selected_nodes = [node_ids[source]]
                edge_labels = []
                for u_idx, edge_idx in path_steps:
                    edge = adj[u_idx][edge_idx]
                    selected_nodes.append(node_ids[edge.to])
                    if edge.edge_kind == EdgeKind.SUPER_SOURCE:
                        edge_labels.append(f"S*->{edge.target_node_id}")
                    elif edge.edge_kind == EdgeKind.SUPER_SINK:
                        edge_labels.append(f"{edge.source_node_id}->T*")
                    else:
                        edge_labels.append(edge.edge_id)

                steps.append(
                    GreedyStepDetail(
                        step_index=augmentations,
                        selected_path=tuple(selected_nodes),
                        path_edge_labels=tuple(edge_labels),
                        flow_sent=bottleneck,
                        cumulative_flow=greedy_flow,
                    )
                )

        end_ns = time.perf_counter_ns()
        elapsed_ns = end_ns - start_ns

        if verify_invariants:
            flow_network.verify_flow_invariants()

        telemetry = extract_flow_telemetry(
            flow_network,
            achieved_flow=greedy_flow,
            domain_network=domain_network,
        )

        return GreedyResult(
            rule=parsed_rule.value,
            max_flow=greedy_flow,
            total_population=telemetry.total_population,
            total_shelter_capacity=telemetry.total_shelter_capacity,
            unmet_demand=telemetry.unmet_demand,
            evacuation_rate=telemetry.evacuation_rate,
            road_flows=telemetry.road_flows,
            source_evacuations=telemetry.source_evacuations,
            shelter_intakes=telemetry.shelter_intakes,
            augmentations=augmentations,
            paths_explored=paths_explored,
            execution_time_ns=elapsed_ns,
            execution_time_ms=elapsed_ns / 1_000_000.0,
            algorithm_name=f"Greedy Baseline ({parsed_rule.value})",
            steps=tuple(steps) if trace else None,
        )

    @staticmethod
    def _find_shortest_hop_forward_path(
        adj: list[list[FlowEdge]],
        sorted_forward_adj: list[list[tuple[int, FlowEdge]]],
        num_nodes: int,
        source: int,
        sink: int,
        inf_bound: int,
    ) -> tuple[list[tuple[int, int]], int]:
        """BFS over forward-only edges with positive remaining capacity."""
        parent_node = [-1] * num_nodes
        parent_edge = [-1] * num_nodes
        parent_node[source] = source
        queue = deque([source])

        while queue and parent_node[sink] == -1:
            u = queue.popleft()
            for edge_idx, edge in sorted_forward_adj[u]:
                if edge.residual_capacity > 0 and parent_node[edge.to] == -1:
                    parent_node[edge.to] = u
                    parent_edge[edge.to] = edge_idx
                    queue.append(edge.to)

        if parent_node[sink] == -1:
            return [], 0

        return GreedySolver._reconstruct_path(
            adj, parent_node, parent_edge, source, sink, inf_bound
        )

    @staticmethod
    def _find_widest_forward_path(
        adj: list[list[FlowEdge]],
        sorted_forward_adj: list[list[tuple[int, FlowEdge]]],
        num_nodes: int,
        source: int,
        sink: int,
        inf_bound: int,
    ) -> tuple[list[tuple[int, int]], int]:
        """Modified Dijkstra maximizing forward bottleneck capacity (tie-breaking by min hops)."""
        best_cap = [0] * num_nodes
        best_hops = [num_nodes + 1] * num_nodes
        parent_node = [-1] * num_nodes
        parent_edge = [-1] * num_nodes

        best_cap[source] = inf_bound
        best_hops[source] = 0
        parent_node[source] = source
        heap: list[tuple[int, int, int]] = [(-inf_bound, 0, source)]

        while heap:
            neg_cap, hops, u = heapq.heappop(heap)
            cap = -neg_cap
            if cap < best_cap[u] or (cap == best_cap[u] and hops > best_hops[u]):
                continue
            if u == sink:
                break

            next_hops = hops + 1
            for edge_idx, edge in sorted_forward_adj[u]:
                if edge.residual_capacity <= 0:
                    continue
                cand_cap = cap if cap < edge.residual_capacity else edge.residual_capacity
                v = edge.to
                if cand_cap > best_cap[v] or (
                    cand_cap == best_cap[v] and next_hops < best_hops[v]
                ):
                    best_cap[v] = cand_cap
                    best_hops[v] = next_hops
                    parent_node[v] = u
                    parent_edge[v] = edge_idx
                    heapq.heappush(heap, (-cand_cap, next_hops, v))

        if parent_node[sink] == -1:
            return [], 0

        return GreedySolver._reconstruct_path(
            adj, parent_node, parent_edge, source, sink, inf_bound
        )

    @staticmethod
    def _find_lexicographic_dfs_forward_path(
        adj: list[list[FlowEdge]],
        sorted_forward_adj: list[list[tuple[int, FlowEdge]]],
        num_nodes: int,
        source: int,
        sink: int,
        inf_bound: int,
    ) -> tuple[list[tuple[int, int]], int]:
        """Iterative forward-only DFS using lexicographical neighbor order."""
        visited = [False] * num_nodes
        visited[source] = True
        parent_node = [-1] * num_nodes
        parent_edge = [-1] * num_nodes
        parent_node[source] = source

        # Stack stores (node_idx, next_sorted_neighbor_offset)
        stack: list[tuple[int, int]] = [(source, 0)]
        found = False

        while stack:
            u, pos = stack[-1]
            if u == sink:
                found = True
                break
            neighbors = sorted_forward_adj[u]
            if pos >= len(neighbors):
                stack.pop()
                continue
            stack[-1] = (u, pos + 1)
            edge_idx, edge = neighbors[pos]
            if edge.residual_capacity > 0 and not visited[edge.to]:
                visited[edge.to] = True
                parent_node[edge.to] = u
                parent_edge[edge.to] = edge_idx
                stack.append((edge.to, 0))

        if not found:
            return [], 0

        return GreedySolver._reconstruct_path(
            adj, parent_node, parent_edge, source, sink, inf_bound
        )

    @staticmethod
    def _reconstruct_path(
        adj: list[list[FlowEdge]],
        parent_node: list[int],
        parent_edge: list[int],
        source: int,
        sink: int,
        inf_bound: int,
    ) -> tuple[list[tuple[int, int]], int]:
        path_steps: list[tuple[int, int]] = []
        bottleneck = inf_bound
        curr = sink
        while curr != source:
            prev = parent_node[curr]
            e_idx = parent_edge[curr]
            res = adj[prev][e_idx].residual_capacity
            if res < bottleneck:
                bottleneck = res
            path_steps.append((prev, e_idx))
            curr = prev
        path_steps.reverse()
        return path_steps, bottleneck


def solve_greedy_baseline(
    network: EvacuationNetwork,
    *,
    rule: GreedyRule | str = GreedyRule.SHORTEST_HOP,
    trace: bool = False,
) -> GreedyResult:
    """Build an independent FlowNetwork and solve using the forward-only Greedy baseline."""
    flow_network = build_evacuation_network(network)
    return GreedySolver().solve(
        flow_network,
        domain_network=network,
        rule=rule,
        trace=trace,
        reset=False,
        verify_invariants=True,
    )
