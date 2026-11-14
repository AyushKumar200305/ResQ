"""Domain enumerations for ResQ evacuation networks and solvers."""

from enum import Enum

from resq.domain.exceptions import GraphValidationError


class NodeType(str, Enum):
    """Classification of vertices within a disaster-affected road network."""

    AFFECTED_AREA = "affected_area"
    JUNCTION = "junction"
    SHELTER = "shelter"

    @classmethod
    def parse(cls, value: "NodeType | str") -> "NodeType":
        """Normalize a string or NodeType into a canonical NodeType enum value."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise GraphValidationError(
                f"node_type must be a NodeType or string, got {type(value).__name__}."
            )
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == normalized:
                return member
        valid = ", ".join(m.value for m in cls)
        raise GraphValidationError(
            f"Invalid node_type '{value}'. Expected one of: {valid}."
        )


class GreedyRule(str, Enum):
    """Deterministic forward-only path selection rules for the Greedy baseline."""

    SHORTEST_HOP = "shortest_hop"
    WIDEST_PATH = "widest_path"
    LEXICOGRAPHIC_DFS = "lexicographic_dfs"

    @classmethod
    def parse(cls, value: "GreedyRule | str") -> "GreedyRule":
        """Normalize a string or GreedyRule into a canonical GreedyRule enum value."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise GraphValidationError(
                f"greedy_rule must be a GreedyRule or string, got {type(value).__name__}."
            )
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == normalized:
                return member
        valid = ", ".join(m.value for m in cls)
        raise GraphValidationError(
            f"Invalid greedy_rule '{value}'. Expected one of: {valid}."
        )
