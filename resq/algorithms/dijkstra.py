"""Dijkstra's shortest-path solver using adjacency lists and a binary min-heap.

This optional educational extension computes minimum road-distance routes between
a chosen affected area and shelter independently of Dinic's Maximum Flow solver.
Worst-case complexity for single-source shortest paths: O((V + E) log V).
"""

from collections.abc import Iterable
import heapq
import math
import time

from resq.domain.enums import NodeType
from resq.domain.exceptions import EntityNotFoundError, GraphValidationError
from resq.domain.models import EvacuationNetwork
from resq.domain.results import DijkstraResult, ShortestPathRoute


class _IndexedWeightedGraph:
    """Compact adjacency-list representation keyed by integer vertex indices."""

    __slots__ = ("node_ids", "node_to_idx", "adj", "edge_count")

    def __init__(
        self,
        network: EvacuationNetwork,
        *,
        active_roads_only: bool = True,
    ) -> None:
        self.node_ids: tuple[str, ...] = tuple(network.nodes.keys())
        self.node_to_idx: dict[str, int] = {
            nid: idx for idx, nid in enumerate(self.node_ids)
        }
        n = len(self.node_ids)
        # Each slot stores tuples of (target_idx, non_negative_distance, road_id).
        self.adj: list[list[tuple[int, float, str]]] = [[] for _ in range(n)]
        edge_count = 0

        for road in network.roads.values():
            if active_roads_only and not road.is_active:
                continue
            if road.distance < 0.0 or not math.isfinite(road.distance):
                raise GraphValidationError(
                    f"Road '{road.road_id}' distance must be non-negative and finite, got {road.distance}."
                )
            u_idx = self.node_to_idx[road.source_id]
            v_idx = self.node_to_idx[road.target_id]
            self.adj[u_idx].append((v_idx, float(road.distance), road.road_id))
            edge_count += 1

        # Sort outgoing adjacency lists deterministically for reproducible tie-breaking.
        for edges in self.adj:
            edges.sort(key=lambda item: (self.node_ids[item[0]], item[1], item[2]))

        self.edge_count: int = edge_count


class DijkstraSolver:
    """Computes shortest non-negative road-distance routes via adjacency list + binary min-heap."""

    @staticmethod
    def _run_dijkstra_raw(
        graph: _IndexedWeightedGraph,
        source_idx: int,
        *,
        target_idx: int | None = None,
        blocked_nodes: frozenset[int] = frozenset(),
        blocked_roads: frozenset[str] = frozenset(),
        stop_at_target: bool = False,
    ) -> tuple[list[float], list[int], list[str | None], int, int]:
        """Run O((V + E) log V) binary min-heap Dijkstra from source_idx."""
        n = len(graph.node_ids)
        dist: list[float] = [math.inf] * n
        hops: list[int] = [10**9] * n
        parent_node: list[int] = [-1] * n
        parent_road: list[str | None] = [None] * n

        if source_idx in blocked_nodes:
            return dist, parent_node, parent_road, 0, 0

        dist[source_idx] = 0.0
        hops[source_idx] = 0

        # Binary min-heap entries: (distance, hop_count, vertex_id, vertex_idx)
        heap: list[tuple[float, int, str, int]] = [
            (0.0, 0, graph.node_ids[source_idx], source_idx)
        ]
        heap_pops = 0
        relaxed_edges = 0

        while heap:
            cur_dist, cur_hops, _cur_id, u_idx = heapq.heappop(heap)
            heap_pops += 1

            # Lazy deletion check: discard outdated heap states in O(1).
            if cur_dist > dist[u_idx] or (
                cur_dist == dist[u_idx] and cur_hops > hops[u_idx]
            ):
                continue

            if stop_at_target and target_idx is not None and u_idx == target_idx:
                break

            for v_idx, weight, road_id in graph.adj[u_idx]:
                if v_idx in blocked_nodes or road_id in blocked_roads:
                    continue
                new_dist = cur_dist + weight
                new_hops = cur_hops + 1
                if new_dist < dist[v_idx] or (
                    new_dist == dist[v_idx] and new_hops < hops[v_idx]
                ):
                    dist[v_idx] = new_dist
                    hops[v_idx] = new_hops
                    parent_node[v_idx] = u_idx
                    parent_road[v_idx] = road_id
                    relaxed_edges += 1
                    heapq.heappush(
                        heap,
                        (new_dist, new_hops, graph.node_ids[v_idx], v_idx),
                    )

        return dist, parent_node, parent_road, relaxed_edges, heap_pops

    @staticmethod
    def _reconstruct_path(
        graph: _IndexedWeightedGraph,
        source_idx: int,
        target_idx: int,
        parent_node: list[int],
        parent_road: list[str | None],
    ) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
        """Reconstruct ordered (node_path, road_ids) from source_idx to target_idx."""
        if source_idx != target_idx and parent_node[target_idx] == -1:
            return None

        nodes_rev: list[str] = [graph.node_ids[target_idx]]
        roads_rev: list[str] = []
        curr = target_idx
        while curr != source_idx:
            p_idx = parent_node[curr]
            rid = parent_road[curr]
            if p_idx == -1 or rid is None:
                return None
            roads_rev.append(rid)
            nodes_rev.append(graph.node_ids[p_idx])
            curr = p_idx

        nodes_rev.reverse()
        roads_rev.reverse()
        return tuple(nodes_rev), tuple(roads_rev)

    @staticmethod
    def _build_route(
        network: EvacuationNetwork,
        *,
        rank: int,
        node_path: Iterable[str],
        road_ids: Iterable[str],
    ) -> ShortestPathRoute:
        """Assemble detailed route telemetry from node and road sequences."""
        node_seq = tuple(node_path)
        road_seq = tuple(road_ids)
        node_names = tuple(network.nodes[nid].name for nid in node_seq)
        roads = [network.roads[rid] for rid in road_seq]

        road_names = tuple(r.name or r.road_id for r in roads)
        road_distances = tuple(float(r.distance) for r in roads)
        road_capacities = tuple(r.effective_capacity for r in roads)
        total_distance = float(sum(road_distances))
        bottleneck_capacity = min(road_capacities) if road_capacities else 0
        total_time = float(sum(r.travel_time_min for r in roads))

        src_node = network.nodes[node_seq[0]]
        dst_node = network.nodes[node_seq[-1]]
        return ShortestPathRoute(
            rank=rank,
            source_id=src_node.node_id,
            source_name=src_node.name,
            shelter_id=dst_node.node_id,
            shelter_name=dst_node.name,
            total_distance=total_distance,
            node_path=node_seq,
            node_names=node_names,
            road_ids=road_seq,
            road_names=road_names,
            road_distances=road_distances,
            road_capacities=road_capacities,
            bottleneck_capacity=bottleneck_capacity,
            total_travel_time_min=total_time,
        )

    def _find_alternative_route(
        self,
        network: EvacuationNetwork,
        graph: _IndexedWeightedGraph,
        primary_route: ShortestPathRoute,
        target_idx: int,
    ) -> ShortestPathRoute | None:
        """Compute the second-shortest simple path differing by >= 1 road (Yen's k=2 spur)."""
        primary_nodes = primary_route.node_path
        primary_roads = primary_route.road_ids
        best_candidate: tuple[float, int, tuple[str, ...], tuple[str, ...]] | None = None

        for spur_pos in range(len(primary_roads)):
            spur_node_id = primary_nodes[spur_pos]
            spur_node_idx = graph.node_to_idx[spur_node_id]
            root_nodes = primary_nodes[:spur_pos]
            root_roads = primary_roads[:spur_pos]

            blocked_nodes = frozenset(graph.node_to_idx[nid] for nid in root_nodes)
            blocked_roads = frozenset({primary_roads[spur_pos]})

            dist, parent_node, parent_road, _, _ = self._run_dijkstra_raw(
                graph,
                spur_node_idx,
                target_idx=target_idx,
                blocked_nodes=blocked_nodes,
                blocked_roads=blocked_roads,
                stop_at_target=True,
            )
            if not math.isfinite(dist[target_idx]):
                continue

            reconstructed = self._reconstruct_path(
                graph, spur_node_idx, target_idx, parent_node, parent_road
            )
            if reconstructed is None:
                continue

            spur_nodes, spur_roads = reconstructed
            full_nodes = root_nodes + spur_nodes
            full_roads = root_roads + spur_roads
            if full_roads == primary_roads or len(set(full_nodes)) != len(full_nodes):
                continue

            root_distance = sum(network.roads[rid].distance for rid in root_roads)
            total_distance = float(root_distance + dist[target_idx])
            cand_key = (total_distance, len(full_roads), full_roads, full_nodes)
            if best_candidate is None or cand_key < best_candidate:
                best_candidate = cand_key

        if best_candidate is None:
            return None

        _, _, alt_roads, alt_nodes = best_candidate
        return self._build_route(
            network, rank=2, node_path=alt_nodes, road_ids=alt_roads
        )

    def solve(
        self,
        network: EvacuationNetwork,
        source_id: str,
        shelter_id: str,
        *,
        active_roads_only: bool = True,
        require_area_and_shelter: bool = True,
        find_alternative: bool = True,
    ) -> DijkstraResult:
        """Compute shortest-distance path (and alternative route) from source to shelter."""
        if source_id not in network.nodes:
            raise EntityNotFoundError(
                f"Source node '{source_id}' does not exist in network."
            )
        if shelter_id not in network.nodes:
            raise EntityNotFoundError(
                f"Target shelter '{shelter_id}' does not exist in network."
            )

        src_node = network.nodes[source_id]
        dst_node = network.nodes[shelter_id]
        if require_area_and_shelter:
            if src_node.node_type != NodeType.AFFECTED_AREA:
                raise GraphValidationError(
                    f"Dijkstra evacuation origin '{source_id}' must be an affected_area node, "
                    f"got '{src_node.node_type.value}'."
                )
            if dst_node.node_type != NodeType.SHELTER:
                raise GraphValidationError(
                    f"Dijkstra evacuation destination '{shelter_id}' must be a shelter node, "
                    f"got '{dst_node.node_type.value}'."
                )

        start_ns = time.perf_counter_ns()
        graph = _IndexedWeightedGraph(network, active_roads_only=active_roads_only)
        source_idx = graph.node_to_idx[source_id]
        target_idx = graph.node_to_idx[shelter_id]

        dist, parent_node, parent_road, relaxed_edges, heap_pops = self._run_dijkstra_raw(
            graph,
            source_idx,
            target_idx=target_idx,
            stop_at_target=False,
        )

        distances_map = {
            nid: float(d)
            for nid, d in zip(graph.node_ids, dist)
            if math.isfinite(d)
        }

        shortest_route: ShortestPathRoute | None = None
        alternative_route: ShortestPathRoute | None = None
        reachable = math.isfinite(dist[target_idx])

        if reachable:
            reconstructed = self._reconstruct_path(
                graph, source_idx, target_idx, parent_node, parent_road
            )
            if reconstructed is not None:
                p_nodes, p_roads = reconstructed
                shortest_route = self._build_route(
                    network, rank=1, node_path=p_nodes, road_ids=p_roads
                )
                if find_alternative:
                    alternative_route = self._find_alternative_route(
                        network, graph, shortest_route, target_idx
                    )

        elapsed_ns = time.perf_counter_ns() - start_ns

        return DijkstraResult(
            source_id=src_node.node_id,
            source_name=src_node.name,
            shelter_id=dst_node.node_id,
            shelter_name=dst_node.name,
            reachable=shortest_route is not None,
            shortest_route=shortest_route,
            alternative_route=alternative_route,
            distances_from_source=distances_map,
            relaxed_edges_count=relaxed_edges,
            heap_pops=heap_pops,
            vertex_count=len(graph.node_ids),
            edge_count=graph.edge_count,
            execution_time_ns=elapsed_ns,
            execution_time_ms=elapsed_ns / 1_000_000.0,
        )


def solve_shortest_path_dijkstra(
    network: EvacuationNetwork,
    source_id: str,
    shelter_id: str,
    *,
    active_roads_only: bool = True,
    require_area_and_shelter: bool = True,
    find_alternative: bool = True,
) -> DijkstraResult:
    """Convenience wrapper to solve Dijkstra's shortest distance between source and shelter."""
    return DijkstraSolver().solve(
        network,
        source_id,
        shelter_id,
        active_roads_only=active_roads_only,
        require_area_and_shelter=require_area_and_shelter,
        find_alternative=find_alternative,
    )
