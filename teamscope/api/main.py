"""
TeamScope API — FastAPI application entry point.
All routes are prefixed with /api.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, consultants, projects, assignments, frameworks, grid, settings as settings_router, alerts, reports, imports, templates

app = FastAPI(
    title="TeamScope API",
    description="Capacity and availability planning for cybersecurity consulting teams.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under /api prefix
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
    return {"status": "ok"}
