"""Pydantic schemas for Dijkstra shortest-path calculations and max-flow comparison."""

from typing import Any
from pydantic import BaseModel, Field


class DijkstraRequest(BaseModel):
    """Parameters to query shortest path between source and shelter."""

    source_id: str = Field(..., description="Affected area origin identifier")
    shelter_id: str = Field(..., description="Shelter destination identifier")


class ShortestRouteDetailSchema(BaseModel):
    """Calculated path route metrics."""

    node_path: list[str]
    road_ids: list[str]
    total_distance: float
    total_travel_time_min: float
    bottleneck_capacity: int


class ShortestVsMaxFlowComparisonSchema(BaseModel):
    """DAA educational comparison between individual shortest path and max flow."""

    system_max_flow: int
    source_population: int
    source_dispatched_flow: int
    shelter_capacity: int
    shelter_received_flow: int
    bottleneck_on_shortest_path: int
    educational_takeaway: str


class DijkstraResponse(BaseModel):
    """Dijkstra shortest path and alternative route results."""

    source_id: str
    shelter_id: str
    is_reachable: bool
    execution_time_ms: float
    relaxed_edges_count: int
    heap_pops: int
    shortest_route: ShortestRouteDetailSchema | None = None
    alternative_route: ShortestRouteDetailSchema | None = None
    comparison: ShortestVsMaxFlowComparisonSchema | None = None
