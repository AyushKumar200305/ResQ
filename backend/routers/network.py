"""Network management, preset loading, and node/road CRUD endpoints."""

from fastapi import APIRouter, HTTPException, Query

from resq.domain.exceptions import (
    DuplicateIdentifierError,
    EntityNotFoundError,
    GraphValidationError,
)
from resq.domain.models import EvacuationNetwork, Node, RoadEdge
from resq.services.presets import list_presets, load_preset_network

from backend.mappers import (
    network_to_response,
    node_to_response,
    road_to_response,
    validation_to_response,
)
from backend.schemas.network import (
    NetworkCreate,
    NetworkResponse,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    PresetSummary,
    RoadCreate,
    RoadResponse,
    RoadUpdate,
    ValidationReportResponse,
)
from backend.state import state_manager

router = APIRouter(prefix="/api/network", tags=["Network"])


@router.get("", response_model=NetworkResponse, summary="Get current active evacuation network")
def get_current_network() -> NetworkResponse:
    """Retrieve full configuration and topology of the current active network."""
    net = state_manager.get_network(make_copy=True)
    return network_to_response(net)


@router.post("", response_model=NetworkResponse, summary="Create or replace active evacuation network")
def create_network(payload: NetworkCreate) -> NetworkResponse:
    """Construct a new evacuation network from user-submitted node and road data."""
    try:
        new_net = EvacuationNetwork(
            network_id=payload.network_id,
            name=payload.name,
            description=payload.description,
            metadata=payload.metadata,
        )
        for node_in in payload.nodes:
            new_net.add_node(
                node_id=node_in.node_id,
                name=node_in.name,
                node_type=node_in.node_type,
                population=node_in.population,
                shelter_capacity=node_in.shelter_capacity,
                x=node_in.x,
                y=node_in.y,
                metadata=node_in.metadata,
            )
        for road_in in payload.roads:
            new_net.add_road(
                road_id=road_in.road_id,
                source_id=road_in.source_id,
                target_id=road_in.target_id,
                capacity=road_in.capacity,
                name=road_in.name,
                distance=road_in.distance,
                travel_time_min=road_in.travel_time_min,
                is_active=road_in.is_active,
                metadata=road_in.metadata,
            )
        state_manager.set_network(new_net)
        return network_to_response(new_net)
    except (GraphValidationError, DuplicateIdentifierError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/demo", response_model=NetworkResponse, summary="Load the official demo dataset")
def load_demo_network(
    preset: str = Query(default="metro_flood_baseline", description="Demo preset key to load"),
) -> NetworkResponse:
    """Reset the active network to a standard demo dataset."""
    net = state_manager.reset_to_preset(preset)
    return network_to_response(net)


@router.get("/presets", response_model=list[PresetSummary], summary="List available scenario presets")
def get_presets() -> list[PresetSummary]:
    """Return all built-in disaster scenario presets available for loading."""
    descriptors = list_presets(include_all=True)
    return [
        PresetSummary(
            key=d.key,
            title=d.title,
            filename=d.filename,
            summary=d.summary,
        )
        for d in descriptors
    ]


@router.post("/presets/{preset_key}", response_model=NetworkResponse, summary="Load a scenario preset")
def load_preset(preset_key: str) -> NetworkResponse:
    """Load a specific preset network by its key identifier."""
    try:
        net = state_manager.reset_to_preset(preset_key)
        return network_to_response(net)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/validate", response_model=ValidationReportResponse, summary="Validate active network")
def validate_active_network() -> ValidationReportResponse:
    """Run full topological and structural validity audit on the active network."""
    net = state_manager.get_network(make_copy=False)
    report = net.validate()
    return validation_to_response(report, net)


# ----------------------------------------------------------------------
# Node CRUD
# ----------------------------------------------------------------------

@router.post("/nodes", response_model=NodeResponse, status_code=201, summary="Add a new node")
def add_node(payload: NodeCreate) -> NodeResponse:
    """Add a new affected area, junction, or shelter to the active network."""
    net = state_manager.get_network(make_copy=True)
    try:
        created = net.add_node(
            node_id=payload.node_id,
            name=payload.name,
            node_type=payload.node_type,
            population=payload.population,
            shelter_capacity=payload.shelter_capacity,
            x=payload.x,
            y=payload.y,
            metadata=payload.metadata,
        )
        state_manager.set_network(net)
        return node_to_response(created)
    except DuplicateIdentifierError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/nodes/{node_id}", response_model=NodeResponse, summary="Update an existing node")
def update_node(node_id: str, payload: NodeUpdate) -> NodeResponse:
    """Modify attributes of an existing node in the active network."""
    net = state_manager.get_network(make_copy=True)
    try:
        kwargs: dict = {}
        if payload.name is not None:
            kwargs["name"] = payload.name
        if payload.node_type is not None:
            kwargs["node_type"] = payload.node_type
        if payload.population is not None:
            kwargs["population"] = payload.population
        if payload.shelter_capacity is not None:
            kwargs["shelter_capacity"] = payload.shelter_capacity
        if payload.x is not None:
            kwargs["x"] = payload.x
        if payload.y is not None:
            kwargs["y"] = payload.y
        if payload.metadata is not None:
            kwargs["metadata"] = payload.metadata

        updated = net.edit_node(node_id, **kwargs)
        state_manager.set_network(net)
        return node_to_response(updated)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/nodes/{node_id}", summary="Delete a node")
def delete_node(
    node_id: str,
    cascade: bool = Query(default=True, description="Cascade delete incident roads"),
) -> dict[str, object]:
    """Remove a node and optionally cascade-delete all connected roads."""
    net = state_manager.get_network(make_copy=True)
    try:
        incident_roads = net.delete_node(node_id, cascade=cascade)
        state_manager.set_network(net)
        return {
            "deleted_node_id": node_id,
            "cascade": cascade,
            "incident_roads_deleted": [r.road_id for r in incident_roads],
        }
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ----------------------------------------------------------------------
# Road CRUD
# ----------------------------------------------------------------------

@router.post("/roads", response_model=RoadResponse, status_code=201, summary="Add a directed road")
def add_road(payload: RoadCreate) -> RoadResponse:
    """Register a new directed road edge connecting existing nodes in the active network."""
    net = state_manager.get_network(make_copy=True)
    try:
        created = net.add_road(
            road_id=payload.road_id,
            source_id=payload.source_id,
            target_id=payload.target_id,
            capacity=payload.capacity,
            name=payload.name,
            distance=payload.distance,
            travel_time_min=payload.travel_time_min,
            is_active=payload.is_active,
            metadata=payload.metadata,
        )
        state_manager.set_network(net)
        return road_to_response(created)
    except DuplicateIdentifierError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (GraphValidationError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/roads/{road_id}", response_model=RoadResponse, summary="Update an existing road")
def update_road(road_id: str, payload: RoadUpdate) -> RoadResponse:
    """Modify attributes of an existing directed road (capacity, distance, status)."""
    net = state_manager.get_network(make_copy=True)
    try:
        kwargs: dict = {}
        if payload.source_id is not None:
            kwargs["source_id"] = payload.source_id
        if payload.target_id is not None:
            kwargs["target_id"] = payload.target_id
        if payload.capacity is not None:
            kwargs["capacity"] = payload.capacity
        if payload.name is not None:
            kwargs["name"] = payload.name
        if payload.distance is not None:
            kwargs["distance"] = payload.distance
        if payload.travel_time_min is not None:
            kwargs["travel_time_min"] = payload.travel_time_min
        if payload.is_active is not None:
            kwargs["is_active"] = payload.is_active
        if payload.metadata is not None:
            kwargs["metadata"] = payload.metadata

        updated = net.edit_road(road_id, **kwargs)
        state_manager.set_network(net)
        return road_to_response(updated)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/roads/{road_id}", summary="Delete a directed road")
def delete_road(road_id: str) -> dict[str, str]:
    """Remove a directed road edge from the active network."""
    net = state_manager.get_network(make_copy=True)
    try:
        deleted = net.delete_road(road_id)
        state_manager.set_network(net)
        return {
            "deleted_road_id": deleted.road_id,
            "source_id": deleted.source_id,
            "target_id": deleted.target_id,
        }
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
