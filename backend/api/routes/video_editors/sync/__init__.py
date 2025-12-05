"""
Sync API routes for lip-sync video processing

Includes:
- /sync-process: Simple lip-sync for normal video editor (single audio file)
- /pro-sync-process: Pro lip-sync with segments (multiple audio files)
"""

from fastapi import APIRouter

router = APIRouter()

# Import Pro Sync API routes (segments-based lip-sync)
try:
    from .routes import router as pro_sync_routes
    router.include_router(pro_sync_routes)
except ImportError as e:
    import logging
    logging.warning(f"Could not import pro sync routes: {e}")

# Import Simple Sync API routes (single audio lip-sync for normal editor)
try:
    from .sync_api_original import router as simple_sync_routes
    router.include_router(simple_sync_routes)
except ImportError as e:
    import logging
    logging.warning(f"Could not import simple sync routes: {e}")

__all__ = ["router"]
