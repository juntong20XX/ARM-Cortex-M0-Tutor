"""
include routers
"""
from fastapi import APIRouter

from .routes import session

api_router = APIRouter()
api_router.include_router(session.router, prefix="/api")
