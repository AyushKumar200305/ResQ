"""Shelter intake and allocation assessment service.

Evaluates current occupancy, total capacity, available capacity, expected incoming evacuees
(derived from Dinic maximum flow and wave simulations), feasible ingress routes, and saturation timelines.
"""

from typing import Sequence
from resq.domain.enums import NodeType
from resq.domain.models import EvacuationNetwork
from resq.domain.relief_models import ShelterAllocationStatus
from resq.services.evacuation_simulator import FullAnalysisBundle, run_full_evacuation_analysis


def assess_shelter_allocations(
    network: EvacuationNetwork,
    bundle: FullAnalysisBundle | None = None,
) -> list[ShelterAllocationStatus]:
    """Calculate real-time capacity, occupancy, and incoming evacuee assignment for all shelters."""
    if bundle is None:
        bundle = run_full_evacuation_analysis(network, trace=False)

    shelter_nodes = network.shelters
    if not shelter_nodes:
        return []

    dinic_res = bundle.dinic_result
    routes = bundle.routes

    # Aggregate incoming flows and serviced areas per shelter from Dinic solution
    incoming_flow_map: dict[str, int] = {}
    serviced_areas_map: dict[str, set[str]] = {}
    feasible_routes_count: dict[str, int] = {}

    for s in shelter_nodes:
        incoming_flow_map[s.node_id] = 0
        serviced_areas_map[s.node_id] = set()
        feasible_routes_count[s.node_id] = 0

    if dinic_res and dinic_res.shelter_intakes:
        for sid, detail in dinic_res.shelter_intakes.items():
            if sid in incoming_flow_map:
                incoming_flow_map[sid] = detail.assigned_flow

    for r in routes:
        if r.shelter_id in feasible_routes_count:
            feasible_routes_count[r.shelter_id] += 1
            serviced_areas_map[r.shelter_id].add(r.source_id)

    results: list[ShelterAllocationStatus] = []

    for shelter in shelter_nodes:
        meta = shelter.metadata or {}
        tot_cap = shelter.shelter_capacity
        current_occ = int(meta.get("current_occupancy", 0))
        avail_cap = max(0, tot_cap - current_occ)
        expected_in = incoming_flow_map.get(shelter.node_id, 0)
        projected_tot = current_occ + expected_in
        sat_pct = round((projected_tot / tot_cap * 100.0), 1) if tot_cap > 0 else 100.0
        is_over = projected_tot > tot_cap

        # Determine status
        if is_over:
            status = "OVERFLOW_RISK"
            advisory = f"Overflow Alert: Projected load ({projected_tot:,}) exceeds capacity by {projected_tot - tot_cap:,} evacuees. Divert secondary waves."
        elif sat_pct >= 95.0:
            status = "SATURATED"
            advisory = f"At Maximum Capacity: Shelter fully assigned ({sat_pct:.1f}%). Prepare overflow protocol."
        elif sat_pct >= 75.0:
            status = "NEAR_CAPACITY"
            advisory = f"High Occupancy: {avail_cap:,} beds remaining ({sat_pct:.1f}% committed). Monitor inflow rate."
        else:
            status = "AVAILABLE"
            advisory = f"Adequate Capacity: {avail_cap:,} beds available for incoming evacuees."

        # Hours until saturation estimate (based on hourly intake rate)
        if expected_in > 0 and avail_cap > 0:
            hours_to_sat = round(avail_cap / expected_in, 1)
        elif avail_cap == 0:
            hours_to_sat = 0.0
        else:
            hours_to_sat = None

        shelter_type = str(meta.get("shelter_type", "General Community Shelter"))
        serviced_ids = tuple(sorted(serviced_areas_map.get(shelter.node_id, set())))

        results.append(
            ShelterAllocationStatus(
                shelter_id=shelter.node_id,
                shelter_name=shelter.name,
                shelter_type=shelter_type,
                total_capacity=tot_cap,
                current_occupancy=current_occ,
                available_capacity=avail_cap,
                expected_incoming=expected_in,
                projected_total=projected_tot,
                saturation_pct=sat_pct,
                is_overcapacity=is_over,
                capacity_status=status,
                serviced_area_ids=serviced_ids,
                feasible_route_count=feasible_routes_count.get(shelter.node_id, 0),
                estimated_hours_to_saturation=hours_to_sat,
                operational_advisory=advisory,
            )
        )

    return results
