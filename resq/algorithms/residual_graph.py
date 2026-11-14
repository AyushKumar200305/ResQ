"""Residual graph representation separating original capacities from working residuals."""

from dataclasses import dataclass
from enum import Enum

from resq.domain.exceptions import (
    DuplicateIdentifierError,
    EntityNotFoundError,
    GraphValidationError,
)
from resq.domain.validation import (
    SUPER_SINK_ID,
    SUPER_SOURCE_ID,
    validate_non_negative_int,
)


class EdgeKind(str, Enum):
    """Semantic classification of edges inside the augmented flow network."""

    SUPER_SOURCE = "super_source"
    ROAD = "road"
    SUPER_SINK = "super_sink"
    RESIDUAL_REVERSE = "residual_reverse"


@dataclass(slots=True)
class FlowEdge:
    """Directed edge slot inside FlowNetwork's indexed adjacency lists.

    `original_capacity` stores the immutable modeled capacity c(u, v) (0 for
    reverse residual edges), while `residual_capacity` and `flow` capture the
    mutable algorithm state.
    """

    to: int
    rev: int
    original_capacity: int
    residual_capacity: int
    flow: int
    edge_id: str
    edge_kind: EdgeKind
    is_forward: bool
    source_node_id: str
    target_node_id: str
    nominal_capacity: int


class FlowNetwork:
    """Indexed adjacency-list residual graph for multi-source, multi-sink evacuation flow."""

    def __init__(
        self,
        *,
        super_source_id: str = SUPER_SOURCE_ID,
        super_sink_id: str = SUPER_SINK_ID,
    ) -> None:
        if super_source_id == super_sink_id:
            raise GraphValidationError(
                "super_source_id and super_sink_id must be distinct."
            )
        self.super_source_id: str = super_source_id
        self.super_sink_id: str = super_sink_id

        self.node_ids: list[str] = []
        self.node_to_index: dict[str, int] = {}
        self.adj: list[list[FlowEdge]] = []

        self._forward_edge_refs: dict[tuple[EdgeKind, str], tuple[int, int]] = {}

        self.super_source_idx: int = self.register_node(super_source_id)
        self.super_sink_idx: int = self.register_node(super_sink_id)

    @property
    def num_nodes(self) -> int:
        """Total number of vertices including super-source and super-sink."""
        return len(self.node_ids)

    @property
    def num_forward_edges(self) -> int:
        """Number of forward modeled edges (excluding residual reverse slots)."""
        return len(self._forward_edge_refs)

    def register_node(self, node_id: str) -> int:
        """Register a vertex ID in deterministic order and return its integer index."""
        if node_id in self.node_to_index:
            return self.node_to_index[node_id]
        idx = len(self.node_ids)
        self.node_ids.append(node_id)
        self.node_to_index[node_id] = idx
        self.adj.append([])
        return idx

    def add_directed_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        capacity: int,
        *,
        edge_id: str,
        edge_kind: EdgeKind,
        nominal_capacity: int | None = None,
    ) -> tuple[int, int]:
        """Insert a forward capacity edge and its paired 0-capacity residual reverse edge."""
        if source_node_id not in self.node_to_index:
            raise EntityNotFoundError(
                f"Source vertex '{source_node_id}' is not registered in FlowNetwork."
            )
        if target_node_id not in self.node_to_index:
            raise EntityNotFoundError(
                f"Target vertex '{target_node_id}' is not registered in FlowNetwork."
            )
        if source_node_id == target_node_id:
            raise GraphValidationError(
                f"Self-loop edge '{edge_id}' on vertex '{source_node_id}' is not allowed."
            )
        if edge_kind == EdgeKind.RESIDUAL_REVERSE:
            raise GraphValidationError(
                "Caller must not manually insert RESIDUAL_REVERSE edges."
            )

        clean_cap = validate_non_negative_int(capacity, f"capacity for edge '{edge_id}'")
        clean_nominal = (
            clean_cap
            if nominal_capacity is None
            else validate_non_negative_int(
                nominal_capacity, f"nominal_capacity for edge '{edge_id}'"
            )
        )

        ref_key = (edge_kind, edge_id)
        if ref_key in self._forward_edge_refs:
            raise DuplicateIdentifierError(
                f"Duplicate {edge_kind.value} edge identifier '{edge_id}' in FlowNetwork."
            )

        u_idx = self.node_to_index[source_node_id]
        v_idx = self.node_to_index[target_node_id]

        fwd_pos = len(self.adj[u_idx])
        bwd_pos = len(self.adj[v_idx])

        forward_edge = FlowEdge(
            to=v_idx,
            rev=bwd_pos,
            original_capacity=clean_cap,
            residual_capacity=clean_cap,
            flow=0,
            edge_id=edge_id,
            edge_kind=edge_kind,
            is_forward=True,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            nominal_capacity=clean_nominal,
        )
        reverse_edge = FlowEdge(
            to=u_idx,
            rev=fwd_pos,
            original_capacity=0,
            residual_capacity=0,
            flow=0,
            edge_id=edge_id,
            edge_kind=EdgeKind.RESIDUAL_REVERSE,
            is_forward=False,
            source_node_id=target_node_id,
            target_node_id=source_node_id,
            nominal_capacity=0,
        )

        self.adj[u_idx].append(forward_edge)
        self.adj[v_idx].append(reverse_edge)
        self._forward_edge_refs[ref_key] = (u_idx, fwd_pos)
        return (u_idx, fwd_pos)

    def push_flow(self, u_idx: int, edge_idx: int, amount: int) -> None:
        """Augment flow along `adj[u_idx][edge_idx]` and update residual capacities."""
        if amount < 0:
            raise GraphValidationError(f"Flow augmentation must be >= 0, got {amount}.")
        edge = self.adj[u_idx][edge_idx]
        if amount > edge.residual_capacity:
            raise GraphValidationError(
                f"Cannot push {amount} on edge '{edge.edge_id}' with residual capacity "
                f"{edge.residual_capacity}."
            )
        if amount == 0:
            return
        rev_edge = self.adj[edge.to][edge.rev]
        edge.residual_capacity -= amount
        edge.flow += amount
        rev_edge.residual_capacity += amount
        rev_edge.flow -= amount

    def reset_flows(self) -> None:
        """Restore all residual capacities to original capacities and zero all flows."""
        for edge_list in self.adj:
            for edge in edge_list:
                edge.residual_capacity = edge.original_capacity
                edge.flow = 0

    def get_forward_edge(self, edge_kind: EdgeKind, edge_id: str) -> FlowEdge:
        """Look up a specific forward edge by kind and domain identifier."""
        ref_key = (edge_kind, edge_id)
        if ref_key not in self._forward_edge_refs:
            raise EntityNotFoundError(
                f"Edge ({edge_kind.value}, '{edge_id}') not found in FlowNetwork."
            )
        u_idx, pos = self._forward_edge_refs[ref_key]
        return self.adj[u_idx][pos]

    def get_road_edge(self, road_id: str) -> FlowEdge:
        """Look up the forward FlowEdge corresponding to a domain road_id."""
        return self.get_forward_edge(EdgeKind.ROAD, road_id)

    def get_super_source_edge(self, area_node_id: str) -> FlowEdge:
        """Look up the Super-Source -> AffectedArea edge."""
        return self.get_forward_edge(EdgeKind.SUPER_SOURCE, area_node_id)

    def get_super_sink_edge(self, shelter_node_id: str) -> FlowEdge:
        """Look up the Shelter -> Super-Sink edge."""
        return self.get_forward_edge(EdgeKind.SUPER_SINK, shelter_node_id)

    def get_edges_by_kind(self, edge_kind: EdgeKind) -> list[FlowEdge]:
        """Return all forward edges matching the requested EdgeKind."""
        return [
            self.adj[u_idx][pos]
            for (kind, _), (u_idx, pos) in self._forward_edge_refs.items()
            if kind == edge_kind
        ]

    def get_road_edges(self) -> list[FlowEdge]:
        """Return all forward physical road edges."""
        return self.get_edges_by_kind(EdgeKind.ROAD)

    def get_super_source_edges(self) -> list[FlowEdge]:
        """Return all Super-Source -> AffectedArea edges."""
        return self.get_edges_by_kind(EdgeKind.SUPER_SOURCE)

    def get_super_sink_edges(self) -> list[FlowEdge]:
        """Return all Shelter -> Super-Sink edges."""
        return self.get_edges_by_kind(EdgeKind.SUPER_SINK)

    def total_outflow_from_super_source(self) -> int:
        """Compute net flow leaving the virtual Super-Source."""
        return sum(edge.flow for edge in self.get_super_source_edges())

    def total_inflow_to_super_sink(self) -> int:
        """Compute net flow arriving at the virtual Super-Sink."""
        return sum(edge.flow for edge in self.get_super_sink_edges())

    def snapshot_capacities(self) -> dict[str, dict[str, int | str]]:
        """Return a non-mutating snapshot comparing original vs. residual capacities."""
        snapshot: dict[str, dict[str, int | str]] = {}
        for (kind, edge_id), (u_idx, pos) in self._forward_edge_refs.items():
            edge = self.adj[u_idx][pos]
            key = f"{kind.value}:{edge_id}"
            snapshot[key] = {
                "edge_id": edge.edge_id,
                "edge_kind": kind.value,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "original_capacity": edge.original_capacity,
                "residual_capacity": edge.residual_capacity,
                "flow": edge.flow,
            }
        return snapshot

    def verify_flow_invariants(self) -> None:
        """Assert capacity bounds, residual/original separation, and flow conservation."""
        net_balance = [0] * self.num_nodes

        for u_idx, edge_list in enumerate(self.adj):
            for edge_idx, edge in enumerate(edge_list):
                partner = self.adj[edge.to][edge.rev]
                if partner.to != u_idx or partner.rev != edge_idx:
                    raise GraphValidationError(
                        f"Broken reverse pointer on edge '{edge.edge_id}'."
                    )

                if edge.is_forward:
                    if not (0 <= edge.flow <= edge.original_capacity):
                        raise GraphValidationError(
                            f"Capacity bound violated on edge '{edge.edge_id}': "
                            f"flow={edge.flow}, original_capacity={edge.original_capacity}."
                        )
                    expected_residual = edge.original_capacity - edge.flow
                    if edge.residual_capacity != expected_residual:
                        raise GraphValidationError(
                            f"Residual capacity mismatch on edge '{edge.edge_id}': "
                            f"residual={edge.residual_capacity}, expected={expected_residual}."
                        )
                    if partner.original_capacity != 0:
                        raise GraphValidationError(
                            f"Reverse edge for '{edge.edge_id}' must have original_capacity == 0."
                        )
                    if partner.flow != -edge.flow or partner.residual_capacity != edge.flow:
                        raise GraphValidationError(
                            f"Skew/residual symmetry violated on edge '{edge.edge_id}'."
                        )

                    net_balance[u_idx] -= edge.flow
                    net_balance[edge.to] += edge.flow

        for idx, balance in enumerate(net_balance):
            if idx not in (self.super_source_idx, self.super_sink_idx) and balance != 0:
                raise GraphValidationError(
                    f"Flow conservation violated at vertex '{self.node_ids[idx]}': "
                    f"net balance={balance}."
                )

        if net_balance[self.super_source_idx] != -net_balance[self.super_sink_idx]:
            raise GraphValidationError(
                "Super-Source outflow does not equal Super-Sink inflow."
            )
