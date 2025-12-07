"""
AHF Middleware API - Main Application

FastAPI application entry point for the AI Hub Framework middleware.

Usage:
    # Run with uvicorn
    uvicorn middleware.main:app --reload
    
    # Or run directly
    python -m middleware.main

Version: 1.0.0
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import tools_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting AHF Middleware API on {settings.api.host}:{settings.api.port}")
    print(f"API Prefix: {settings.api.api_prefix}")
    print(f"Tools Bucket: {settings.s3.tools_bucket}")
    
    yield
    
    # Shutdown
    print("Shutting down AHF Middleware API")


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
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "ahf-middleware"}
    
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
