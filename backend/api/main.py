"""
Main FastAPI application for video text inpainting service
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import logging
from contextlib import asynccontextmanager

from backend.config import settings, validate_settings
from backend.models.database import init_database

# Import routes from refactored subdirectories
from backend.api.routes.auth import router as auth_router
from backend.api.routes.users import router as users_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.files import router as files_router
from backend.api.routes.admin import router as admin_router
from backend.api.routes.video_editors import router as video_editors_router
from backend.api.routes.upload import router as upload_router
from backend.api.routes.init_db_endpoint import router as init_db_router
from backend.api.routes.test_login_debug import router as debug_router

from backend.api.websocket import websocket_router

# Configure logging with timezone
import os
os.environ['TZ'] = settings.timezone

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting Video Text Inpainting Service")
    
    try:
        # Validate configuration
        validate_settings()
        logger.info("Configuration validated successfully")
        
        # Initialize database
        init_database()
        logger.info("Database initialized successfully")
        
        # Additional startup tasks could go here
        # - Start background tasks
        # - Initialize external services
        # - Load ML models
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Video Text Inpainting Service")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Professional video text inpainting service with automatic text detection and removal",
    version=settings.app_version,
    openapi_url="/api/v1/openapi.json" if settings.debug else None,
    docs_url="/api/v1/docs" if settings.debug else None,
    redoc_url="/api/v1/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Trust proxy headers in production
if settings.environment == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} - {process_time:.4f}s - "
        f"{request.method} {request.url}"
    )
    
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler: {exc}", exc_info=True)
    import traceback
    error_detail = str(exc) if settings.debug else "Internal server error"
    traceback_str = traceback.format_exc() if settings.debug else None
    if traceback_str:
        logger.error(f"Traceback: {traceback_str}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_detail,
            "error_id": str(int(time.time())),  # Simple error ID for tracking
            "traceback": traceback_str if settings.debug else None
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": time.time()
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "message": "Video Text Inpainting Service API",
        "docs_url": "/api/v1/docs" if settings.debug else None,
        "health_url": "/health"
    }

# Include API routers from refactored subdirectories
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix="/api/v1/users",
    tags=["Users"]
)

app.include_router(
    jobs_router,
    prefix="/api/v1/jobs",
    tags=["Video Processing Jobs"]
)

app.include_router(
    files_router,
    prefix="/api/v1/files",
    tags=["File Management"]
)

app.include_router(
    admin_router,
    prefix="/api/v1/admin",
    tags=["Administration"]
)

app.include_router(
    video_editors_router,
    prefix="/api/v1/video-editors",
    tags=["Video Editors (GhostCut, Sync API)"]
)

app.include_router(
    upload_router,
    prefix="/api/v1",
    tags=["Upload and Process"]
)

# Include database initialization router (for setup only)
app.include_router(
    init_db_router,
    prefix="/api/v1/setup",
    tags=["Setup"]
)

# Include debug router (for development only)
app.include_router(
    debug_router,
    prefix="/api/v1/debug",
    tags=["Debug"]
)

# Include WebSocket router
app.include_router(websocket_router)

# Serve static files in development
if settings.debug:
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")

# API versioning endpoint
@app.get("/api/v1")
async def api_version():
    """API version information"""
    return {
        "version": "v1",
        "service": settings.app_name,
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users", 
            "jobs": "/api/v1/jobs",
            "files": "/api/v1/files",
            "admin": "/api/v1/admin",
            "websocket": "/ws"
        }
    }

# Metrics endpoint (if enabled)
if settings.enable_metrics:
    @app.get("/metrics")
    async def metrics():
        """Basic metrics endpoint"""
        # This could be extended with Prometheus metrics
        return {
            "status": "metrics_enabled",
            "timestamp": time.time()
        }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
        log_level=settings.log_level.lower()
    )