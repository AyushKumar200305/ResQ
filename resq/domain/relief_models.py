"""Domain models and schemas for Disaster Evacuation Planning and Relief Management.

Covers the four practical operational decisions:
1. Area Priority Assessment (Hazard urgency, vulnerability, road accessibility, explainable tier).
2. Evacuation Route Recommendations (Primary, alternative, unverified, hazard avoidance).
3. Shelter Allocation (Occupancy, expected incoming evacuees, feasible corridors).
4. Camp Resource Allocation (Water, food, medical supplies, medicines, blankets, hygiene kits).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class HazardSeverity(str, Enum):
    """Hazard severity classification for impacted zones."""

    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"

    @classmethod
    def parse(cls, value: object) -> "HazardSeverity":
        if isinstance(value, cls):
            return value
        val_str = str(value).lower().strip()
        for member in cls:
            if member.value == val_str:
                return member
        return cls.MODERATE


class PriorityTier(str, Enum):
    """Operational evacuation dispatch triage tier."""

    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"


class RoadSafetyStatus(str, Enum):
    """Operational road verification and condition status."""

    VERIFIED_CLEAR = "verified_clear"
    UNVERIFIED_REPORT = "unverified_report"
    HAZARD_AVOID = "hazard_avoid"
    CLOSED_DAMAGED = "closed_damaged"

    @classmethod
    def parse(cls, value: object) -> "RoadSafetyStatus":
        if isinstance(value, cls):
            return value
        val_str = str(value).lower().strip()
        for member in cls:
            if member.value == val_str:
                return member
        return cls.VERIFIED_CLEAR


class SupplyResource(str, Enum):
    """Relief resource item categories for camp supply management."""

    WATER = "water_liters"
    FOOD = "food_rations"
    MEDICAL_SUPPLIES = "medical_supplies"
    MEDICINES = "medicines"
    BLANKETS = "blankets"
    HYGIENE_KITS = "hygiene_kits"


@dataclass(frozen=True, slots=True)
class AreaPriorityAssessment:
    """Evaluated triage priority for a disaster-affected area."""

    area_id: str
    area_name: str
    population: int
    hazard_severity: HazardSeverity
    time_to_impact_hours: float
    vulnerable_population: int
    vulnerability_pct: float
    outgoing_capacity: int
    capacity_deficit: int
    spans_minimum_cut: bool
    priority_score: float
    priority_tier: PriorityTier
    dispatch_order: int
    explanation: str


@dataclass(frozen=True, slots=True)
class RouteRecommendation:
    """Turn-by-turn route recommendation from an affected area to a shelter."""

    route_id: str
    source_id: str
    source_name: str
    shelter_id: str
    shelter_name: str
    is_primary: bool
    node_path: tuple[str, ...]
    road_ids: tuple[str, ...]
    total_distance_km: float
    total_travel_time_min: float
    bottleneck_capacity: int
    hazard_risk_score: float
    has_unverified_roads: bool
    has_hazard_roads: bool
    unverified_road_ids: tuple[str, ...]
    hazard_road_ids: tuple[str, ...]
    operational_advisory: str  # "RECOMMENDED", "CAUTION", "UNVERIFIED_RECON_NEEDED", "AVOID"
    recommendation_notes: str


@dataclass(frozen=True, slots=True)
class ShelterAllocationStatus:
    """Real-time intake capacity, current occupancy, and incoming evacuees."""

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
    capacity_status: str  # "AVAILABLE", "NEAR_CAPACITY", "SATURATED", "OVERFLOW_RISK"
    serviced_area_ids: tuple[str, ...]
    feasible_route_count: int
    estimated_hours_to_saturation: float | None
    operational_advisory: str


@dataclass(frozen=True, slots=True)
class ResourceConsumptionConfig:
    """Configurable daily per-person consumption rates and planning duration."""

    planning_duration_days: float = 3.0
    water_liters_per_person_day: float = 3.0
    food_rations_per_person_day: float = 2.0
    medical_supplies_per_person: float = 0.05
    medicines_doses_per_person_day: float = 0.10
    blankets_per_person: float = 1.0
    hygiene_kits_per_person: float = 0.20


@dataclass(frozen=True, slots=True)
class ShelterResourceItemDetail:
    """Allocation status for a single supply category at one shelter."""

    resource: SupplyResource
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
    status: str  # "SUFFICIENT", "DEFICIT_WARNING", "CRITICAL_SHORTAGE"


@dataclass(frozen=True, slots=True)
class ShelterReliefDemand:
    """Comprehensive relief resource requirement and allocation for a shelter."""

    shelter_id: str
    shelter_name: str
    total_occupants_served: int
    resources: dict[str, ShelterResourceItemDetail]
    critical_shortages_count: int
    minimum_autonomy_days: float
    shelter_priority_weight: float
    explanation: str


@dataclass(frozen=True, slots=True)
class ReliefAllocationResult:
    """Global multi-resource relief distribution summary across all camps."""

    planning_duration_days: float
    total_population_served: int
    central_depot_inventory: dict[str, int]
    total_demand: dict[str, int]
    total_allocated: dict[str, int]
    total_shortages: dict[str, int]
    shelter_allocations: list[ShelterReliefDemand]
    depot_remaining_inventory: dict[str, int]
    allocation_heuristic_explanation: str
    algorithm_clarification: str  # Explains separation of relief greedy from evacuation greedy
