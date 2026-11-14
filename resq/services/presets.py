"""Built-in disaster evacuation preset catalog and loaders."""

from dataclasses import dataclass
from pathlib import Path

from resq.domain.exceptions import EntityNotFoundError
from resq.domain.models import EvacuationNetwork
from resq.services.scenario_io import load_network_json

_SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"


@dataclass(frozen=True, slots=True)
class PresetDescriptor:
    """Metadata describing a built-in disaster evacuation scenario."""

    key: str
    title: str
    filename: str
    summary: str


PRESET_CATALOG: tuple[PresetDescriptor, ...] = (
    PresetDescriptor(
        key="metro_flood_baseline",
        title="Metro River Basin Flood (Demo)",
        filename="metro_flood_baseline.json",
        summary="3 affected wards, 5 junctions, 3 shelters, and 15 arterial corridors with river-crossing bottlenecks.",
    ),
    PresetDescriptor(
        key="bridge_collapse_crisis",
        title="Earthquake Bridge Collapse",
        filename="bridge_collapse_crisis.json",
        summary="Metro grid under severe seismic failure: North Ridgeway Bridge severed and Civic Arena intake reduced.",
    ),
    PresetDescriptor(
        key="coastal_cyclone_surge",
        title="Coastal Cyclone Surge",
        filename="coastal_cyclone_surge.json",
        summary="Coastal evacuation featuring parallel causeways and inland shelter capacity limits.",
    ),
    PresetDescriptor(
        key="greedy_trap_benchmark",
        title="DAA Benchmark: Greedy Trap",
        filename="greedy_trap_benchmark.json",
        summary="Counterexample where Shortest-Hop Greedy achieves 1,000 flow while Dinic reroutes to 2,000 optimal flow.",
    ),
)

COLLEGE_DEMO_DESCRIPTOR = PresetDescriptor(
    key="presentation_demo_dataset",
    title="College Presentation Demo (Prompt 4)",
    filename="presentation_demo_dataset.json",
    summary="Official 5 hazard zones (5,500 pop), 10 junctions, 4 shelters (5,100 cap), and 26 directed corridors with alternative paths and shared bottlenecks.",
)

_PRESETS_BY_KEY: dict[str, PresetDescriptor] = {p.key: p for p in PRESET_CATALOG}
_PRESETS_BY_KEY["presentation_demo_dataset"] = COLLEGE_DEMO_DESCRIPTOR
_PRESETS_BY_KEY["college_demo"] = COLLEGE_DEMO_DESCRIPTOR


def list_presets(include_all: bool = False) -> tuple[PresetDescriptor, ...]:
    """Return built-in preset scenario descriptors."""
    if include_all:
        return (COLLEGE_DEMO_DESCRIPTOR,) + PRESET_CATALOG
    return PRESET_CATALOG


def load_preset_network(preset_key: str = "metro_flood_baseline") -> EvacuationNetwork:
    """Load and return a fresh EvacuationNetwork copy for the requested preset key."""
    if preset_key not in _PRESETS_BY_KEY:
        valid = ", ".join(_PRESETS_BY_KEY)
        raise EntityNotFoundError(
            f"Unknown preset '{preset_key}'. Available presets: {valid}."
        )
    descriptor = _PRESETS_BY_KEY[preset_key]
    return load_network_json(_SCENARIOS_DIR / descriptor.filename)
