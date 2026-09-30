"""Aggregates every v1 router this service owns behind `/api/v1`."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import fleet

api_router = APIRouter()
api_router.include_router(fleet.router)
