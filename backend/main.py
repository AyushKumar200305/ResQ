"""Main FastAPI application entry point for the ResQ Disaster Evacuation Optimizer."""

import logging
import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from resq.domain.exceptions import (
    DuplicateIdentifierError,
    EntityNotFoundError,
    GraphValidationError,
    NetworkSerializationError,
)

from backend.routers import (
    comparison,
    dijkstra,
    health,
    network,
    relief,
    reports,
    scenarios,
    solve,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("resq.backend")

app = FastAPI(
    title="ResQ — Disaster Evacuation Flow & Bottleneck Optimizer API",
    description=(
        "Production-grade RESTful API serving Dinic's Maximum Flow, Minimum Cut "
        "Reachability Analysis, Greedy Baselines, Dijkstra Shortest Path, and "
        "What-If Scenario Lab Simulations for emergency disaster evacuation planning."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for local Vite/React development server and deployed environments
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Allow custom CORS origins from environment (comma-separated)
env_origins = os.getenv("CORS_ORIGINS", "")
if env_origins:
    origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https://.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# Global Exception Handlers (Never expose Python tracebacks to frontend)
# ----------------------------------------------------------------------

@app.exception_handler(GraphValidationError)
async def handle_graph_validation_error(request: Request, exc: GraphValidationError) -> JSONResponse:
    logger.warning("GraphValidationError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": "GraphValidationError"},
    )


@app.exception_handler(EntityNotFoundError)
async def handle_entity_not_found(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    logger.warning("EntityNotFoundError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc), "error_type": "EntityNotFoundError"},
    )


@app.exception_handler(DuplicateIdentifierError)
async def handle_duplicate_id(request: Request, exc: DuplicateIdentifierError) -> JSONResponse:
    logger.warning("DuplicateIdentifierError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "error_type": "DuplicateIdentifierError"},
    )


@app.exception_handler(NetworkSerializationError)
async def handle_serialization_error(request: Request, exc: NetworkSerializationError) -> JSONResponse:
    logger.warning("NetworkSerializationError on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": "NetworkSerializationError"},
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred during evacuation optimization. Please verify network topology and parameters.",
            "error_type": "InternalServerError",
        },
    )


# ----------------------------------------------------------------------
# Register Routers
# ----------------------------------------------------------------------

app.include_router(health.router)
app.include_router(network.router)
app.include_router(solve.router)
app.include_router(scenarios.router)
app.include_router(comparison.router)
app.include_router(dijkstra.router)
app.include_router(relief.router)
app.include_router(reports.router)


@app.get("/", summary="Root endpoint with API overview")
def root() -> dict[str, str]:
    """Root entry point providing interactive documentation links."""
    return {
        "service": "ResQ Evacuation Optimizer API",
        "documentation": "/docs",
        "health_check": "/api/health",
        "status": "operational",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
