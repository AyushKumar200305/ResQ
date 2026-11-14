"""Thread-safe application state manager for ResQ FastAPI backend."""

import threading
from typing import Sequence

from resq.domain.models import EvacuationNetwork
from resq.domain.results import AlgorithmComparisonResult
from resq.services.evacuation_simulator import FullAnalysisBundle
from resq.services.presets import load_preset_network
from resq.services.scenario_lab import ScenarioEvaluation


class StateManager:
    """Manages active network and cached analysis results across HTTP requests."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current_network: EvacuationNetwork = load_preset_network("metro_flood_baseline")
        self._cached_bundle: FullAnalysisBundle | None = None
        self._cached_comparison: AlgorithmComparisonResult | None = None
        self._cached_scenarios: list[ScenarioEvaluation] = []

    def get_network(self, *, make_copy: bool = True) -> EvacuationNetwork:
        """Return the current active evacuation network."""
        with self._lock:
            return self._current_network.copy() if make_copy else self._current_network

    def set_network(self, network: EvacuationNetwork) -> EvacuationNetwork:
        """Replace the active network and invalidate stale analytical caches."""
        with self._lock:
            self._current_network = network.copy()
            self._cached_bundle = None
            self._cached_comparison = None
            self._cached_scenarios = []
            return self._current_network.copy()

    def reset_to_preset(self, preset_key: str = "metro_flood_baseline") -> EvacuationNetwork:
        """Reset the active network to a built-in preset."""
        fresh = load_preset_network(preset_key)
        return self.set_network(fresh)

    def get_bundle(self) -> FullAnalysisBundle | None:
        """Get cached full analysis bundle if available."""
        with self._lock:
            return self._cached_bundle

    def set_bundle(self, bundle: FullAnalysisBundle) -> None:
        """Cache full analysis bundle."""
        with self._lock:
            self._cached_bundle = bundle

    def get_comparison(self) -> AlgorithmComparisonResult | None:
        """Get cached comparison result if available."""
        with self._lock:
            return self._cached_comparison

    def set_comparison(self, comp: AlgorithmComparisonResult) -> None:
        """Cache algorithm comparison result."""
        with self._lock:
            self._cached_comparison = comp

    def get_scenarios(self) -> list[ScenarioEvaluation]:
        """Get cached scenario evaluations."""
        with self._lock:
            return list(self._cached_scenarios)

    def set_scenarios(self, scenarios: Sequence[ScenarioEvaluation]) -> None:
        """Cache scenario evaluations."""
        with self._lock:
            self._cached_scenarios = list(scenarios)


state_manager = StateManager()
