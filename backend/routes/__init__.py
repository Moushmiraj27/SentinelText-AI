"""Aggregate routers while preserving the public /api route paths."""
from fastapi import APIRouter

from backend.routes.auth import router as auth_router
from backend.routes.wellness import router as wellness_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(wellness_router)
