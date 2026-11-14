"""Custom exception hierarchy for ResQ domain and graph validation errors."""


class ResQError(Exception):
    """Base exception for all ResQ domain, graph, and simulation errors."""


class GraphValidationError(ResQError, ValueError):
    """Raised when graph topology, node attributes, or road parameters are invalid."""


class DuplicateIdentifierError(GraphValidationError):
    """Raised when attempting to add a node or road with an existing identifier."""


class EntityNotFoundError(GraphValidationError):
    """Raised when referencing a node or road identifier that does not exist."""


class NetworkSerializationError(GraphValidationError):
    """Raised when importing or exporting network data fails schema validation."""
