"""Service wrapper re-exporting build_evacuation_network for Layer 3 callers."""

from resq.algorithms.flow_builder import build_evacuation_network

__all__ = ["build_evacuation_network"]
