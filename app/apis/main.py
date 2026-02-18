"""
include routers
"""
from fastapi import APIRouter

from .routes import session, project, user, trace

api_router = APIRouter()
api_router.include_router(session.router, prefix="/api")
api_router.include_router(project.router, prefix="/api")
api_router.include_router(user.router, prefix="/api")
api_router.include_router(trace.router, prefix="/api")
