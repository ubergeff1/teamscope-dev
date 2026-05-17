"""
TeamScope API -- FastAPI application entry point.

This module creates and configures the FastAPI application instance. It is the
file that ASGI servers (uvicorn, gunicorn) import to serve the API.

Application structure:
  - All API routes are mounted under the ``/api`` prefix so that a reverse proxy
    can serve the frontend on ``/`` and the API on ``/api`` from the same domain.
  - CORS middleware is configured to allow the frontend origin(s) specified in
    the ``CORS_ORIGINS`` environment variable (see config.py).
  - Interactive API documentation is available at ``/api/docs`` (Swagger UI)
    and ``/api/redoc`` (ReDoc).

Registered routers (all prefixed with /api):
  - auth:         Login and token endpoints.
  - consultants:  CRUD for consultant profiles and capacity settings.
  - projects:     CRUD for projects and their deliverables/phases.
  - assignments:  Manual assignment management (as opposed to auto-synced ones).
  - frameworks:   Compliance framework and control family definitions.
  - grid:         The capacity/availability grid -- the core planning view.
  - settings:     Application-level settings (e.g., snap_end_to_friday).
  - alerts:       Over-allocation and deadline alerts.
  - reports:      Utilization and workload reports.
  - imports:      Bulk data import (e.g., from spreadsheets).
  - templates:    Project and deliverable templates.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, consultants, projects, assignments, frameworks, grid, settings as settings_router, alerts, reports, imports, templates

# Create the main FastAPI application instance.
# - title/description/version: Shown in the auto-generated OpenAPI docs.
# - docs_url/redoc_url/openapi_url: Moved under /api to match the route prefix.
app = FastAPI(
    title="TeamScope API",
    description="Capacity and availability planning for cybersecurity consulting teams.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS (Cross-Origin Resource Sharing) middleware.
# This is required because the frontend (typically on localhost:5000 during dev)
# runs on a different origin than the API.
# - allow_origins: List of allowed frontend origins (from CORS_ORIGINS env var).
# - allow_credentials: Permits cookies/auth headers in cross-origin requests.
# - allow_methods/allow_headers: Wildcard allows all HTTP methods and headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under the /api prefix.
# Each router defines its own sub-prefix (e.g., /auth, /consultants), so the
# full path becomes /api/auth, /api/consultants, etc.
for router in [
    auth.router,
    consultants.router,
    projects.router,
    assignments.router,
    frameworks.router,
    grid.router,
    settings_router.router,
    alerts.router,
    reports.router,
    imports.router,
    templates.router,
]:
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health():
    """Health check endpoint for load balancers and monitoring.

    Returns a simple JSON response ``{"status": "ok"}`` to confirm the API
    process is running and able to handle requests. This endpoint does not
    check database connectivity -- it only confirms the ASGI server is alive.

    Returns:
        dict: ``{"status": "ok"}``
    """
    return {"status": "ok"}
