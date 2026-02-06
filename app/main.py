from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import get_settings
from app.api import auth_router, code_router, get_agent_routes
from app.api.routes import preview_router
from app.services.cleanup import ensure_previews_dir, cleanup_expired_previews

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Bridge IDE - Execute code, GitHub OAuth, and AI project generation",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(code_router, prefix=settings.API_V1_STR)

# Lazy load agent routes to avoid import errors
try:
    agent_routes_module = get_agent_routes()
    app.include_router(agent_routes_module.router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])
    projects = agent_routes_module.projects  # Access active projects
except Exception as e:
    logger.warning(f"Failed to load agent routes: {e}")
    projects = {}

app.include_router(preview_router, tags=["preview"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth",
            "code": "/api/code",
            "agents": "/api/agents"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# Initialize previews directory and mount static file serving
ensure_previews_dir()
previews_path = Path("/tmp/previews").resolve()
app.mount("/preview", StaticFiles(directory=previews_path), name="previews")


# Background scheduler for cleanup
scheduler = BackgroundScheduler()


def scheduled_cleanup():
    """Periodic cleanup of expired previews - runs every 30 minutes."""
    logger.info("Running scheduled preview cleanup...")
    try:
        result = cleanup_expired_previews(projects, expire_hours=24)
        logger.info(f"Cleanup complete: {result['cleaned_count']} removed, {result['freed_space_mb']}MB freed")
    except Exception as e:
        logger.error(f"Scheduled cleanup failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize background scheduler on app startup."""
    ensure_previews_dir()
    
    # Schedule cleanup job to run every 30 minutes
    scheduler.add_job(
        scheduled_cleanup,
        "interval",
        minutes=30,
        id="preview_cleanup",
        name="Cleanup expired previews",
        replace_existing=True
    )
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started - cleanup runs every 30 minutes")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler shut down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        timeout_keep_alive=300,  # Keep connections alive for 5 minutes for long SSE streams
        timeout_graceful_shutdown=30  # Allow 30 seconds for graceful shutdown
    )
