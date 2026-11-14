"""Centralized Streamlit session-state controller for ResQ."""

from dataclasses import dataclass
from datetime import datetime
import streamlit as st

from resq.domain.enums import GreedyRule
from resq.domain.exceptions import ResQError
from resq.domain.models import EvacuationNetwork
from resq.domain.results import AlgorithmComparisonResult, DijkstraResult
from resq.services.comparator import compare_dinic_vs_greedy
from resq.services.evacuation_simulator import (
    DisruptionSpec,
    FullAnalysisBundle,
    apply_disruptions,
    run_full_evacuation_analysis,
)
from resq.services.presets import load_preset_network

PAGES: tuple[str, ...] = (
    "Overview",
    "Network Builder",
    "Live Simulation",
    "Flow Analysis",
    "Bottleneck Analysis",
    "Scenario Lab",
    "Algorithm Comparison",
    "Shortest Path (Dijkstra)",
    "Reports",
    "About ResQ",
)


@dataclass
class SavedScenarioRecord:
    """Snapshot stored in Scenario Lab for side-by-side multi-scenario comparison."""

    scenario_id: str
    label: str
    saved_at: str
    network: EvacuationNetwork
    bundle: FullAnalysisBundle | None = None


def init_session_state() -> None:
    """Initialize all persistent session state keys on first application load."""
    if "resq_initialized" not in st.session_state:
        st.session_state["resq_initialized"] = True
        st.session_state["active_page"] = "Overview"
        st.session_state["nav_radio"] = "Overview"
        st.session_state["_pending_page"] = None
        st.session_state["active_network"] = load_preset_network("metro_flood_baseline")
        st.session_state["active_preset_key"] = "metro_flood_baseline"
        st.session_state["network_revision"] = 1
        st.session_state["analysis_bundle"] = None
        st.session_state["analysis_timestamp"] = None
        st.session_state["sim_disruption"] = DisruptionSpec()
        st.session_state["sim_bundle"] = None
        st.session_state["comparison_result"] = None
        st.session_state["saved_scenarios"] = {}
        st.session_state["scenario_lab_suite"] = {}
        st.session_state["scalability_report"] = None
        st.session_state["dijkstra_result"] = None
        st.session_state["flash_message"] = None
        st.session_state["playback_step"] = 0
        st.session_state["playback_playing"] = False
        st.session_state["playback_target"] = "base"

    pending = st.session_state.get("_pending_page")
    if pending in PAGES:
        st.session_state["active_page"] = pending
        st.session_state["nav_radio"] = pending
        st.session_state["_pending_page"] = None


def navigate_to(page_name: str) -> None:
    """Queue navigation to a target page and trigger an immediate rerun."""
    if page_name in PAGES:
        st.session_state["_pending_page"] = page_name
        st.rerun()


def set_flash(level: str, text: str) -> None:
    """Store a transient status notification displayed on the next render."""
    st.session_state["flash_message"] = (level, text)


def consume_flash() -> tuple[str, str] | None:
    """Pop and return any pending status notification."""
    msg = st.session_state.get("flash_message")
    st.session_state["flash_message"] = None
    return msg


def get_active_network() -> EvacuationNetwork:
    """Return the working EvacuationNetwork currently loaded in session state."""
    return st.session_state["active_network"]


def get_analysis_bundle() -> FullAnalysisBundle | None:
    """Return the latest valid FullAnalysisBundle, or None if not yet analyzed."""
    return st.session_state.get("analysis_bundle")


def invalidate_analysis(*, bump_revision: bool = True) -> None:
    """Clear derived flow/bottleneck/simulation results whenever topology changes."""
    st.session_state["analysis_bundle"] = None
    st.session_state["analysis_timestamp"] = None
    st.session_state["sim_bundle"] = None
    st.session_state["comparison_result"] = None
    st.session_state["scenario_lab_suite"] = {}
    st.session_state["dijkstra_result"] = None
    st.session_state["playback_step"] = 0
    st.session_state["playback_playing"] = False
    st.session_state["playback_target"] = "base"
    if bump_revision:
        st.session_state["network_revision"] = (
            st.session_state.get("network_revision", 1) + 1
        )


def load_demo_network(preset_key: str = "metro_flood_baseline") -> tuple[bool, str]:
    """Load a built-in preset topology and clear stale derived results."""
    try:
        net = load_preset_network(preset_key)
    except ResQError as exc:
        return False, str(exc)

    st.session_state["active_network"] = net
    st.session_state["active_preset_key"] = preset_key
    st.session_state["sim_disruption"] = DisruptionSpec()
    invalidate_analysis()
    return True, f"Loaded preset network '{net.name}'."


def reset_network_to_empty() -> None:
    """Reset the working workspace to a clean empty network."""
    st.session_state["active_network"] = EvacuationNetwork(
        network_id="custom-network",
        name="Custom Evacuation Network",
        description="User-defined disaster evacuation graph.",
    )
    st.session_state["active_preset_key"] = None
    st.session_state["sim_disruption"] = DisruptionSpec()
    invalidate_analysis()


def reset_workspace() -> str:
    """Reset any active simulation disruptions and clear unpersisted analysis state."""
    st.session_state["sim_disruption"] = DisruptionSpec()
    invalidate_analysis(bump_revision=False)
    return "Analysis results and temporary disruptions reset."


def run_primary_analysis(
    *,
    trace: bool = True,
    wave_hours: int = 8,
    upgrade_delta: int = 100,
) -> tuple[bool, str]:
    """Execute Dinic Max-Flow, Min-Cut, route decomposition, and upgrade analysis."""
    net = get_active_network()
    report = net.validate()
    if not report.is_valid:
        return False, " ".join(report.errors)

    try:
        bundle = run_full_evacuation_analysis(
            net,
            trace=trace,
            wave_hours=wave_hours,
            upgrade_delta=upgrade_delta,
        )
        default_comp = compare_dinic_vs_greedy(
            net, greedy_rule=GreedyRule.SHORTEST_HOP, repeats=3, trace=False
        )
    except ResQError as exc:
        return False, str(exc)

    st.session_state["analysis_bundle"] = bundle
    st.session_state["comparison_result"] = default_comp
    st.session_state["analysis_timestamp"] = datetime.now().strftime("%H:%M:%S")
    st.session_state["playback_step"] = 0
    st.session_state["playback_playing"] = False
    return (
        True,
        f"Dinic analysis complete: Max Flow = {bundle.dinic_result.max_flow:,} "
        f"({bundle.dinic_result.execution_time_ms:.3f} ms).",
    )


def run_simulation_overlay(disruption: DisruptionSpec, *, wave_hours: int = 8) -> tuple[bool, str]:
    """Apply temporary disruption overrides on a copy and run full analysis."""
    base_net = get_active_network()
    report = base_net.validate()
    if not report.is_valid:
        return False, " ".join(report.errors)

    try:
        sim_net = apply_disruptions(base_net, disruption)
        sim_bundle = run_full_evacuation_analysis(
            sim_net,
            trace=True,
            wave_hours=wave_hours,
            upgrade_delta=100,
        )
    except ResQError as exc:
        return False, str(exc)

    st.session_state["sim_disruption"] = disruption
    st.session_state["sim_bundle"] = sim_bundle
    st.session_state["playback_step"] = 0
    st.session_state["playback_playing"] = False
    return (
        True,
        f"Simulation evaluated: Disrupted Max Flow = {sim_bundle.dinic_result.max_flow:,}.",
    )


def save_current_scenario(custom_label: str | None = None) -> tuple[bool, str]:
    """Save an independent snapshot of the current network (and analysis if valid)."""
    net = get_active_network()
    saved_map: dict[str, SavedScenarioRecord] = st.session_state["saved_scenarios"]

    idx = len(saved_map) + 1
    label = (custom_label or "").strip() or f"{net.name} #{idx}"
    scenario_id = f"scn_{idx}_{datetime.now().strftime('%H%M%S')}"

    snapshot_net = net.copy(new_network_id=scenario_id, new_name=label)
    bundle = st.session_state.get("analysis_bundle")
    if bundle is None and snapshot_net.validate().is_valid:
        try:
            bundle = run_full_evacuation_analysis(
                snapshot_net, trace=False, wave_hours=8, upgrade_delta=100
            )
        except ResQError:
            bundle = None

    saved_map[scenario_id] = SavedScenarioRecord(
        scenario_id=scenario_id,
        label=label,
        saved_at=datetime.now().strftime("%H:%M:%S"),
        network=snapshot_net,
        bundle=bundle,
    )
    return True, f"Saved scenario '{label}' to Scenario Lab."


def save_simulated_scenario(label: str | None = None) -> tuple[bool, str]:
    """Save the active disrupted simulation network into Scenario Lab."""
    sim_bundle: FullAnalysisBundle | None = st.session_state.get("sim_bundle")
    if sim_bundle is None:
        return False, "Run a disruption simulation first before saving."
    saved_map: dict[str, SavedScenarioRecord] = st.session_state["saved_scenarios"]
    idx = len(saved_map) + 1
    clean_label = (label or "").strip() or f"Disrupted Scenario #{idx}"
    scenario_id = f"sim_{idx}_{datetime.now().strftime('%H%M%S')}"
    snapshot_net = sim_bundle.network.copy(new_network_id=scenario_id, new_name=clean_label)

    saved_map[scenario_id] = SavedScenarioRecord(
        scenario_id=scenario_id,
        label=clean_label,
        saved_at=datetime.now().strftime("%H:%M:%S"),
        network=snapshot_net,
        bundle=sim_bundle,
    )
    return True, f"Saved disrupted scenario '{clean_label}' to Scenario Lab."


def set_comparison_result(result: AlgorithmComparisonResult | None) -> None:
    """Store Dinic-vs-Greedy comparison output."""
    st.session_state["comparison_result"] = result


def get_comparison_result() -> AlgorithmComparisonResult | None:
    """Retrieve stored Dinic-vs-Greedy comparison output."""
    return st.session_state.get("comparison_result")


def set_dijkstra_result(result: DijkstraResult | None) -> None:
    """Store Dijkstra shortest-path query result."""
    st.session_state["dijkstra_result"] = result


def get_dijkstra_result() -> DijkstraResult | None:
    """Retrieve stored Dijkstra shortest-path query result."""
    return st.session_state.get("dijkstra_result")
