# =============================================================================
# AHF (AI Hub Framework) - Fargate Base Image
# =============================================================================
# 
# Production-ready Docker image for AWS Fargate deployment.
# This serves as a base image for building AI-powered workflow applications.
#
# Features:
# - Multi-stage build for smaller image size
# - Non-root user for security
# - Health check support
# - Graceful shutdown handling (SIGTERM)
# - Optimized for Python async workloads
#
# Build:
#   docker build -t ahf-base:latest .
#
# Run locally:
#   docker run -p 8000:8000 ahf-base:latest
#
# Fargate:
#   - Task CPU: 256-4096 (0.25-4 vCPU)
#   - Task Memory: 512-30720 MB
#   - Recommended: 1024 CPU, 2048 MB memory for production
#
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency resolution
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./
COPY utils/pyproject.toml ./utils/

# Install dependencies using uv (faster than pip)
RUN uv pip install --system --no-cache -e . 

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

# Labels for container registry
LABEL org.opencontainers.image.title="AHF - AI Hub Framework"
LABEL org.opencontainers.image.description="Production base image for AI-powered workflows"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="AHF"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # AHF-specific
    AHF_ENVIRONMENT=production \
    AHF_LOG_LEVEL=INFO \
    # Uvicorn
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_WORKERS=1 \
    UVICORN_LOOP=uvloop \
    UVICORN_HTTP=httptools \
    # Graceful shutdown timeout (Fargate sends SIGTERM)
    UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=30

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup core/ ./core/
COPY --chown=appuser:appgroup utils/ ./utils/
COPY --chown=appuser:appgroup middleware/ ./middleware/

# Create logs directory
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app/logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check for Fargate
# Fargate uses this to determine container health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Default command - run the middleware API
# For custom workflows, override this in your derived Dockerfile
CMD ["python", "-m", "uvicorn", "middleware.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--timeout-graceful-shutdown", "30"]

