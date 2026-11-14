"""Validation primitives and network-level graph integrity checks."""

from dataclasses import dataclass, field
import math
from typing import TYPE_CHECKING, Any

from resq.domain.enums import NodeType
from resq.domain.exceptions import GraphValidationError

if TYPE_CHECKING:
    from resq.domain.models import EvacuationNetwork

SCHEMA_VERSION = "1.0"
SUPER_SOURCE_ID = "__SUPER_SOURCE__"
SUPER_SINK_ID = "__SUPER_SINK__"
RESERVED_NODE_IDS = frozenset({SUPER_SOURCE_ID, SUPER_SINK_ID})


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Structured result of network readiness and integrity validation."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def raise_if_invalid(self) -> None:
        """Raise GraphValidationError summarizing all errors if the graph is invalid."""
        if not self.is_valid:
            joined = "; ".join(self.errors)
            raise GraphValidationError(f"Evacuation network validation failed: {joined}")


def validate_identifier(
    value: Any,
    field_name: str,
    *,
    reserved: frozenset[str] = frozenset(),
) -> str:
    """Validate that an identifier is a non-empty, untrimmed-free, non-reserved string."""
    if not isinstance(value, str):
        raise GraphValidationError(
            f"{field_name} must be a string, got {type(value).__name__}."
        )
    if not value or not value.strip():
        raise GraphValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip():
        raise GraphValidationError(
            f"{field_name} ('{value}') must not contain leading or trailing whitespace."
        )
    if value in reserved:
        raise GraphValidationError(
            f"{field_name} '{value}' is reserved for internal flow modeling."
        )
    return value


def validate_name(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    """Validate a human-readable label string."""
    if not isinstance(value, str):
        raise GraphValidationError(
            f"{field_name} must be a string, got {type(value).__name__}."
        )
    stripped = value.strip()
    if not allow_empty and not stripped:
        raise GraphValidationError(f"{field_name} must be a non-empty string.")
    return stripped


def validate_non_negative_int(value: Any, field_name: str) -> int:
    """Validate that a numeric capacity or population value is a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphValidationError(
            f"{field_name} must be an integer, got {type(value).__name__}."
        )
    if value < 0:
        raise GraphValidationError(
            f"{field_name} must be non-negative, got {value}."
        )
    return value


def validate_non_negative_float(value: Any, field_name: str) -> float:
    """Validate that a continuous scalar (e.g., travel time) is a finite non-negative float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphValidationError(
            f"{field_name} must be a number, got {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise GraphValidationError(f"{field_name} must be finite, got {value}.")
    if numeric < 0.0:
        raise GraphValidationError(
            f"{field_name} must be non-negative, got {numeric}."
        )
    return numeric


def validate_optional_coordinate(value: Any, field_name: str) -> float | None:
    """Validate an optional spatial coordinate."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphValidationError(
            f"{field_name} must be a number or None, got {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise GraphValidationError(f"{field_name} must be finite, got {value}.")
    return numeric


def validate_node_configuration(
    node_type: NodeType,
    population: int,
    shelter_capacity: int,
) -> None:
    """Enforce role-specific constraints across affected areas, junctions, and shelters."""
    if node_type == NodeType.AFFECTED_AREA:
        if shelter_capacity != 0:
            raise GraphValidationError(
                "Affected area nodes cannot declare shelter_capacity (must be 0)."
            )
    elif node_type == NodeType.JUNCTION:
        if population != 0 or shelter_capacity != 0:
            raise GraphValidationError(
                "Junction nodes must have both population == 0 and shelter_capacity == 0."
            )
    elif node_type == NodeType.SHELTER:
        if population != 0:
            raise GraphValidationError(
                "Shelter nodes cannot declare affected population (must be 0)."
            )
    else:
        raise GraphValidationError(f"Unsupported node type: {node_type}.")


def validate_network(network: "EvacuationNetwork") -> ValidationReport:
    """Validate structural integrity and evacuation readiness of an EvacuationNetwork."""
    errors: list[str] = []
    warnings: list[str] = []

    nodes = network.nodes
    roads = network.roads

    for key, node in nodes.items():
        if key != node.node_id:
            errors.append(
                f"Node registry mismatch: key '{key}' does not match node_id '{node.node_id}'."
            )
        try:
            validate_node_configuration(
                node.node_type,
                node.population,
                node.shelter_capacity,
            )
        except GraphValidationError as exc:
            errors.append(f"Node '{node.node_id}': {exc}")

    for key, road in roads.items():
        if key != road.road_id:
            errors.append(
                f"Road registry mismatch: key '{key}' does not match road_id '{road.road_id}'."
            )
        if road.source_id not in nodes:
            errors.append(
                f"Road '{road.road_id}' references missing source node '{road.source_id}'."
            )
        if road.target_id not in nodes:
            errors.append(
                f"Road '{road.road_id}' references missing target node '{road.target_id}'."
            )
        if road.source_id == road.target_id:
            errors.append(
                f"Road '{road.road_id}' cannot connect node '{road.source_id}' to itself."
            )

    affected_areas = network.affected_areas
    shelters = network.shelters

    if not affected_areas:
        errors.append("Network must contain at least one affected_area node.")
    if not shelters:
        errors.append("Network must contain at least one shelter node.")

    if affected_areas and shelters:
        total_pop = network.total_population
        total_shelter_cap = network.total_shelter_capacity

        if total_pop == 0:
            warnings.append(
                "Total affected population across all sources is 0; max evacuation flow will be 0."
            )
        if total_shelter_cap == 0:
            warnings.append(
                "Total capacity across all shelters is 0; max evacuation flow will be 0."
            )
        if total_pop > total_shelter_cap:
            warnings.append(
                f"Total affected population ({total_pop}) exceeds total shelter capacity "
                f"({total_shelter_cap}); complete evacuation is impossible without shelter expansion."
            )

        for area in affected_areas:
            outgoing_active = [
                r for r in network.get_outgoing_roads(area.node_id) if r.effective_capacity > 0
            ]
            if area.population > 0 and not outgoing_active:
                warnings.append(
                    f"Affected area '{area.node_id}' ({area.name}) has population {area.population} "
                    "but no active outgoing roads with positive capacity."
                )

        for shelter in shelters:
            incoming_active = [
                r for r in network.get_incoming_roads(shelter.node_id) if r.effective_capacity > 0
            ]
            if shelter.shelter_capacity > 0 and not incoming_active:
                warnings.append(
                    f"Shelter '{shelter.node_id}' ({shelter.name}) has capacity {shelter.shelter_capacity} "
                    "but no active incoming roads with positive capacity."
                )

    return ValidationReport(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_network_or_raise(network: "EvacuationNetwork") -> ValidationReport:
    """Validate the evacuation network and raise GraphValidationError on any error."""
    report = validate_network(network)
    report.raise_if_invalid()
    return report
