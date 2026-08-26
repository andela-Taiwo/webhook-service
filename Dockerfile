# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (much faster than pip)
# Create a virtual environment in /app/.venv
RUN uv sync --frozen --no-dev

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.13-slim AS runtime

# Set labels for better container management
LABEL maintainer="your-email@example.com"
LABEL description="Production-grade webhook service with FastAPI"
LABEL version="1.0.0"

# Create non-root user for security
RUN groupadd -r webhook && useradd -r -g webhook webhook

# Set working directory
WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for PostgreSQL async driver
    libpq5 \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=webhook:webhook src /app/src
COPY --chown=webhook:webhook alembic /app/alembic
COPY --chown=webhook:webhook alembic.ini /app/alembic.ini

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}" \
    WEBHOOK_ENVIRONMENT=production

# Create directory for logs with proper permissions
RUN mkdir -p /app/logs && chown -R webhook:webhook /app/logs

# Switch to non-root user
USER webhook

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

# Expose port
EXPOSE 8000

# Run migrations and start application
CMD ["sh", "-c", "alembic upgrade head && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"]

# ============================================================================
# Stage 3: Development - Include dev dependencies and tools
# ============================================================================
FROM builder AS development

# Install development dependencies
RUN uv sync --frozen

# Install additional dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy all files including tests
COPY . /app/

# Set environment for development
ENV WEBHOOK_ENVIRONMENT=local \
    WEBHOOK_LOG_JSON=false \
    PATH="/app/.venv/bin:${PATH}"

# Development server with auto-reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# Stage 4: Test - Run tests in isolated environment
# ============================================================================
FROM development AS test

# Set test environment variables
ENV WEBHOOK_ENVIRONMENT=test \
    WEBHOOK_DATABASE_URL=sqlite+aiosqlite:///:memory: \
    WEBHOOK_SECRET_KEY=test-secret-key

# Run linting and tests when container starts (not during build)
CMD ["sh", "-c", "echo 'Running linter...' && ruff check src/ tests/ && echo 'Running tests...' && pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml"]
