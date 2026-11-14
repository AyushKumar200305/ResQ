"""Camp resource allocation service for disaster relief management.

Calculates multi-resource demand (water, food, medical supplies, medicines, blankets, hygiene kits)
using configurable consumption assumptions and planning horizons.
Allocates limited central depot inventory using an explainable, deterministic fair-share heuristic.
"""

from dataclasses import asdict
import math
from typing import Any, Mapping

from resq.domain.models import EvacuationNetwork
from resq.domain.relief_models import (
    ReliefAllocationResult,
    ResourceConsumptionConfig,
    ShelterAllocationStatus,
    ShelterReliefDemand,
    ShelterResourceItemDetail,
    SupplyResource,
)
from resq.services.shelter_allocation import assess_shelter_allocations


# Standard humanitarian labels and units (Sphere Project Standards)
RESOURCE_METADATA: dict[SupplyResource, dict[str, str]] = {
    SupplyResource.WATER: {"label": "Clean Drinking Water", "unit": "liters"},
    SupplyResource.FOOD: {"label": "Emergency Food Rations", "unit": "rations"},
    SupplyResource.MEDICAL_SUPPLIES: {"label": "Trauma & First Aid Kits", "unit": "kits"},
    SupplyResource.MEDICINES: {"label": "Essential Prescription Doses", "unit": "doses"},
    SupplyResource.BLANKETS: {"label": "Emergency Bedding & Blankets", "unit": "units"},
    SupplyResource.HYGIENE_KITS: {"label": "Family Hygiene & Sanitation Packs", "unit": "kits"},
}


def allocate_camp_resources(
    network: EvacuationNetwork,
    *,
    shelter_statuses: list[ShelterAllocationStatus] | None = None,
    depot_stock: dict[str, int] | None = None,
    config: ResourceConsumptionConfig | None = None,
    planning_duration_days: float | None = None,
) -> ReliefAllocationResult:
    """Execute fair-share relief resource distribution across emergency shelters.

    Important DAA Algorithmic Clarification:
      This relief resource allocation algorithm is a bounded multi-resource knapsack / proportional
      fair allocation heuristic across discrete camp demands. It is mathematically independent from
      the Dinic maximum-flow algorithm (which computes network corridor capacities) and the Greedy
      evacuation heuristic (which commits flow along forward-only augmenting paths without reverse edges).
    """
    if config is None:
        config = ResourceConsumptionConfig()

    duration = float(planning_duration_days if planning_duration_days is not None else config.planning_duration_days)
    duration = max(0.5, duration)

    if shelter_statuses is None:
        shelter_statuses = assess_shelter_allocations(network)

    if not shelter_statuses:
        return ReliefAllocationResult(
            planning_duration_days=duration,
            total_population_served=0,
            central_depot_inventory={},
            total_demand={},
            total_allocated={},
            total_shortages={},
            shelter_allocations=[],
            depot_remaining_inventory={},
            allocation_heuristic_explanation="No active shelters available for relief distribution.",
            algorithm_clarification="Relief resource allocation is a supply distribution heuristic, distinct from evacuation max-flow.",
        )

    # 1. Resolve Available Central Depot Inventory
    # If not passed explicitly, attempt to read from network.metadata['relief_depot'] or set realistic defaults
    net_meta = network.metadata or {}
    depot_meta = net_meta.get("relief_depot", {})
    default_depot = {
        SupplyResource.WATER.value: 28000,
        SupplyResource.FOOD.value: 18000,
        SupplyResource.MEDICAL_SUPPLIES.value: 500,
        SupplyResource.MEDICINES.value: 1200,
        SupplyResource.BLANKETS.value: 4000,
        SupplyResource.HYGIENE_KITS.value: 1000,
    }
    available_depot: dict[str, int] = {}
    for res_enum in SupplyResource:
        key = res_enum.value
        if depot_stock and key in depot_stock:
            available_depot[key] = max(0, int(depot_stock[key]))
        elif depot_meta and key in depot_meta:
            available_depot[key] = max(0, int(depot_meta[key]))
        else:
            available_depot[key] = default_depot[key]

    total_pop_served = sum(s.projected_total for s in shelter_statuses)

    # 2. Compute Gross and Net Demand per Shelter for each Resource
    # Structure: shelter_id -> resource_key -> {gross_demand, current_stock, net_demand, daily_rate}
    demand_matrix: dict[str, dict[SupplyResource, dict[str, Any]]] = {}
    total_net_demand_by_res: dict[SupplyResource, int] = {r: 0 for r in SupplyResource}
    total_gross_demand_by_res: dict[SupplyResource, int] = {r: 0 for r in SupplyResource}

    for s in shelter_statuses:
        shl_node = network.nodes.get(s.shelter_id)
        shl_meta = shl_node.metadata if shl_node else {}
        current_inventory = shl_meta.get("current_supplies", shl_meta.get("current_inventory", {}))

        pop = max(1, s.projected_total)
        demand_matrix[s.shelter_id] = {}

        for res_enum in SupplyResource:
            unit_info = RESOURCE_METADATA[res_enum]
            cur_stock = max(0, int(current_inventory.get(res_enum.value, 0)))

            # Consumption rate logic (some are per day, some are static per-person)
            if res_enum == SupplyResource.WATER:
                daily_rate = config.water_liters_per_person_day
                gross = math.ceil(pop * daily_rate * duration)
            elif res_enum == SupplyResource.FOOD:
                daily_rate = config.food_rations_per_person_day
                gross = math.ceil(pop * daily_rate * duration)
            elif res_enum == SupplyResource.MEDICAL_SUPPLIES:
                daily_rate = config.medical_supplies_per_person / duration
                gross = math.ceil(pop * config.medical_supplies_per_person)
            elif res_enum == SupplyResource.MEDICINES:
                daily_rate = config.medicines_doses_per_person_day
                gross = math.ceil(pop * daily_rate * duration)
            elif res_enum == SupplyResource.BLANKETS:
                daily_rate = config.blankets_per_person / duration
                gross = math.ceil(pop * config.blankets_per_person)
            elif res_enum == SupplyResource.HYGIENE_KITS:
                daily_rate = config.hygiene_kits_per_person / duration
                gross = math.ceil(pop * config.hygiene_kits_per_person)
            else:
                daily_rate = 1.0
                gross = pop

            net = max(0, gross - cur_stock)
            demand_matrix[s.shelter_id][res_enum] = {
                "gross_demand": gross,
                "current_stock": cur_stock,
                "net_demand": net,
                "daily_rate": daily_rate,
                "pop": pop,
            }
            total_net_demand_by_res[res_enum] += net
            total_gross_demand_by_res[res_enum] += gross

    # 3. Proportional Fair Allocation of Depot Stock
    # allocated_matrix: shelter_id -> resource_enum -> allocated_amount
    allocated_matrix: dict[str, dict[SupplyResource, int]] = {s.shelter_id: {} for s in shelter_statuses}
    remaining_depot: dict[str, int] = {}
    total_allocated_by_res: dict[str, int] = {}
    total_shortages_by_res: dict[str, int] = {}

    for res_enum in SupplyResource:
        key = res_enum.value
        avail_stock = available_depot[key]
        total_net = total_net_demand_by_res[res_enum]

        if total_net == 0:
            for s in shelter_statuses:
                allocated_matrix[s.shelter_id][res_enum] = 0
            remaining_depot[key] = avail_stock
            total_allocated_by_res[key] = 0
            total_shortages_by_res[key] = 0
        elif avail_stock >= total_net:
            # 100% Demand Satisfaction
            for s in shelter_statuses:
                allocated_matrix[s.shelter_id][res_enum] = demand_matrix[s.shelter_id][res_enum]["net_demand"]
            remaining_depot[key] = avail_stock - total_net
            total_allocated_by_res[key] = total_net
            total_shortages_by_res[key] = 0
        else:
            # Scarcity Deficit: Proportional Fair Allocation
            allocated_sum = 0
            fractions: list[tuple[float, str]] = []

            for s in shelter_statuses:
                net_req = demand_matrix[s.shelter_id][res_enum]["net_demand"]
                share_float = (net_req / total_net) * avail_stock
                share_int = int(share_float)
                allocated_matrix[s.shelter_id][res_enum] = share_int
                allocated_sum += share_int
                fractions.append((share_float - share_int, s.shelter_id))

            # Distribute remainder by largest fractional remainder
            remainder = avail_stock - allocated_sum
            fractions.sort(key=lambda x: -x[0])
            for _, sid in fractions[:remainder]:
                if allocated_matrix[sid][res_enum] < demand_matrix[sid][res_enum]["net_demand"]:
                    allocated_matrix[sid][res_enum] += 1
                    allocated_sum += 1

            remaining_depot[key] = max(0, avail_stock - allocated_sum)
            total_allocated_by_res[key] = allocated_sum
            total_shortages_by_res[key] = max(0, total_net - allocated_sum)

    # 4. Assemble Detailed Shelter Output Records
    shelter_records: list[ShelterReliefDemand] = []

    for s in shelter_statuses:
        res_details: dict[str, ShelterResourceItemDetail] = {}
        critical_count = 0
        autonomy_list: list[float] = []

        for res_enum in SupplyResource:
            d_info = demand_matrix[s.shelter_id][res_enum]
            alloc = allocated_matrix[s.shelter_id][res_enum]
            cur = d_info["current_stock"]
            gross = d_info["gross_demand"]
            net = d_info["net_demand"]
            final = cur + alloc
            shortage = max(0, net - alloc)
            fulfill_pct = round((final / gross * 100.0), 1) if gross > 0 else 100.0

            # Calculate days of autonomy
            daily_burn = d_info["pop"] * d_info["daily_rate"]
            if daily_burn > 0:
                autonomy = round(final / daily_burn, 1)
            else:
                autonomy = duration

            autonomy_list.append(autonomy)

            if autonomy < 1.0 or fulfill_pct < 50.0:
                item_status = "CRITICAL_SHORTAGE"
                critical_count += 1
            elif autonomy < duration or fulfill_pct < 100.0:
                item_status = "DEFICIT_WARNING"
            else:
                item_status = "SUFFICIENT"

            unit_meta = RESOURCE_METADATA[res_enum]
            res_details[res_enum.value] = ShelterResourceItemDetail(
                resource=res_enum,
                resource_label=unit_meta["label"],
                unit=unit_meta["unit"],
                current_stock=cur,
                gross_demand=gross,
                net_demand=net,
                allocated_stock=alloc,
                final_stock=final,
                shortage=shortage,
                fulfillment_pct=fulfill_pct,
                days_of_autonomy=autonomy,
                status=item_status,
            )

        min_autonomy = min(autonomy_list) if autonomy_list else duration
        shl_weight = round(s.projected_total / max(1, total_pop_served), 3)

        if critical_count > 0:
            shl_explanation = f"Critical relief supply deficit ({critical_count} items below 24h reserve). Minimum autonomy is {min_autonomy:.1f} days."
        elif min_autonomy < duration:
            shl_explanation = f"Partial relief fulfillment: Stock lasts {min_autonomy:.1f} of {duration:.1f} planned days. Resupply convoy required."
        else:
            shl_explanation = f"Fully provisioned for {duration:.1f} days across all 6 core relief categories."

        shelter_records.append(
            ShelterReliefDemand(
                shelter_id=s.shelter_id,
                shelter_name=s.shelter_name,
                total_occupants_served=s.projected_total,
                resources=res_details,
                critical_shortages_count=critical_count,
                minimum_autonomy_days=min_autonomy,
                shelter_priority_weight=shl_weight,
                explanation=shl_explanation,
            )
        )

    # Explanation of the heuristic
    heuristic_narrative = (
        f"Fair-Share Proportional Heuristic: Calculated {duration:.1f}-day gross requirement using Sphere Humanitarian Standards "
        f"for {total_pop_served:,} evacuees. Where central depot inventory fell below aggregate regional demand, stock was rationed "
        f"proportionally to each shelter's net deficit to ensure equitable autonomy and prevent isolated camp starvation."
    )

    clarification_note = (
        "Algorithm Distinction: Relief Resource Allocation executes a Multi-Resource Proportional Knapsack Heuristic over "
        "humanitarian demand vectors. It is mathematically independent from the Dinic Maximum Flow algorithm (which solves "
        "directed corridor capacities via BFS/DFS) and the Evacuation Greedy baseline (which routes paths without reverse edges)."
    )

    return ReliefAllocationResult(
        planning_duration_days=duration,
        total_population_served=total_pop_served,
        central_depot_inventory=available_depot,
        total_demand={r.value: total_gross_demand_by_res[r] for r in SupplyResource},
        total_allocated=total_allocated_by_res,
        total_shortages=total_shortages_by_res,
        shelter_allocations=shelter_records,
        depot_remaining_inventory=remaining_depot,
        allocation_heuristic_explanation=heuristic_narrative,
        algorithm_clarification=clarification_note,
    )
