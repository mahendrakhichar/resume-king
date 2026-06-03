"""Main entry point for the ResumeForge AI backend application."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from db.database import init_db, close_db
from services.vector_service import VectorService
from api.routes import resumes, sessions, export, agents
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup folder preparations, database and ChromaDB initializations."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version} under environment: {settings.app_env}")
    
    # 1. Create upload storage directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # 2. Initialize database schemas (dev auto-creation)
    if settings.app_env == "development":
        logger.info("Dev Mode: Automatically creating PostgreSQL database schemas...")
        try:
            await init_db()
            logger.info("Database schemas initialized.")
        except Exception as e:
            logger.error(f"Failed to auto-initialize DB tables: {e}. Ensure DATABASE_URL is correct.")
            
    # 3. Initialize ChromaDB vector service
    logger.info("Initializing vector indexing client...")
    VectorService.get_client()
    logger.info("ChromaDB vector client initialized successfully.")
    
    yield
    
    # Clean up operations on shutdown
    logger.info("Cleaning up backend resources...")
    await close_db()
    logger.info("Shutdown lifecycle complete.")


# Initialize FastAPI App
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Multi-Agent Resume Optimization and Application Tailoring Platform backend API.",
    lifespan=lifespan,
    debug=settings.app_debug
)

# Configure CORS Middleware
# Allows seamless API queries from modern frontend setups (such as React on Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(resumes.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(agents.router)  # Mounted raw for /ws endpoint path formatting


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple API check confirming status of all core operations."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env
    }
