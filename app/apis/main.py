"""
include routers
"""
from fastapi import APIRouter

from .routes import sesson

api_router = APIRouter()
api_router.include_router(sesson.router)
