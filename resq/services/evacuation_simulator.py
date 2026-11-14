"""Evacuation simulation services: disruption sandboxing, wave projections, and upgrade ROI."""

from dataclasses import dataclass, field

from resq.algorithms.dinic import DinicSolver
from resq.algorithms.flow_builder import build_evacuation_network
from resq.algorithms.min_cut import MinCutExtractor
from resq.algorithms.path_decomposition import (
    EvacuationRoute,
    decompose_evacuation_routes,
)
from resq.domain.enums import NodeType
from resq.domain.exceptions import GraphValidationError
from resq.domain.models import EvacuationNetwork
from resq.domain.results import DinicResult, MinCutResult


@dataclass(frozen=True, slots=True)
class DisruptionSpec:
    """Non-destructive disaster disruption overlay applied to a base EvacuationNetwork."""

    disabled_roads: frozenset[str] = field(default_factory=frozenset)
    road_capacity_factors: dict[str, float] = field(default_factory=dict)
    disabled_shelters: frozenset[str] = field(default_factory=frozenset)
    demand_multipliers: dict[str, float] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Return True if any disruption modifier is active."""
        return bool(
            self.disabled_roads
            or any(abs(f - 1.0) > 1e-9 for f in self.road_capacity_factors.values())
            or self.disabled_shelters
            or any(abs(m - 1.0) > 1e-9 for m in self.demand_multipliers.values())
        )


@dataclass(frozen=True, slots=True)
class WaveStep:
    """One discrete time-horizon wave in multi-hour evacuation projection."""

    hour: int
    evacuated_this_hour: int
    cumulative_evacuated: int
    remaining_population: int
    remaining_shelter_capacity: int
    completion_pct: float


@dataclass(frozen=True, slots=True)
class UpgradeCandidate:
    """Exact marginal flow impact of expanding a bottleneck road or shelter."""

    target_id: str
    target_kind: str  # "road" or "shelter"
    label: str
    current_capacity: int
    added_capacity: int
    base_max_flow: int
    new_max_flow: int
    marginal_flow_gain: int
    gain_per_unit: float


@dataclass(frozen=True, slots=True)
class FullAnalysisBundle:
    """Complete mathematical diagnostic snapshot consumed by UI pages."""

    network: EvacuationNetwork
    dinic_result: DinicResult
    min_cut: MinCutResult
    routes: tuple[EvacuationRoute, ...]
    upgrade_candidates: tuple[UpgradeCandidate, ...]
    wave_timeline: tuple[WaveStep, ...]


def apply_disruptions(
    base_network: EvacuationNetwork,
    disruption: DisruptionSpec,
) -> EvacuationNetwork:
    """Create a modified scenario copy with road closures, capacity drops, and surges."""
    modified = base_network.copy(
        new_network_id=f"{base_network.network_id}-sim",
        new_name=f"{base_network.name} (Simulated)",
    )

    for road_id in disruption.disabled_roads:
        if road_id in modified.roads:
            modified.edit_road(road_id, is_active=False)

    for road_id, factor in disruption.road_capacity_factors.items():
        if road_id in modified.roads:
            if factor < 0.0:
                raise GraphValidationError(
                    f"Capacity factor for road '{road_id}' must be >= 0, got {factor}."
                )
            road = modified.get_road(road_id)
            scaled_cap = max(0, int(round(road.capacity * factor)))
            modified.edit_road(road_id, capacity=scaled_cap)

    for shelter_id in disruption.disabled_shelters:
        if shelter_id in modified.nodes:
            node = modified.get_node(shelter_id)
            if node.node_type == NodeType.SHELTER:
                modified.edit_node(shelter_id, shelter_capacity=0)

    for area_id, mult in disruption.demand_multipliers.items():
        if area_id in modified.nodes:
            node = modified.get_node(area_id)
            if node.node_type == NodeType.AFFECTED_AREA:
                if mult < 0.0:
                    raise GraphValidationError(
                        f"Demand multiplier for '{area_id}' must be >= 0, got {mult}."
                    )
                scaled_pop = max(0, int(round(node.population * mult)))
                modified.edit_node(area_id, population=scaled_pop)

    return modified


def simulate_evacuation_waves(
    network: EvacuationNetwork,
    *,
    max_hours: int = 12,
) -> list[WaveStep]:
    """Project cumulative evacuation across discrete hourly waves using iterative Dinic runs.

    Road capacities represent hourly corridor throughput (people/hour), while initial
    populations and shelter capacities represent total evacuees and total bed intake.
    """
    if max_hours < 1:
        raise GraphValidationError(f"max_hours must be >= 1, got {max_hours}.")

    working = network.copy()
    initial_pop = working.total_population
    cumulative = 0
    timeline: list[WaveStep] = []
    solver = DinicSolver()

    for hour in range(1, max_hours + 1):
        remaining_pop = working.total_population
        remaining_beds = working.total_shelter_capacity

        if remaining_pop == 0 or remaining_beds == 0:
            timeline.append(
                WaveStep(
                    hour=hour,
                    evacuated_this_hour=0,
                    cumulative_evacuated=cumulative,
                    remaining_population=remaining_pop,
                    remaining_shelter_capacity=remaining_beds,
                    completion_pct=(cumulative / initial_pop * 100.0)
                    if initial_pop > 0
                    else 100.0,
                )
            )
            continue

        flow_net = build_evacuation_network(working)
        res = solver.solve(
            flow_net,
            domain_network=working,
            trace=False,
            reset=False,
            verify_invariants=False,
        )
        moved = res.max_flow
        cumulative += moved

        for area_id, src_detail in res.source_evacuations.items():
            working.edit_node(area_id, population=src_detail.unmet_demand)
        for shelter_id, shl_detail in res.shelter_intakes.items():
            working.edit_node(shelter_id, shelter_capacity=shl_detail.remaining_capacity)

        timeline.append(
            WaveStep(
                hour=hour,
                evacuated_this_hour=moved,
                cumulative_evacuated=cumulative,
                remaining_population=working.total_population,
                remaining_shelter_capacity=working.total_shelter_capacity,
                completion_pct=(cumulative / initial_pop * 100.0)
                if initial_pop > 0
                else 100.0,
            )
        )

        if moved == 0:
            # No further paths or shelter capacity available; fill remaining horizon flat.
            for rem_hr in range(hour + 1, max_hours + 1):
                timeline.append(
                    WaveStep(
                        hour=rem_hr,
                        evacuated_this_hour=0,
                        cumulative_evacuated=cumulative,
                        remaining_population=working.total_population,
                        remaining_shelter_capacity=working.total_shelter_capacity,
                        completion_pct=(cumulative / initial_pop * 100.0)
                        if initial_pop > 0
                        else 100.0,
                    )
                )
            break

    return timeline


def analyze_upgrade_sensitivity(
    network: EvacuationNetwork,
    base_max_flow: int,
    min_cut: MinCutResult,
    *,
    delta_capacity: int = 100,
) -> list[UpgradeCandidate]:
    """Test +delta_capacity expansions on bottleneck roads & shelters using Dinic's solver."""
    if delta_capacity < 1:
        raise GraphValidationError(
            f"delta_capacity must be >= 1, got {delta_capacity}."
        )

    candidates: list[UpgradeCandidate] = []
    solver = DinicSolver()

    # Candidate roads: min-cut road bottlenecks + any inactive roads (potential restoration)
    candidate_road_ids: list[str] = []
    seen_roads: set[str] = set()
    for cut_edge in min_cut.road_bottlenecks:
        if cut_edge.edge_id not in seen_roads:
            candidate_road_ids.append(cut_edge.edge_id)
            seen_roads.add(cut_edge.edge_id)
    for road_id, road in network.roads.items():
        if not road.is_active and road_id not in seen_roads:
            candidate_road_ids.append(road_id)
            seen_roads.add(road_id)

    for road_id in candidate_road_ids:
        road = network.get_road(road_id)
        trial = network.copy()
        if not road.is_active:
            trial.edit_road(road_id, is_active=True, capacity=max(road.capacity, delta_capacity))
            added = trial.get_road(road_id).effective_capacity
            label = f"Reopen {road.road_id} ({road.source_id} -> {road.target_id})"
        else:
            trial.edit_road(road_id, capacity=road.capacity + delta_capacity)
            added = delta_capacity
            label = f"Expand {road.road_id} ({road.source_id} -> {road.target_id})"

        flow_net = build_evacuation_network(trial)
        res = solver.solve(flow_net, trace=False, reset=False, verify_invariants=False)
        gain = res.max_flow - base_max_flow
        candidates.append(
            UpgradeCandidate(
                target_id=road_id,
                target_kind="road",
                label=label,
                current_capacity=road.effective_capacity,
                added_capacity=added,
                base_max_flow=base_max_flow,
                new_max_flow=res.max_flow,
                marginal_flow_gain=gain,
                gain_per_unit=(gain / added) if added > 0 else 0.0,
            )
        )

    for cut_shelter in min_cut.shelter_capacity_cuts:
        shelter_id = cut_shelter.edge_id
        shelter = network.get_node(shelter_id)
        trial = network.copy()
        trial.edit_node(
            shelter_id,
            shelter_capacity=shelter.shelter_capacity + delta_capacity,
        )
        flow_net = build_evacuation_network(trial)
        res = solver.solve(flow_net, trace=False, reset=False, verify_invariants=False)
        gain = res.max_flow - base_max_flow
        candidates.append(
            UpgradeCandidate(
                target_id=shelter_id,
                target_kind="shelter",
                label=f"Expand Shelter {shelter.name} ({shelter_id})",
                current_capacity=shelter.shelter_capacity,
                added_capacity=delta_capacity,
                base_max_flow=base_max_flow,
                new_max_flow=res.max_flow,
                marginal_flow_gain=gain,
                gain_per_unit=gain / delta_capacity,
            )
        )

    candidates.sort(key=lambda c: (-c.marginal_flow_gain, -c.gain_per_unit, c.target_id))
    return candidates


def run_full_evacuation_analysis(
    network: EvacuationNetwork,
    *,
    trace: bool = True,
    wave_hours: int = 8,
    upgrade_delta: int = 100,
) -> FullAnalysisBundle:
    """Execute Dinic max-flow, min-cut extraction, path decomposition, waves, and upgrade ROI."""
    flow_network = build_evacuation_network(network)
    dinic_result = DinicSolver().solve(
        flow_network,
        domain_network=network,
        trace=trace,
        reset=False,
        verify_invariants=True,
    )
    min_cut = MinCutExtractor().extract(
        flow_network,
        domain_network=network,
        expected_max_flow=dinic_result.max_flow,
    )
    routes = tuple(
        decompose_evacuation_routes(flow_network, domain_network=network)
    )
    upgrade_candidates = tuple(
        analyze_upgrade_sensitivity(
            network,
            dinic_result.max_flow,
            min_cut,
            delta_capacity=upgrade_delta,
        )
    )
    wave_timeline = tuple(
        simulate_evacuation_waves(network, max_hours=wave_hours)
    )
    return FullAnalysisBundle(
        network=network,
        dinic_result=dinic_result,
        min_cut=min_cut,
        routes=routes,
        upgrade_candidates=upgrade_candidates,
        wave_timeline=wave_timeline,
    )
