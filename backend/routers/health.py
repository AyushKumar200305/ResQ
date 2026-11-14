"""Health check and service status router."""

from datetime import datetime, timezone
from fastapi import APIRouter

from backend.state import state_manager

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("", summary="System health and operational status")
def get_health() -> dict[str, object]:
    """Return backend health status, active network overview, and server timestamp."""
    net = state_manager.get_network(make_copy=False)
    return {
        "status": "healthy",
        "service": "ResQ Disaster Evacuation Flow & Bottleneck Optimizer",
        "version": "1.0.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "active_network": {
            "network_id": net.network_id,
            "name": net.name,
            "nodes_count": len(net.nodes),
            "roads_count": len(net.roads),
            "total_population": net.total_population,
            "total_shelter_capacity": net.total_shelter_capacity,
        },
    }
