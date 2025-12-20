"""
Embedded editor routes for phraze.so integration
"""

from fastapi import APIRouter
from .routes import router as embedded_router
from .mock_routes import router as mock_router
from .upload import router as upload_router

router = APIRouter()

# Include main embedded routes
router.include_router(embedded_router)

# Include upload routes for audio file uploads
router.include_router(upload_router, tags=["Embedded Upload"])

# Include mock routes for testing (only available in development)
router.include_router(mock_router, prefix="/mock", tags=["Mock Testing"])

__all__ = ["router"]
