"""FastAPI router for Disaster Evacuation Planning and Relief Management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from resq.domain.enums import NodeType
from resq.domain.exceptions import EntityNotFoundError, GraphValidationError
from resq.domain.relief_models import (
    ResourceConsumptionConfig,
    RoadSafetyStatus,
)
from resq.services.area_priority import assess_area_priorities
from resq.services.camp_resources import allocate_camp_resources
from resq.services.route_recommendations import recommend_evacuation_routes
from resq.services.shelter_allocation import assess_shelter_allocations

from backend.schemas.relief import (
    AreaPrioritySchema,
    ReliefAllocationResponse,
    ReliefOverviewResponse,
    ResourceConfigRequest,
    RouteRecommendationSchema,
    ShelterAllocationStatusSchema,
    ShelterInventoryUpdateRequest,
    ShelterReliefDemandSchema,
    ShelterResourceItemSchema,
    VerifyRoadRequest,
)
from backend.state import state_manager

router = APIRouter(prefix="/api/relief", tags=["Relief Management & Decision Support"])


def _serialize_priorities(items) -> list[AreaPrioritySchema]:
    return [
        AreaPrioritySchema(
            area_id=item.area_id,
            area_name=item.area_name,
            population=item.population,
            hazard_severity=item.hazard_severity.value,
            time_to_impact_hours=item.time_to_impact_hours,
            vulnerable_population=item.vulnerable_population,
            vulnerability_pct=item.vulnerability_pct,
            outgoing_capacity=item.outgoing_capacity,
            capacity_deficit=item.capacity_deficit,
            spans_minimum_cut=item.spans_minimum_cut,
            priority_score=item.priority_score,
            priority_tier=item.priority_tier.value,
            dispatch_order=item.dispatch_order,
            explanation=item.explanation,
        )
        for item in items
    ]


def _serialize_routes(items) -> list[RouteRecommendationSchema]:
    return [
        RouteRecommendationSchema(
            route_id=item.route_id,
            source_id=item.source_id,
            source_name=item.source_name,
            shelter_id=item.shelter_id,
            shelter_name=item.shelter_name,
            is_primary=item.is_primary,
            node_path=list(item.node_path),
            road_ids=list(item.road_ids),
            total_distance_km=item.total_distance_km,
            total_travel_time_min=item.total_travel_time_min,
            bottleneck_capacity=item.bottleneck_capacity,
            hazard_risk_score=item.hazard_risk_score,
            has_unverified_roads=item.has_unverified_roads,
            has_hazard_roads=item.has_hazard_roads,
            unverified_road_ids=list(item.unverified_road_ids),
            hazard_road_ids=list(item.hazard_road_ids),
            operational_advisory=item.operational_advisory,
            recommendation_notes=item.recommendation_notes,
        )
        for item in items
    ]


def _serialize_shelters(items) -> list[ShelterAllocationStatusSchema]:
    return [
        ShelterAllocationStatusSchema(
            shelter_id=item.shelter_id,
            shelter_name=item.shelter_name,
            shelter_type=item.shelter_type,
            total_capacity=item.total_capacity,
            current_occupancy=item.current_occupancy,
            available_capacity=item.available_capacity,
            expected_incoming=item.expected_incoming,
            projected_total=item.projected_total,
            saturation_pct=item.saturation_pct,
            is_overcapacity=item.is_overcapacity,
            capacity_status=item.capacity_status,
            serviced_area_ids=list(item.serviced_area_ids),
            feasible_route_count=item.feasible_route_count,
            estimated_hours_to_saturation=item.estimated_hours_to_saturation,
            operational_advisory=item.operational_advisory,
        )
        for item in items
    ]


def _serialize_resources(res) -> ReliefAllocationResponse:
    shelter_records = []
    for s in res.shelter_allocations:
        item_details = {}
        for r_key, r_item in s.resources.items():
            item_details[r_key] = ShelterResourceItemSchema(
                resource=r_item.resource.value,
                resource_label=r_item.resource_label,
                unit=r_item.unit,
                current_stock=r_item.current_stock,
                gross_demand=r_item.gross_demand,
                net_demand=r_item.net_demand,
                allocated_stock=r_item.allocated_stock,
                final_stock=r_item.final_stock,
                shortage=r_item.shortage,
                fulfillment_pct=r_item.fulfillment_pct,
                days_of_autonomy=r_item.days_of_autonomy,
                status=r_item.status,
            )

        shelter_records.append(
            ShelterReliefDemandSchema(
                shelter_id=s.shelter_id,
                shelter_name=s.shelter_name,
                total_occupants_served=s.total_occupants_served,
                resources=item_details,
                critical_shortages_count=s.critical_shortages_count,
                minimum_autonomy_days=s.minimum_autonomy_days,
                shelter_priority_weight=s.shelter_priority_weight,
                explanation=s.explanation,
            )
        )

    return ReliefAllocationResponse(
        planning_duration_days=res.planning_duration_days,
        total_population_served=res.total_population_served,
        central_depot_inventory=res.central_depot_inventory,
        total_demand=res.total_demand,
        total_allocated=res.total_allocated,
        total_shortages=res.total_shortages,
        shelter_allocations=shelter_records,
        depot_remaining_inventory=res.depot_remaining_inventory,
        allocation_heuristic_explanation=res.allocation_heuristic_explanation,
        algorithm_clarification=res.algorithm_clarification,
    )


@router.get("/priorities", response_model=list[AreaPrioritySchema], summary="Decision 1: Area priority assessment")
def get_area_priorities() -> list[AreaPrioritySchema]:
    """Identify which affected areas should be evacuated first and why."""
    net = state_manager.get_network(make_copy=False)
    bundle = state_manager.get_bundle()
    try:
        priorities = assess_area_priorities(net, bundle=bundle)
        return _serialize_priorities(priorities)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/routes", response_model=list[RouteRecommendationSchema], summary="Decision 2: Evacuation route recommendations")
def get_route_recommendations() -> list[RouteRecommendationSchema]:
    """Identify which routes should be used, avoided or marked unverified."""
    net = state_manager.get_network(make_copy=False)
    try:
        routes = recommend_evacuation_routes(net)
        return _serialize_routes(routes)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/routes/verify", summary="Update road operational safety status")
def verify_road_status(payload: VerifyRoadRequest) -> dict[str, Any]:
    """Update or verify road condition (e.g. verified clear, unverified report, hazard avoid)."""
    net = state_manager.get_network(make_copy=True)
    road = net.roads.get(payload.road_id)
    if road is None:
        raise HTTPException(status_code=404, detail=f"Road '{payload.road_id}' not found.")

    valid_statuses = [s.value for s in RoadSafetyStatus]
    if payload.new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.new_status}'. Allowed: {', '.join(valid_statuses)}",
        )

    # Update metadata
    meta = dict(road.metadata or {})
    meta["safety_status"] = payload.new_status
    if payload.hazard_risk_score is not None:
        meta["hazard_risk_score"] = payload.hazard_risk_score
    if payload.verification_notes is not None:
        meta["verification_notes"] = payload.verification_notes

    is_active = payload.new_status != RoadSafetyStatus.CLOSED_DAMAGED.value
    net.edit_road(
        payload.road_id,
        is_active=is_active,
        metadata=meta,
    )
    state_manager.set_network(net)

    return {
        "status": "success",
        "road_id": payload.road_id,
        "safety_status": payload.new_status,
        "is_active": is_active,
        "message": f"Road {payload.road_id} updated to {payload.new_status}.",
    }


@router.get("/shelters", response_model=list[ShelterAllocationStatusSchema], summary="Decision 3: Shelter allocation status")
def get_shelter_allocations() -> list[ShelterAllocationStatusSchema]:
    """Identify which shelters should receive evacuees, occupancy, and saturation timelines."""
    net = state_manager.get_network(make_copy=False)
    bundle = state_manager.get_bundle()
    try:
        statuses = assess_shelter_allocations(net, bundle=bundle)
        return _serialize_shelters(statuses)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resources", response_model=ReliefAllocationResponse, summary="Decision 4: Camp relief resource allocation")
def compute_relief_resources(payload: ResourceConfigRequest | None = None) -> ReliefAllocationResponse:
    """Calculate and allocate food, water, medical supplies, and medicines among shelters."""
    net = state_manager.get_network(make_copy=False)
    bundle = state_manager.get_bundle()
    try:
        shelter_statuses = assess_shelter_allocations(net, bundle=bundle)

        config = ResourceConsumptionConfig()
        depot_stock = None
        duration = 3.0

        if payload is not None:
            duration = payload.planning_duration_days
            config = ResourceConsumptionConfig(
                planning_duration_days=duration,
                water_liters_per_person_day=payload.water_liters_per_person_day,
                food_rations_per_person_day=payload.food_rations_per_person_day,
                medical_supplies_per_person=payload.medical_supplies_per_person,
                medicines_doses_per_person_day=payload.medicines_doses_per_person_day,
                blankets_per_person=payload.blankets_per_person,
                hygiene_kits_per_person=payload.hygiene_kits_per_person,
            )
            depot_stock = payload.depot_stock_override

        res = allocate_camp_resources(
            net,
            shelter_statuses=shelter_statuses,
            depot_stock=depot_stock,
            config=config,
            planning_duration_days=duration,
        )
        return _serialize_resources(res)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/resources", response_model=ReliefAllocationResponse, summary="Default 3-day camp relief resource allocation")
def get_default_relief_resources(
    days: float = Query(default=3.0, ge=0.5, le=14.0, description="Planning duration in days"),
) -> ReliefAllocationResponse:
    """Retrieve relief resource allocations using default consumption assumptions."""
    req = ResourceConfigRequest(planning_duration_days=days)
    return compute_relief_resources(req)


@router.put(
    "/shelters/{shelter_id}/inventory",
    response_model=ReliefAllocationResponse,
    summary="Update local physical inventory for a specific shelter",
)
def update_shelter_inventory(
    shelter_id: str,
    payload: ShelterInventoryUpdateRequest,
    days: float = Query(default=3.0, ge=0.5, le=14.0, description="Planning duration in days"),
) -> ReliefAllocationResponse:
    """Update on-site physical supplies at a shelter, persist in graph state, and return recalculated allocations."""
    net = state_manager.get_network(make_copy=True)
    try:
        node = net.get_node(shelter_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Shelter '{shelter_id}' not found.") from exc

    if node.node_type != NodeType.SHELTER:
        raise HTTPException(status_code=400, detail=f"Node '{shelter_id}' is a {node.node_type.value}, not a shelter.")

    if node.metadata is None:
        node.metadata = {}

    supplies = {
        "water_liters": int(payload.water_liters),
        "food_rations": int(payload.food_rations),
        "medical_supplies": int(payload.medical_supplies),
        "medicines": int(payload.medicines),
        "blankets": int(payload.blankets),
        "hygiene_kits": int(payload.hygiene_kits),
    }
    node.metadata["current_supplies"] = supplies
    node.metadata["current_inventory"] = supplies

    # Persist in state manager and invalidate stale analysis caches
    state_manager.set_network(net)

    try:
        shelter_statuses = assess_shelter_allocations(net)
        config = ResourceConsumptionConfig(planning_duration_days=days)
        result = allocate_camp_resources(
            net,
            shelter_statuses=shelter_statuses,
            config=config,
            planning_duration_days=days,
        )
        return _serialize_resources(result)
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



@router.get("/overview", response_model=ReliefOverviewResponse, summary="Unified Relief & Evacuation Decision Support Briefing")
def get_relief_overview() -> ReliefOverviewResponse:
    """Consolidated situational overview addressing all four practical evacuation and relief decisions."""
    net = state_manager.get_network(make_copy=False)
    bundle = state_manager.get_bundle()
    try:
        priorities = assess_area_priorities(net, bundle=bundle)
        routes = recommend_evacuation_routes(net)
        shelters = assess_shelter_allocations(net, bundle=bundle)
        resources = allocate_camp_resources(net, shelter_statuses=shelters, planning_duration_days=3.0)

        # Generate top-level executive advisories
        advisories: list[str] = []
        if priorities:
            top_p = priorities[0]
            advisories.append(f"Immediate Triage Dispatch: {top_p.area_name} ({top_p.priority_tier.value.upper()}) requires first wave priority due to {top_p.time_to_impact_hours:.1f}h impact window.")

        unverified_cnt = sum(1 for r in routes if r.has_unverified_roads)
        if unverified_cnt > 0:
            advisories.append(f"Reconnaissance Needed: {unverified_cnt} route(s) contain unconfirmed road segments requiring scout inspection.")

        overflow_cnt = sum(1 for s in shelters if s.is_overcapacity or s.capacity_status == "OVERFLOW_RISK")
        if overflow_cnt > 0:
            advisories.append(f"Shelter Influx Warning: {overflow_cnt} shelter(s) projected to reach or exceed maximum bed capacity.")

        crit_res_cnt = sum(s.critical_shortages_count for s in resources.shelter_allocations)
        if crit_res_cnt > 0:
            advisories.append(f"Relief Supply Shortage: {crit_res_cnt} critical supply item(s) across shelters have less than 24 hours of reserve stock.")

        clarification = (
            "DAA Algorithmic Separation: Dinic's Algorithm (O(V²E)) computes global maximum integer evacuation flow. "
            "Greedy Evacuation commits flow forward without backward residual edges. "
            "Relief Resource Allocation uses a Multi-Resource Proportional Knapsack Heuristic over camp demands."
        )

        return ReliefOverviewResponse(
            priorities=_serialize_priorities(priorities),
            routes=_serialize_routes(routes),
            shelters=_serialize_shelters(shelters),
            resources=_serialize_resources(resources),
            summary_advisories=advisories,
            algorithm_clarification=clarification,
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
