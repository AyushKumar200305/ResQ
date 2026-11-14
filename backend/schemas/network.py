"""Pydantic schemas for network topology, nodes, roads, and validation."""

from typing import Any
from pydantic import BaseModel, Field


class NodeCreate(BaseModel):
    """Payload to create a new graph vertex."""

    node_id: str = Field(..., description="Unique node identifier (e.g. A1, J2, S3)")
    name: str = Field(..., description="Human-readable node name")
    node_type: str = Field(..., description="NodeType: 'affected_area', 'junction', or 'shelter'")
    population: int = Field(default=0, ge=0, description="Affected evacuee population (affected areas only)")
    shelter_capacity: int = Field(default=0, ge=0, description="Shelter intake capacity (shelters only)")
    x: float | None = Field(default=None, description="Optional X coordinate for visual layout")
    y: float | None = Field(default=None, description="Optional Y coordinate for visual layout")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom metadata")


class NodeUpdate(BaseModel):
    """Payload to update an existing graph vertex."""

    name: str | None = Field(default=None, description="Updated node name")
    node_type: str | None = Field(default=None, description="Updated NodeType")
    population: int | None = Field(default=None, ge=0, description="Updated population")
    shelter_capacity: int | None = Field(default=None, ge=0, description="Updated shelter capacity")
    x: float | None = Field(default=None, description="Updated X coordinate")
    y: float | None = Field(default=None, description="Updated Y coordinate")
    metadata: dict[str, Any] | None = Field(default=None, description="Updated metadata")


class NodeResponse(BaseModel):
    """Serialized node representation."""

    node_id: str
    name: str
    node_type: str
    population: int
    shelter_capacity: int
    x: float | None = None
    y: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoadCreate(BaseModel):
    """Payload to create a new directed road edge."""

    road_id: str = Field(..., description="Unique road identifier (e.g. R1, R2)")
    source_id: str = Field(..., description="Origin node identifier")
    target_id: str = Field(..., description="Destination node identifier")
    capacity: int = Field(..., ge=0, description="Hourly corridor flow capacity (people/hour)")
    name: str = Field(default="", description="Optional road or corridor name")
    distance: float = Field(default=1.0, ge=0.0, description="Road distance in kilometers")
    travel_time_min: float = Field(default=0.0, ge=0.0, description="Estimated transit time in minutes")
    is_active: bool = Field(default=True, description="Whether the road is open or closed/disabled")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom metadata")


class RoadUpdate(BaseModel):
    """Payload to update an existing directed road edge."""

    source_id: str | None = Field(default=None, description="Updated origin node")
    target_id: str | None = Field(default=None, description="Updated destination node")
    capacity: int | None = Field(default=None, ge=0, description="Updated capacity")
    name: str | None = Field(default=None, description="Updated road name")
    distance: float | None = Field(default=None, ge=0.0, description="Updated distance in km")
    travel_time_min: float | None = Field(default=None, ge=0.0, description="Updated transit time")
    is_active: bool | None = Field(default=None, description="Updated active status")
    metadata: dict[str, Any] | None = Field(default=None, description="Updated metadata")


class RoadResponse(BaseModel):
    """Serialized road edge representation."""

    road_id: str
    source_id: str
    target_id: str
    capacity: int
    effective_capacity: int
    name: str
    distance: float
    travel_time_min: float
    is_active: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class NetworkCreate(BaseModel):
    """Payload to import or create a full evacuation network."""

    network_id: str = Field(default="custom_network", description="Unique network ID")
    name: str = Field(default="Custom Evacuation Network", description="Network title")
    description: str = Field(default="", description="Detailed network description")
    nodes: list[NodeCreate] = Field(default_factory=list, description="List of nodes")
    roads: list[RoadCreate] = Field(default_factory=list, description="List of directed roads")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class NetworkResponse(BaseModel):
    """Complete serialized evacuation network state."""

    schema_version: str = "1.0.0"
    network_id: str
    name: str
    description: str
    total_population: int
    total_shelter_capacity: int
    total_active_road_capacity: int
    nodes: list[NodeResponse]
    roads: list[RoadResponse]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationReportResponse(BaseModel):
    """Structural and evacuation validity diagnosis."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    affected_areas_count: int
    junctions_count: int
    shelters_count: int
    roads_count: int
    total_population: int
    total_shelter_capacity: int


class PresetSummary(BaseModel):
    """Summary of a built-in disaster scenario preset."""

    key: str
    title: str
    filename: str
    summary: str
