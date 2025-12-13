"""
AHF Middleware API - Main Application

FastAPI application entry point for the AI Hub Framework middleware.
Optimized for containerized deployments (AWS Fargate, ECS, Kubernetes).

Features:
- Graceful shutdown with SIGTERM handling
- Connection pooling for HTTP clients
- Health check endpoints for load balancers
- Structured logging for CloudWatch

Usage:
    # Run with uvicorn
    uvicorn middleware.main:app --reload
    
    # Or run directly
    python -m middleware.main

Version: 1.1.0
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import tools_router

# Import session manager for Fargate-ready HTTP connection pooling
from core.tools import (
    get_session_manager,
    shutdown_session_manager,
    install_signal_handlers,
)

# Configure structured logging for CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ahf.middleware")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for Fargate/containerized deployments.
    
    Handles:
    - HTTP session manager startup (connection pooling)
    - Signal handler installation for graceful shutdown
    - Clean resource cleanup on shutdown
    """
    settings = get_settings()
    
    # Startup
    logger.info(
        "Starting AHF Middleware API",
        extra={
            "host": settings.api.host,
            "port": settings.api.port,
            "api_prefix": settings.api.api_prefix,
        }
    )
    
    # Initialize HTTP session manager for connection pooling
    session_manager = await get_session_manager()
    await session_manager.startup()
    logger.info("HTTP Session Manager initialized")
    
    # Install signal handlers for graceful shutdown (SIGTERM from Fargate)
    install_signal_handlers()
    
    yield
    
    # Shutdown - Clean up all resources
    logger.info("Shutting down AHF Middleware API")
    
    # Close HTTP session manager (closes all connections)
    await shutdown_session_manager()
    logger.info("HTTP Session Manager shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="AHF Middleware API",
        description="REST API for AI Hub Framework - Manage tools, agents, workflows, and prompts",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=f"{settings.api.api_prefix}/docs",
        redoc_url=f"{settings.api.api_prefix}/redoc",
        openapi_url=f"{settings.api.api_prefix}/openapi.json",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(
        tools_router,
        prefix=f"{settings.api.api_prefix}/tools",
        tags=["Tools"],
    )
    
    # Health check endpoint for Fargate/ALB
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for load balancers and container orchestration.
        
        Returns 200 if the service is healthy, includes session manager status.
        """
        try:
            session_manager = await get_session_manager()
            http_health = await session_manager.health_check()
        except Exception:
            http_health = {"healthy": False, "details": {"error": "Session manager unavailable"}}
        
        return {
            "status": "healthy" if http_health.get("healthy", True) else "degraded",
            "service": "ahf-middleware",
            "version": "1.1.0",
            "checks": {
                "http_session_manager": http_health,
            }
        }
    
    # Readiness probe for Kubernetes/Fargate
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        """Readiness probe - checks if the service is ready to accept traffic."""
        try:
            session_manager = await get_session_manager()
            is_ready = session_manager.is_healthy
        except Exception:
            is_ready = False
        
        if is_ready:
            return {"ready": True}
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"ready": False, "reason": "HTTP session manager not ready"}
            )
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API info."""
        return {
            "service": "AHF Middleware API",
            "version": "1.0.0",
            "docs": f"{settings.api.api_prefix}/docs",
            "health": "/health",
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "middleware.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
    )
