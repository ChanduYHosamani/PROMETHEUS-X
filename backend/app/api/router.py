"""Central API v1 router."""

from fastapi import APIRouter

from backend.app.api.routes import analytics, categories, health, inspections, models, reviews

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(categories.router)
api_router.include_router(models.router)
api_router.include_router(inspections.router)
api_router.include_router(reviews.router)
api_router.include_router(analytics.router)
