# Multi-stage build for Ingest Validator microservice
# Stage 1: Builder
FROM python:3.13-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create wheels for all dependencies
RUN pip install --user --no-cache-dir --no-warn-script-location \
    -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set environment variables
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Copy application code
COPY src/ /app/src/
COPY schemas/ /app/schemas/

# Create non-root user for security
RUN useradd -m -u 1000 validator && \
    chown -R validator:validator /app

USER validator

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Expose port
EXPOSE 8080

# Run the service
CMD ["python", "-m", "src.main"]

