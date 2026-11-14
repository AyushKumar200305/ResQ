"""Core graph domain models for ResQ disaster evacuation networks."""

import copy
from dataclasses import dataclass, field
import json
from types import MappingProxyType
from typing import Any, Mapping

from resq.domain.enums import NodeType
from resq.domain.exceptions import (
    DuplicateIdentifierError,
    EntityNotFoundError,
    GraphValidationError,
    NetworkSerializationError,
)
from resq.domain.validation import (
    RESERVED_NODE_IDS,
    SCHEMA_VERSION,
    ValidationReport,
    validate_identifier,
    validate_name,
    validate_network,
    validate_node_configuration,
    validate_non_negative_float,
    validate_non_negative_int,
    validate_optional_coordinate,
)

_UNSET: Any = object()


@dataclass(frozen=True, slots=True)
class Node:
    """Directed graph vertex representing an affected area, junction, or shelter."""

    node_id: str
    name: str
    node_type: NodeType
    population: int = 0
    shelter_capacity: int = 0
    x: float | None = None
    y: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        clean_id = validate_identifier(
            self.node_id, "node_id", reserved=RESERVED_NODE_IDS
        )
        clean_name = validate_name(self.name, "name")
        parsed_type = NodeType.parse(self.node_type)
        clean_pop = validate_non_negative_int(self.population, "population")
        clean_cap = validate_non_negative_int(self.shelter_capacity, "shelter_capacity")
        validate_node_configuration(parsed_type, clean_pop, clean_cap)
        clean_x = validate_optional_coordinate(self.x, "x")
        clean_y = validate_optional_coordinate(self.y, "y")

        if not isinstance(self.metadata, dict):
            raise GraphValidationError(
                f"metadata must be a dict, got {type(self.metadata).__name__}."
            )
        clean_meta = copy.deepcopy(self.metadata)

        object.__setattr__(self, "node_id", clean_id)
        object.__setattr__(self, "name", clean_name)
        object.__setattr__(self, "node_type", parsed_type)
        object.__setattr__(self, "population", clean_pop)
        object.__setattr__(self, "shelter_capacity", clean_cap)
        object.__setattr__(self, "x", clean_x)
        object.__setattr__(self, "y", clean_y)
        object.__setattr__(self, "metadata", clean_meta)

    def copy(self) -> "Node":
        """Return an independent copy of this node."""
        return Node(
            node_id=self.node_id,
            name=self.name,
            node_type=self.node_type,
            population=self.population,
            shelter_capacity=self.shelter_capacity,
            x=self.x,
            y=self.y,
            metadata=copy.deepcopy(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize node fields to a JSON-compatible dictionary."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "population": self.population,
            "shelter_capacity": self.shelter_capacity,
            "x": self.x,
            "y": self.y,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Node":
        """Construct and validate a Node from a dictionary."""
        if not isinstance(data, Mapping):
            raise NetworkSerializationError(
                f"Node entry must be a mapping, got {type(data).__name__}."
            )
        for required_key in ("node_id", "name", "node_type"):
            if required_key not in data:
                raise NetworkSerializationError(
                    f"Node entry missing required key '{required_key}'."
                )
        return cls(
            node_id=data["node_id"],
            name=data["name"],
            node_type=data["node_type"],
            population=data.get("population", 0),
            shelter_capacity=data.get("shelter_capacity", 0),
            x=data.get("x"),
            y=data.get("y"),
            metadata=data.get("metadata", {}) or {},
        )


@dataclass(frozen=True, slots=True)
class RoadEdge:
    """Directed weighted road connecting two distinct vertices with capacity and distance."""

    road_id: str
    source_id: str
    target_id: str
    capacity: int
    name: str = ""
    distance: float = 1.0
    travel_time_min: float = 0.0
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        clean_id = validate_identifier(self.road_id, "road_id")
        clean_src = validate_identifier(
            self.source_id, "source_id", reserved=RESERVED_NODE_IDS
        )
        clean_dst = validate_identifier(
            self.target_id, "target_id", reserved=RESERVED_NODE_IDS
        )
        if clean_src == clean_dst:
            raise GraphValidationError(
                f"Road '{clean_id}' cannot be a self-loop on node '{clean_src}'."
            )
        clean_cap = validate_non_negative_int(self.capacity, "capacity")
        clean_name = validate_name(self.name, "road name", allow_empty=True)
        clean_distance = validate_non_negative_float(self.distance, "distance")
        clean_time = validate_non_negative_float(self.travel_time_min, "travel_time_min")
        if not isinstance(self.is_active, bool):
            raise GraphValidationError(
                f"is_active must be a boolean, got {type(self.is_active).__name__}."
            )
        if not isinstance(self.metadata, dict):
            raise GraphValidationError(
                f"metadata must be a dict, got {type(self.metadata).__name__}."
            )
        clean_meta = copy.deepcopy(self.metadata)

        object.__setattr__(self, "road_id", clean_id)
        object.__setattr__(self, "source_id", clean_src)
        object.__setattr__(self, "target_id", clean_dst)
        object.__setattr__(self, "capacity", clean_cap)
        object.__setattr__(self, "name", clean_name)
        object.__setattr__(self, "distance", clean_distance)
        object.__setattr__(self, "travel_time_min", clean_time)
        object.__setattr__(self, "is_active", self.is_active)
        object.__setattr__(self, "metadata", clean_meta)

    @property
    def effective_capacity(self) -> int:
        """Capacity available for evacuation flow (0 when road is inactive/closed)."""
        return self.capacity if self.is_active else 0

    def copy(self) -> "RoadEdge":
        """Return an independent copy of this directed road."""
        return RoadEdge(
            road_id=self.road_id,
            source_id=self.source_id,
            target_id=self.target_id,
            capacity=self.capacity,
            name=self.name,
            distance=self.distance,
            travel_time_min=self.travel_time_min,
            is_active=self.is_active,
            metadata=copy.deepcopy(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize road edge fields to a JSON-compatible dictionary."""
        return {
            "road_id": self.road_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "capacity": self.capacity,
            "name": self.name,
            "distance": self.distance,
            "travel_time_min": self.travel_time_min,
            "is_active": self.is_active,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RoadEdge":
        """Construct and validate a RoadEdge from a dictionary."""
        if not isinstance(data, Mapping):
            raise NetworkSerializationError(
                f"Road entry must be a mapping, got {type(data).__name__}."
            )
        for required_key in ("road_id", "source_id", "target_id", "capacity"):
            if required_key not in data:
                raise NetworkSerializationError(
                    f"Road entry missing required key '{required_key}'."
                )
        return cls(
            road_id=data["road_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            capacity=data["capacity"],
            name=data.get("name", ""),
            distance=data.get("distance", 1.0),
            travel_time_min=data.get("travel_time_min", 0.0),
            is_active=data.get("is_active", True),
            metadata=data.get("metadata", {}) or {},
        )


class EvacuationNetwork:
    """Directed capacity graph representing a disaster-affected evacuation region."""

    def __init__(
        self,
        *,
        network_id: str = "default",
        name: str = "Untitled Evacuation Network",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.network_id: str = validate_identifier(network_id, "network_id")
        self.name: str = validate_name(name, "network name")
        if not isinstance(description, str):
            raise GraphValidationError(
                f"description must be a string, got {type(description).__name__}."
            )
        self.description: str = description
        if metadata is None:
            self.metadata: dict[str, Any] = {}
        elif isinstance(metadata, dict):
            self.metadata = copy.deepcopy(metadata)
        else:
            raise GraphValidationError(
                f"metadata must be a dict, got {type(metadata).__name__}."
            )
        self._nodes: dict[str, Node] = {}
        self._roads: dict[str, RoadEdge] = {}

    @property
    def nodes(self) -> Mapping[str, Node]:
        """Read-only view of nodes keyed by unique node_id."""
        return MappingProxyType(self._nodes)

    @property
    def roads(self) -> Mapping[str, RoadEdge]:
        """Read-only view of directed roads keyed by unique road_id."""
        return MappingProxyType(self._roads)

    @property
    def affected_areas(self) -> list[Node]:
        """All affected-area source nodes in insertion order."""
        return self.get_nodes_by_type(NodeType.AFFECTED_AREA)

    @property
    def junctions(self) -> list[Node]:
        """All intermediate junction nodes in insertion order."""
        return self.get_nodes_by_type(NodeType.JUNCTION)

    @property
    def shelters(self) -> list[Node]:
        """All shelter destination nodes in insertion order."""
        return self.get_nodes_by_type(NodeType.SHELTER)

    @property
    def total_population(self) -> int:
        """Total evacuee population across all affected areas."""
        return sum(node.population for node in self.affected_areas)

    @property
    def total_shelter_capacity(self) -> int:
        """Total bed/intake capacity across all shelters."""
        return sum(node.shelter_capacity for node in self.shelters)

    @property
    def total_active_road_capacity(self) -> int:
        """Sum of capacities across all currently active directed roads."""
        return sum(road.effective_capacity for road in self._roads.values())

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: NodeType | str,
        *,
        population: int = 0,
        shelter_capacity: int = 0,
        x: float | None = None,
        y: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node:
        """Create and register a validated node in the network."""
        node = Node(
            node_id=node_id,
            name=name,
            node_type=NodeType.parse(node_type),
            population=population,
            shelter_capacity=shelter_capacity,
            x=x,
            y=y,
            metadata={} if metadata is None else metadata,
        )
        return self.insert_node(node)

    def insert_node(self, node: Node) -> Node:
        """Insert a pre-constructed Node instance, enforcing unique node_id."""
        if not isinstance(node, Node):
            raise GraphValidationError(
                f"Expected a Node instance, got {type(node).__name__}."
            )
        if node.node_id in self._nodes:
            raise DuplicateIdentifierError(
                f"Node with identifier '{node.node_id}' already exists."
            )
        stored = node.copy()
        self._nodes[stored.node_id] = stored
        return stored

    def edit_node(
        self,
        node_id: str,
        *,
        name: Any = _UNSET,
        node_type: Any = _UNSET,
        population: Any = _UNSET,
        shelter_capacity: Any = _UNSET,
        x: Any = _UNSET,
        y: Any = _UNSET,
        metadata: Any = _UNSET,
    ) -> Node:
        """Atomically update attributes of an existing node while preserving constraints."""
        existing = self.get_node(node_id)
        updated = Node(
            node_id=existing.node_id,
            name=existing.name if name is _UNSET else name,
            node_type=existing.node_type if node_type is _UNSET else node_type,
            population=existing.population if population is _UNSET else population,
            shelter_capacity=(
                existing.shelter_capacity
                if shelter_capacity is _UNSET
                else shelter_capacity
            ),
            x=existing.x if x is _UNSET else x,
            y=existing.y if y is _UNSET else y,
            metadata=existing.metadata if metadata is _UNSET else metadata,
        )
        self._nodes[existing.node_id] = updated
        return updated

    def delete_node(self, node_id: str, *, cascade: bool = True) -> list[RoadEdge]:
        """Remove a node and optionally cascade-delete its incident directed roads."""
        self.get_node(node_id)
        incident = [
            road
            for road in self._roads.values()
            if road.source_id == node_id or road.target_id == node_id
        ]
        if incident and not cascade:
            road_ids = ", ".join(road.road_id for road in incident)
            raise GraphValidationError(
                f"Cannot delete node '{node_id}' while incident roads exist: {road_ids}."
            )
        for road in incident:
            del self._roads[road.road_id]
        del self._nodes[node_id]
        return incident

    def get_node(self, node_id: str) -> Node:
        """Retrieve a node by ID or raise EntityNotFoundError."""
        if node_id not in self._nodes:
            raise EntityNotFoundError(f"Node '{node_id}' does not exist in network.")
        return self._nodes[node_id]

    def get_nodes_by_type(self, node_type: NodeType | str) -> list[Node]:
        """Return all nodes matching the given NodeType."""
        parsed = NodeType.parse(node_type)
        return [node for node in self._nodes.values() if node.node_type == parsed]

    # ------------------------------------------------------------------
    # Road edge operations
    # ------------------------------------------------------------------

    def add_road(
        self,
        road_id: str,
        source_id: str,
        target_id: str,
        capacity: int,
        *,
        name: str = "",
        distance: float = 1.0,
        travel_time_min: float = 0.0,
        is_active: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> RoadEdge:
        """Create and register a validated directed road between existing nodes."""
        road = RoadEdge(
            road_id=road_id,
            source_id=source_id,
            target_id=target_id,
            capacity=capacity,
            name=name,
            distance=distance,
            travel_time_min=travel_time_min,
            is_active=is_active,
            metadata={} if metadata is None else metadata,
        )
        return self.insert_road(road)

    def insert_road(self, road: RoadEdge) -> RoadEdge:
        """Insert a pre-constructed RoadEdge, verifying endpoints and unique road_id."""
        if not isinstance(road, RoadEdge):
            raise GraphValidationError(
                f"Expected a RoadEdge instance, got {type(road).__name__}."
            )
        if road.road_id in self._roads:
            raise DuplicateIdentifierError(
                f"Road with identifier '{road.road_id}' already exists."
            )
        self._assert_endpoints_exist(road.source_id, road.target_id, road.road_id)
        stored = road.copy()
        self._roads[stored.road_id] = stored
        return stored

    def edit_road(
        self,
        road_id: str,
        *,
        source_id: Any = _UNSET,
        target_id: Any = _UNSET,
        capacity: Any = _UNSET,
        name: Any = _UNSET,
        distance: Any = _UNSET,
        travel_time_min: Any = _UNSET,
        is_active: Any = _UNSET,
        metadata: Any = _UNSET,
    ) -> RoadEdge:
        """Atomically update attributes of an existing road while verifying endpoints."""
        existing = self.get_road(road_id)
        updated = RoadEdge(
            road_id=existing.road_id,
            source_id=existing.source_id if source_id is _UNSET else source_id,
            target_id=existing.target_id if target_id is _UNSET else target_id,
            capacity=existing.capacity if capacity is _UNSET else capacity,
            name=existing.name if name is _UNSET else name,
            distance=existing.distance if distance is _UNSET else distance,
            travel_time_min=(
                existing.travel_time_min
                if travel_time_min is _UNSET
                else travel_time_min
            ),
            is_active=existing.is_active if is_active is _UNSET else is_active,
            metadata=existing.metadata if metadata is _UNSET else metadata,
        )
        self._assert_endpoints_exist(updated.source_id, updated.target_id, updated.road_id)
        self._roads[existing.road_id] = updated
        return updated

    def delete_road(self, road_id: str) -> RoadEdge:
        """Remove and return a directed road by ID."""
        existing = self.get_road(road_id)
        del self._roads[road_id]
        return existing

    def get_road(self, road_id: str) -> RoadEdge:
        """Retrieve a road by ID or raise EntityNotFoundError."""
        if road_id not in self._roads:
            raise EntityNotFoundError(f"Road '{road_id}' does not exist in network.")
        return self._roads[road_id]

    def get_outgoing_roads(self, node_id: str) -> list[RoadEdge]:
        """Return all directed roads originating at node_id."""
        self.get_node(node_id)
        return [road for road in self._roads.values() if road.source_id == node_id]

    def get_incoming_roads(self, node_id: str) -> list[RoadEdge]:
        """Return all directed roads terminating at node_id."""
        self.get_node(node_id)
        return [road for road in self._roads.values() if road.target_id == node_id]

    def get_roads_between(self, source_id: str, target_id: str) -> list[RoadEdge]:
        """Return all parallel directed roads from source_id to target_id."""
        self.get_node(source_id)
        self.get_node(target_id)
        return [
            road
            for road in self._roads.values()
            if road.source_id == source_id and road.target_id == target_id
        ]

    # ------------------------------------------------------------------
    # Validation, Cloning & Serialization
    # ------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Run full structural and evacuation-readiness validation."""
        return validate_network(self)

    def copy(
        self,
        *,
        new_network_id: str | None = None,
        new_name: str | None = None,
    ) -> "EvacuationNetwork":
        """Create a completely independent deep copy of this evacuation network."""
        cloned = EvacuationNetwork(
            network_id=self.network_id if new_network_id is None else new_network_id,
            name=self.name if new_name is None else new_name,
            description=self.description,
            metadata=copy.deepcopy(self.metadata),
        )
        for node in self._nodes.values():
            cloned._nodes[node.node_id] = node.copy()
        for road in self._roads.values():
            cloned._roads[road.road_id] = road.copy()
        return cloned

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire network to a schema-versioned JSON-ready dictionary."""
        return {
            "schema_version": SCHEMA_VERSION,
            "network_id": self.network_id,
            "name": self.name,
            "description": self.description,
            "metadata": copy.deepcopy(self.metadata),
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "roads": [road.to_dict() for road in self._roads.values()],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvacuationNetwork":
        """Deserialize and strictly validate an EvacuationNetwork from a dictionary."""
        if not isinstance(data, Mapping):
            raise NetworkSerializationError(
                f"Network payload must be a JSON object/mapping, got {type(data).__name__}."
            )
        version = data.get("schema_version", SCHEMA_VERSION)
        if version != SCHEMA_VERSION:
            raise NetworkSerializationError(
                f"Unsupported schema_version '{version}'. Expected '{SCHEMA_VERSION}'."
            )

        nodes_raw = data.get("nodes")
        roads_raw = data.get("roads")
        if not isinstance(nodes_raw, list):
            raise NetworkSerializationError("'nodes' must be a JSON array.")
        if not isinstance(roads_raw, list):
            raise NetworkSerializationError("'roads' must be a JSON array.")

        network = cls(
            network_id=data.get("network_id", "default"),
            name=data.get("name", "Imported Evacuation Network"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}) or {},
        )
        for raw_node in nodes_raw:
            node = Node.from_dict(raw_node)
            network.insert_node(node)
        for raw_road in roads_raw:
            road = RoadEdge.from_dict(raw_road)
            network.insert_road(road)
        return network

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the network to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, raw_json: str) -> "EvacuationNetwork":
        """Parse and validate an EvacuationNetwork from a JSON string."""
        if not isinstance(raw_json, str):
            raise NetworkSerializationError(
                f"Expected JSON string, got {type(raw_json).__name__}."
            )
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise NetworkSerializationError(f"Invalid JSON payload: {exc}") from exc
        return cls.from_dict(payload)

    def _assert_endpoints_exist(
        self,
        source_id: str,
        target_id: str,
        road_id: str,
    ) -> None:
        if source_id not in self._nodes:
            raise EntityNotFoundError(
                f"Road '{road_id}' source node '{source_id}' does not exist."
            )
        if target_id not in self._nodes:
            raise EntityNotFoundError(
                f"Road '{road_id}' target node '{target_id}' does not exist."
            )


def copy_network(
    network: EvacuationNetwork,
    *,
    new_network_id: str | None = None,
    new_name: str | None = None,
) -> EvacuationNetwork:
    """Create an independent copy of an EvacuationNetwork."""
    return network.copy(new_network_id=new_network_id, new_name=new_name)
