"""Evacuation route recommendations service using Dijkstra and road safety vetting.

Calculates primary and alternative evacuation routes from affected areas to shelters,
inspects road capacity, distance, travel time, closed/damaged status, hazard exposure,
and flags routes with unverified road conditions requiring scout reconnaissance.
"""

from typing import Sequence
from resq.algorithms.dijkstra import DijkstraSolver
from resq.domain.enums import NodeType
from resq.domain.models import EvacuationNetwork, RoadEdge
from resq.domain.relief_models import (
    RoadSafetyStatus,
    RouteRecommendation,
)


def recommend_evacuation_routes(
    network: EvacuationNetwork,
    *,
    solver: DijkstraSolver | None = None,
    max_routes_per_pair: int = 2,
) -> list[RouteRecommendation]:
    """Generate operational route recommendations for all source-to-shelter pairs using Dijkstra."""
    if solver is None:
        solver = DijkstraSolver()

    recommendations: list[RouteRecommendation] = []
    affected_areas = network.affected_areas
    shelters = network.shelters

    if not affected_areas or not shelters:
        return []

    # Map of roads for fast lookup
    road_map = network.roads

    for area in affected_areas:
        for shelter in shelters:
            # Run Dijkstra to find primary and alternative paths
            dijkstra_res = solver.solve(network, source_id=area.node_id, shelter_id=shelter.node_id)
            if not dijkstra_res.reachable:
                continue

            routes_to_evaluate = []
            if dijkstra_res.shortest_route:
                routes_to_evaluate.append((dijkstra_res.shortest_route, True))
            if max_routes_per_pair > 1 and dijkstra_res.alternative_route:
                routes_to_evaluate.append((dijkstra_res.alternative_route, False))

            for path_route, is_primary in routes_to_evaluate:
                road_ids = path_route.road_ids
                node_path = path_route.node_path

                # Analyze safety status and hazards along constituent roads
                unverified_roads: list[str] = []
                hazard_roads: list[str] = []
                hazard_scores: list[float] = []

                for rid in road_ids:
                    road = road_map.get(rid)
                    if road is None:
                        continue
                    meta = road.metadata or {}
                    raw_status = meta.get("safety_status")
                    if raw_status:
                        status = RoadSafetyStatus.parse(raw_status)
                    else:
                        status = RoadSafetyStatus.VERIFIED_CLEAR if road.is_active else RoadSafetyStatus.CLOSED_DAMAGED

                    risk = float(meta.get("hazard_risk_score", meta.get("hazard_risk", 0.05)))
                    hazard_scores.append(risk)

                    if status == RoadSafetyStatus.UNVERIFIED_REPORT:
                        unverified_roads.append(rid)
                    elif status in (RoadSafetyStatus.HAZARD_AVOID, RoadSafetyStatus.CLOSED_DAMAGED) or risk >= 0.6:
                        hazard_roads.append(rid)

                avg_hazard_risk = round(sum(hazard_scores) / len(hazard_scores), 2) if hazard_scores else 0.05
                has_unverified = len(unverified_roads) > 0
                has_hazard = len(hazard_roads) > 0

                # Formulate operational advisory
                if path_route.bottleneck_capacity <= 0:
                    advisory = "CLOSED_IMPASSABLE"
                    notes = f"Route impassable: Corridor includes disabled or zero-capacity roads ({', '.join(hazard_roads) or 'inactive road'})."
                elif has_hazard:
                    advisory = "AVOID_HAZARD"
                    notes = f"Hazard Avoidance: High flood/debris risk along {', '.join(hazard_roads)}. Divert to alternate corridor."
                elif has_unverified:
                    advisory = "UNVERIFIED_SCOUT_REQUIRED"
                    notes = f"Reconnaissance Required: Road condition unconfirmed on {', '.join(unverified_roads)}. Dispatch scout/drone before civilian convoys."
                elif path_route.bottleneck_capacity < 500:
                    advisory = "CAUTION_CHOKEPOINT"
                    notes = f"Capacity Chokepoint: Minimum segment width ({path_route.bottleneck_capacity:,} p/h) may cause evacuation queues."
                else:
                    advisory = "RECOMMENDED"
                    notes = "Verified Clear: All corridors active, inspected, and free of flood risk."

                route_type_prefix = "P" if is_primary else "ALT"
                route_id = f"ROUTE_{route_type_prefix}_{area.node_id}_{shelter.node_id}"

                recommendations.append(
                    RouteRecommendation(
                        route_id=route_id,
                        source_id=area.node_id,
                        source_name=area.name,
                        shelter_id=shelter.node_id,
                        shelter_name=shelter.name,
                        is_primary=is_primary,
                        node_path=node_path,
                        road_ids=road_ids,
                        total_distance_km=round(path_route.total_distance, 2),
                        total_travel_time_min=round(path_route.total_travel_time_min, 1),
                        bottleneck_capacity=path_route.bottleneck_capacity,
                        hazard_risk_score=avg_hazard_risk,
                        has_unverified_roads=has_unverified,
                        has_hazard_roads=has_hazard,
                        unverified_road_ids=tuple(unverified_roads),
                        hazard_road_ids=tuple(hazard_roads),
                        operational_advisory=advisory,
                        recommendation_notes=notes,
                    )
                )

    return recommendations
