"""Flow path decomposition converting edge-level Dinic flow into evacuation routes."""

from dataclasses import dataclass

from resq.algorithms.residual_graph import EdgeKind, FlowNetwork
from resq.domain.models import EvacuationNetwork


@dataclass(frozen=True, slots=True)
class EvacuationRoute:
    """Single source-to-shelter evacuation corridor with assigned flow volume."""

    route_index: int
    source_id: str
    source_name: str
    shelter_id: str
    shelter_name: str
    node_path: tuple[str, ...]
    road_ids: tuple[str, ...]
    flow: int
    total_travel_time_min: float


def decompose_evacuation_routes(
    flow_network: FlowNetwork,
    *,
    domain_network: EvacuationNetwork | None = None,
) -> list[EvacuationRoute]:
    """Decompose positive flow in a solved FlowNetwork into discrete S->T routes.

    Extracts simple S* -> ... -> T* paths along positive forward flow edges,
    preserving exact total flow conservation across all decomposed routes.
    """
    n = flow_network.num_nodes
    source = flow_network.super_source_idx
    sink = flow_network.super_sink_idx
    adj = flow_network.adj
    node_ids = flow_network.node_ids

    # Track remaining positive forward flow per edge slot without mutating FlowNetwork.
    remaining_adj: list[list[list[object]]] = [[] for _ in range(n)]
    for u_idx, edge_list in enumerate(adj):
        for edge in edge_list:
            if edge.is_forward and edge.flow > 0:
                # [to_idx, remaining_flow, edge_id, edge_kind]
                remaining_adj[u_idx].append(
                    [edge.to, edge.flow, edge.edge_id, edge.edge_kind]
                )

    routes: list[EvacuationRoute] = []
    route_idx = 0

    while True:
        # Iterative DFS to locate one simple S* -> T* path with positive remaining flow.
        visited = [False] * n
        visited[source] = True
        parent_step: list[tuple[int, int] | None] = [None] * n
        stack: list[tuple[int, int]] = [(source, 0)]
        found = False

        while stack:
            u, pos = stack[-1]
            if u == sink:
                found = True
                break
            out_edges = remaining_adj[u]
            if pos >= len(out_edges):
                stack.pop()
                continue
            stack[-1] = (u, pos + 1)
            entry = out_edges[pos]
            v = int(entry[0])  # type: ignore[arg-type]
            rem = int(entry[1])  # type: ignore[arg-type]
            if rem > 0 and not visited[v]:
                visited[v] = True
                parent_step[v] = (u, pos)
                stack.append((v, 0))

        if not found:
            break

        # Reconstruct path and compute bottleneck flow.
        path_entries: list[tuple[int, int]] = []
        bottleneck: int | None = None
        curr = sink
        while curr != source:
            step = parent_step[curr]
            assert step is not None
            pu, pos = step
            rem = int(remaining_adj[pu][pos][1])  # type: ignore[arg-type]
            bottleneck = rem if bottleneck is None else min(bottleneck, rem)
            path_entries.append((pu, pos))
            curr = pu

        assert bottleneck is not None and bottleneck > 0
        path_entries.reverse()

        domain_nodes: list[str] = []
        road_ids: list[str] = []
        travel_time = 0.0

        for pu, pos in path_entries:
            entry = remaining_adj[pu][pos]
            entry[1] = int(entry[1]) - bottleneck  # type: ignore[arg-type]
            edge_id = str(entry[2])
            edge_kind = entry[3]
            to_idx = int(entry[0])  # type: ignore[arg-type]

            if edge_kind == EdgeKind.SUPER_SOURCE:
                domain_nodes.append(node_ids[to_idx])
            elif edge_kind == EdgeKind.ROAD:
                domain_nodes.append(node_ids[to_idx])
                road_ids.append(edge_id)
                if domain_network is not None and edge_id in domain_network.roads:
                    travel_time += domain_network.roads[edge_id].travel_time_min

        if domain_nodes:
            route_idx += 1
            src_id = domain_nodes[0]
            shl_id = domain_nodes[-1]
            src_name = (
                domain_network.nodes[src_id].name
                if domain_network is not None and src_id in domain_network.nodes
                else src_id
            )
            shl_name = (
                domain_network.nodes[shl_id].name
                if domain_network is not None and shl_id in domain_network.nodes
                else shl_id
            )
            routes.append(
                EvacuationRoute(
                    route_index=route_idx,
                    source_id=src_id,
                    source_name=src_name,
                    shelter_id=shl_id,
                    shelter_name=shl_name,
                    node_path=tuple(domain_nodes),
                    road_ids=tuple(road_ids),
                    flow=bottleneck,
                    total_travel_time_min=travel_time,
                )
            )

    return routes
