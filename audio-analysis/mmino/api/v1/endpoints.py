"""
API v1 endpoints
"""
from fastapi import APIRouter

# Import individual routers
from .upload import router as upload_router
from .jobs import router as jobs_router
from .download import router as download_router
from .admin import router as admin_router
from .users import router as users_router
from .auth import router as auth_router
from .system import router as system_router

# Combine all routers
router = APIRouter()

router.include_router(upload_router, prefix="/upload", tags=["upload"])
router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
router.include_router(download_router, prefix="/download", tags=["download"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(auth_router, prefix="/auth", tags=["authentication"])
router.include_router(system_router, prefix="/system", tags=["system"])

__all__ = ["router"]