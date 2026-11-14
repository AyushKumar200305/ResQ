"""Minimum Cut extraction and bottleneck classification from residual graphs."""

from collections import deque

from resq.algorithms.dinic import DinicSolver
from resq.algorithms.residual_graph import EdgeKind, FlowNetwork
from resq.domain.exceptions import GraphValidationError
from resq.domain.models import EvacuationNetwork
from resq.domain.results import DinicResult, MinCutEdgeDetail, MinCutResult
from resq.algorithms.flow_builder import build_evacuation_network


class MinCutExtractor:
    """Extracts the exact S*-T* Minimum Cut from a saturated residual FlowNetwork."""

    def extract(
        self,
        flow_network: FlowNetwork,
        *,
        domain_network: EvacuationNetwork | None = None,
        expected_max_flow: int | None = None,
    ) -> MinCutResult:
        """Run residual BFS from Super-Source to partition vertices and isolate cut edges."""
        flow_network.verify_flow_invariants()

        n = flow_network.num_nodes
        source = flow_network.super_source_idx
        sink = flow_network.super_sink_idx
        adj = flow_network.adj
        node_ids = flow_network.node_ids

        reachable = [False] * n
        reachable[source] = True
        queue = deque([source])

        while queue:
            u = queue.popleft()
            for edge in adj[u]:
                if edge.residual_capacity > 0 and not reachable[edge.to]:
                    reachable[edge.to] = True
                    queue.append(edge.to)

        if reachable[sink]:
            raise GraphValidationError(
                "Cannot extract minimum cut: Super-Sink is still reachable from Super-Source "
                "in the residual graph. Solve maximum flow to completion first."
            )

        max_flow = flow_network.total_inflow_to_super_sink()
        if expected_max_flow is not None and max_flow != expected_max_flow:
            raise GraphValidationError(
                f"Residual flow mismatch: expected max_flow={expected_max_flow}, "
                f"observed={max_flow}."
            )

        reachable_vertices: list[str] = []
        unreachable_vertices: list[str] = []
        reachable_domain_nodes: list[str] = []
        unreachable_domain_nodes: list[str] = []

        for idx, is_reach in enumerate(reachable):
            vid = node_ids[idx]
            is_virtual = idx in (source, sink)
            if is_reach:
                reachable_vertices.append(vid)
                if not is_virtual:
                    reachable_domain_nodes.append(vid)
            else:
                unreachable_vertices.append(vid)
                if not is_virtual:
                    unreachable_domain_nodes.append(vid)

        cut_edges: list[MinCutEdgeDetail] = []
        road_bottlenecks: list[MinCutEdgeDetail] = []
        super_source_cuts: list[MinCutEdgeDetail] = []
        shelter_capacity_cuts: list[MinCutEdgeDetail] = []
        saturated_non_cut_roads: list[str] = []

        for u_idx, edge_list in enumerate(adj):
            u_reach = reachable[u_idx]
            for edge in edge_list:
                if not edge.is_forward:
                    continue
                v_reach = reachable[edge.to]
                crosses_cut = u_reach and not v_reach

                if crosses_cut:
                    label = self._format_edge_label(edge, domain_network)
                    is_active = True
                    if edge.edge_kind == EdgeKind.ROAD and domain_network is not None:
                        road_obj = domain_network.roads.get(edge.edge_id)
                        if road_obj is not None:
                            is_active = road_obj.is_active

                    detail = MinCutEdgeDetail(
                        edge_id=edge.edge_id,
                        edge_kind=edge.edge_kind.value,
                        source_id=edge.source_node_id,
                        target_id=edge.target_node_id,
                        label=label,
                        original_capacity=edge.original_capacity,
                        flow=edge.flow,
                        is_active=is_active,
                    )
                    cut_edges.append(detail)
                    if edge.edge_kind == EdgeKind.ROAD:
                        road_bottlenecks.append(detail)
                    elif edge.edge_kind == EdgeKind.SUPER_SOURCE:
                        super_source_cuts.append(detail)
                    elif edge.edge_kind == EdgeKind.SUPER_SINK:
                        shelter_capacity_cuts.append(detail)
                elif (
                    edge.edge_kind == EdgeKind.ROAD
                    and edge.original_capacity > 0
                    and edge.residual_capacity == 0
                ):
                    saturated_non_cut_roads.append(edge.edge_id)

        total_cut_capacity = sum(edge.original_capacity for edge in cut_edges)
        if total_cut_capacity != max_flow:
            raise GraphValidationError(
                f"Max-Flow Min-Cut invariant violated: max_flow={max_flow}, "
                f"min_cut_capacity={total_cut_capacity}."
            )

        return MinCutResult(
            max_flow=max_flow,
            total_cut_capacity=total_cut_capacity,
            reachable_vertices=tuple(reachable_vertices),
            unreachable_vertices=tuple(unreachable_vertices),
            reachable_domain_nodes=tuple(reachable_domain_nodes),
            unreachable_domain_nodes=tuple(unreachable_domain_nodes),
            cut_edges=tuple(cut_edges),
            road_bottlenecks=tuple(road_bottlenecks),
            super_source_cuts=tuple(super_source_cuts),
            shelter_capacity_cuts=tuple(shelter_capacity_cuts),
            saturated_non_cut_roads=tuple(saturated_non_cut_roads),
            road_cut_capacity=sum(e.original_capacity for e in road_bottlenecks),
            super_source_cut_capacity=sum(e.original_capacity for e in super_source_cuts),
            shelter_cut_capacity=sum(e.original_capacity for e in shelter_capacity_cuts),
        )

    @staticmethod
    def _format_edge_label(
        edge,
        domain_network: EvacuationNetwork | None,
    ) -> str:
        if edge.edge_kind == EdgeKind.ROAD:
            if domain_network is not None and edge.edge_id in domain_network.roads:
                road_name = domain_network.roads[edge.edge_id].name
                if road_name:
                    return f"{edge.edge_id} ({road_name})"
            return f"{edge.edge_id}: {edge.source_node_id} -> {edge.target_node_id}"
        if edge.edge_kind == EdgeKind.SUPER_SOURCE:
            return f"Source Demand Cap: {edge.target_node_id}"
        if edge.edge_kind == EdgeKind.SUPER_SINK:
            return f"Shelter Intake Cap: {edge.source_node_id}"
        return edge.edge_id


def extract_min_cut(
    flow_network: FlowNetwork,
    *,
    domain_network: EvacuationNetwork | None = None,
    expected_max_flow: int | None = None,
) -> MinCutResult:
    """Extract Minimum Cut from an already-solved FlowNetwork."""
    return MinCutExtractor().extract(
        flow_network,
        domain_network=domain_network,
        expected_max_flow=expected_max_flow,
    )


def solve_max_flow_and_min_cut(
    network: EvacuationNetwork,
    *,
    trace: bool = False,
) -> tuple[DinicResult, MinCutResult]:
    """Build FlowNetwork, solve Max Flow with Dinic, and extract the Minimum Cut."""
    flow_network = build_evacuation_network(network)
    dinic_result = DinicSolver().solve(
        flow_network,
        domain_network=network,
        trace=trace,
        reset=False,
        verify_invariants=True,
    )
    min_cut_result = MinCutExtractor().extract(
        flow_network,
        domain_network=network,
        expected_max_flow=dinic_result.max_flow,
    )
    return dinic_result, min_cut_result
