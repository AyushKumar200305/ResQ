"""Pydantic v2 schemas for Disaster Evacuation Planning and Relief Management endpoints."""

from typing import Any
from pydantic import BaseModel, Field


class AreaPrioritySchema(BaseModel):
    """Area priority assessment and explainable triage ranking."""

    area_id: str
    area_name: str
    population: int
    hazard_severity: str
    time_to_impact_hours: float
    vulnerable_population: int
    vulnerability_pct: float
    outgoing_capacity: int
    capacity_deficit: int
    spans_minimum_cut: bool
    priority_score: float
    priority_tier: str
    dispatch_order: int
    explanation: str


class RouteRecommendationSchema(BaseModel):
    """Evacuation route recommendation with safety and verification status."""

    route_id: str
    source_id: str
    source_name: str
    shelter_id: str
    shelter_name: str
    is_primary: bool
    node_path: list[str]
    road_ids: list[str]
    total_distance_km: float
    total_travel_time_min: float
    bottleneck_capacity: int
    hazard_risk_score: float
    has_unverified_roads: bool
    has_hazard_roads: bool
    unverified_road_ids: list[str]
    hazard_road_ids: list[str]
    operational_advisory: str
    recommendation_notes: str


class ShelterAllocationStatusSchema(BaseModel):
    """Shelter capacity, current occupancy, and expected incoming evacuees."""

    shelter_id: str
    shelter_name: str
    shelter_type: str
    total_capacity: int
    current_occupancy: int
    available_capacity: int
    expected_incoming: int
    projected_total: int
    saturation_pct: float
    is_overcapacity: bool
    capacity_status: str
    serviced_area_ids: list[str]
    feasible_route_count: int
    estimated_hours_to_saturation: float | None = None
    operational_advisory: str


class ShelterResourceItemSchema(BaseModel):
    """Single relief resource category detail for one shelter."""

    resource: str
    resource_label: str
    unit: str
    current_stock: int
    gross_demand: int
    net_demand: int
    allocated_stock: int
    final_stock: int
    shortage: int
    fulfillment_pct: float
    days_of_autonomy: float
    status: str


class ShelterReliefDemandSchema(BaseModel):
    """Shelter-level relief demand and allocated supplies."""

    shelter_id: str
    shelter_name: str
    total_occupants_served: int
    resources: dict[str, ShelterResourceItemSchema]
    critical_shortages_count: int
    minimum_autonomy_days: float
    shelter_priority_weight: float
    explanation: str


class ReliefAllocationResponse(BaseModel):
    """Global relief resource allocation across all camps."""

    planning_duration_days: float
    total_population_served: int
    central_depot_inventory: dict[str, int]
    total_demand: dict[str, int]
    total_allocated: dict[str, int]
    total_shortages: dict[str, int]
    shelter_allocations: list[ShelterReliefDemandSchema]
    depot_remaining_inventory: dict[str, int]
    allocation_heuristic_explanation: str
    algorithm_clarification: str


class ReliefOverviewResponse(BaseModel):
    """Comprehensive executive relief and evacuation decision briefing."""

    priorities: list[AreaPrioritySchema]
    routes: list[RouteRecommendationSchema]
    shelters: list[ShelterAllocationStatusSchema]
    resources: ReliefAllocationResponse
    summary_advisories: list[str]
    algorithm_clarification: str


class ResourceConfigRequest(BaseModel):
    """Configurable parameters for relief resource demand and allocation."""

    planning_duration_days: float = Field(default=3.0, ge=0.5, le=14.0)
    water_liters_per_person_day: float = Field(default=3.0, ge=1.0)
    food_rations_per_person_day: float = Field(default=2.0, ge=1.0)
    medical_supplies_per_person: float = Field(default=0.05, ge=0.01)
    medicines_doses_per_person_day: float = Field(default=0.10, ge=0.01)
    blankets_per_person: float = Field(default=1.0, ge=0.1)
    hygiene_kits_per_person: float = Field(default=0.20, ge=0.05)
    depot_stock_override: dict[str, int] | None = None


class VerifyRoadRequest(BaseModel):
    """Request to update a road corridor's operational verification status."""

    road_id: str
    new_status: str = Field(description="verified_clear, unverified_report, hazard_avoid, closed_damaged")
    hazard_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_notes: str | None = None


class ShelterInventoryUpdateRequest(BaseModel):
    """Payload to update physical stock available at a specific emergency shelter."""

    water_liters: int = Field(default=0, ge=0, description="Clean drinking water available on-site in liters")
    food_rations: int = Field(default=0, ge=0, description="Emergency food rations available on-site in meals")
    medical_supplies: int = Field(default=0, ge=0, description="Trauma and first-aid kits available on-site")
    medicines: int = Field(default=0, ge=0, description="Essential prescription medicine doses available on-site")
    blankets: int = Field(default=0, ge=0, description="Emergency bedding units and blankets available on-site")
    hygiene_kits: int = Field(default=0, ge=0, description="Family hygiene and sanitation packs available on-site")

