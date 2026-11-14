"""Pydantic schemas for What-If Scenario Lab simulations."""

from typing import Any
from pydantic import BaseModel, Field

from backend.schemas.analysis import FullAnalysisResponse
from backend.schemas.network import NetworkResponse


class RoadClosureRequest(BaseModel):
    """Request to evaluate a road-closure scenario."""

    road_id: str = Field(..., description="ID of road to close")
    scenario_name: str | None = Field(default=None, description="Optional custom scenario name")


class ReducedShelterRequest(BaseModel):
    """Request to evaluate reduced shelter intake."""

    shelter_id: str = Field(..., description="ID of shelter to reduce")
    new_capacity: int = Field(..., ge=0, description="New reduced shelter bed capacity")
    scenario_name: str | None = Field(default=None, description="Optional custom scenario name")


class IncreasedShelterRequest(BaseModel):
    """Request to evaluate shelter expansion."""

    shelter_id: str = Field(..., description="ID of shelter to expand")
    added_capacity: int = Field(..., ge=1, description="Additional capacity to add")
    scenario_name: str | None = Field(default=None, description="Optional custom scenario name")


class MultiRoadFailureRequest(BaseModel):
    """Request to evaluate simultaneous road failures."""

    road_ids: list[str] = Field(..., min_length=1, description="List of road IDs to close")
    scenario_name: str | None = Field(default=None, description="Optional custom scenario name")


class CustomDisruptionRequest(BaseModel):
    """Custom disruption overlay."""

    scenario_name: str = Field(default="Custom Disaster Disruption")
    disabled_roads: list[str] = Field(default_factory=list)
    road_capacity_factors: dict[str, float] = Field(default_factory=dict)
    disabled_shelters: list[str] = Field(default_factory=list)
    demand_multipliers: dict[str, float] = Field(default_factory=dict)


class ScenarioEvaluationResponse(BaseModel):
    """Scenario simulation results and operational observations."""

    scenario_key: str
    scenario_name: str
    scenario_kind: str
    description: str
    max_flow: int
    unmet_demand: int
    evacuation_rate: float
    baseline_delta: int
    baseline_delta_pct: float
    cut_capacity: int
    bottleneck_roads_count: int
    observations: list[str]
    network: NetworkResponse
    bundle: FullAnalysisResponse | None = None


class ScenarioComparisonSummaryResponse(BaseModel):
    """Comparison matrix across multiple evaluated scenarios."""

    baseline_flow: int
    scenarios: list[ScenarioEvaluationResponse]
