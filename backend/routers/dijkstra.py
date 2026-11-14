"""Dijkstra shortest-path calculations and DAA comparison router."""

from fastapi import APIRouter, HTTPException

from resq.algorithms.dijkstra import solve_shortest_path_dijkstra
from resq.domain.exceptions import EntityNotFoundError, GraphValidationError
from resq.services.shortest_path_service import compare_shortest_path_with_max_flow

from backend.schemas.dijkstra import (
    DijkstraRequest,
    DijkstraResponse,
    ShortestRouteDetailSchema,
    ShortestVsMaxFlowComparisonSchema,
)
from backend.state import state_manager

router = APIRouter(prefix="/api/dijkstra", tags=["Shortest Path (Dijkstra)"])


@router.post("/solve", response_model=DijkstraResponse, summary="Find shortest distance route and compare with Dinic")
def solve_dijkstra(payload: DijkstraRequest) -> DijkstraResponse:
    """Calculate the shortest-distance route and alternative route using Dijkstra's algorithm (O((V+E) log V))."""
    net = state_manager.get_network(make_copy=True)
    try:
        comparison_obj = compare_shortest_path_with_max_flow(
            net,
            source_id=payload.source_id,
            shelter_id=payload.shelter_id,
            compute_flow_if_missing=True,
        )
        d_res = comparison_obj.dijkstra_result

        shortest_schema: ShortestRouteDetailSchema | None = None
        if d_res.shortest_route:
            shortest_schema = ShortestRouteDetailSchema(
                node_path=list(d_res.shortest_route.node_path),
                road_ids=list(d_res.shortest_route.road_ids),
                total_distance=round(d_res.shortest_route.total_distance, 2),
                total_travel_time_min=round(d_res.shortest_route.total_travel_time_min, 1),
                bottleneck_capacity=d_res.shortest_route.bottleneck_capacity,
            )

        alt_schema: ShortestRouteDetailSchema | None = None
        if d_res.alternative_route:
            alt_schema = ShortestRouteDetailSchema(
                node_path=list(d_res.alternative_route.node_path),
                road_ids=list(d_res.alternative_route.road_ids),
                total_distance=round(d_res.alternative_route.total_distance, 2),
                total_travel_time_min=round(d_res.alternative_route.total_travel_time_min, 1),
                bottleneck_capacity=d_res.alternative_route.bottleneck_capacity,
            )

        comp_schema = ShortestVsMaxFlowComparisonSchema(
            system_max_flow=comparison_obj.system_max_flow,
            source_population=comparison_obj.source_population,
            source_dispatched_flow=comparison_obj.source_dispatched_flow,
            shelter_capacity=comparison_obj.shelter_capacity,
            shelter_received_flow=comparison_obj.shelter_received_flow,
            bottleneck_on_shortest_path=d_res.shortest_route.bottleneck_capacity if d_res.shortest_route else 0,
            educational_takeaway=(
                "Dijkstra minimizes individual route distance (km) without regard to road capacities or other evacuees. "
                "Dinic's algorithm maximizes total network throughput (people/hour) by distributing flow across all available corridors."
            ),
        )

        return DijkstraResponse(
            source_id=payload.source_id,
            shelter_id=payload.shelter_id,
            is_reachable=d_res.reachable,
            execution_time_ms=d_res.execution_time_ms,
            relaxed_edges_count=d_res.relaxed_edges_count,
            heap_pops=d_res.heap_pops,
            shortest_route=shortest_schema,
            alternative_route=alt_schema,
            comparison=comp_schema,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
