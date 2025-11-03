# Multi-stage build for Crawler Service

# Stage 1: Builder
FROM python:3.13-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create wheels for all dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 crawler

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .

# Install Python dependencies from wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY src/ ./src/
COPY .env.example .env.example

# Set ownership
RUN chown -R crawler:crawler /app

# Switch to non-root user
USER crawler

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9101/metrics', timeout=5)" || exit 1

# Expose ports
EXPOSE 9101

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

# Run application
CMD ["python", "-m", "src.main"]

