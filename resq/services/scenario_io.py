"""JSON import, export, file save, and file load utilities for EvacuationNetwork."""

from pathlib import Path
from typing import Any, Mapping

from resq.domain.exceptions import NetworkSerializationError
from resq.domain.models import EvacuationNetwork


def export_network_to_dict(network: EvacuationNetwork) -> dict[str, Any]:
    """Export an EvacuationNetwork to a validated JSON-serializable dictionary."""
    return network.to_dict()


def import_network_from_dict(data: Mapping[str, Any]) -> EvacuationNetwork:
    """Import and validate an EvacuationNetwork from a dictionary."""
    return EvacuationNetwork.from_dict(data)


def export_network_to_json(network: EvacuationNetwork, *, indent: int = 2) -> str:
    """Serialize an EvacuationNetwork to a formatted JSON string."""
    return network.to_json(indent=indent)


def import_network_from_json(raw_json: str) -> EvacuationNetwork:
    """Parse and validate an EvacuationNetwork from a JSON string."""
    return EvacuationNetwork.from_json(raw_json)


def save_network_json(
    network: EvacuationNetwork,
    file_path: str | Path,
    *,
    indent: int = 2,
) -> Path:
    """Write an EvacuationNetwork to a UTF-8 JSON file on disk."""
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(network.to_json(indent=indent), encoding="utf-8")
    return target


def load_network_json(file_path: str | Path) -> EvacuationNetwork:
    """Read and validate an EvacuationNetwork from a JSON file on disk."""
    source = Path(file_path)
    if not source.exists():
        raise NetworkSerializationError(f"Network JSON file not found: '{source}'.")
    try:
        raw = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise NetworkSerializationError(
            f"Unable to read network JSON file '{source}': {exc}"
        ) from exc
    return EvacuationNetwork.from_json(raw)
