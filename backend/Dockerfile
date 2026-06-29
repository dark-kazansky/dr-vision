# ═══════════════════════════════════════════════════════════════════════════════
# Doc Intelligence Backend — Production Dockerfile
# Multi-stage build: dependencies cached separately from application code.
# ═══════════════════════════════════════════════════════════════════════════════

# --- Stage 1: Dependencies ---
FROM python:3.11-slim AS deps

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim

WORKDIR /app

# Runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from deps stage
COPY --from=deps /install /usr/local

# Copy application code
COPY . .

# Remove dev/test artifacts from image
RUN rm -rf tests/ .pytest_cache/ .ruff_cache/ .hypothesis/ __pycache__/ \
    .env .env.example Dockerfile Dockerfile.dev .dockerignore

# Non-root user for security
RUN useradd -r -s /bin/false appuser \
    && mkdir -p /backend/data/uploaded \
    && chown -R appuser:appuser /app /backend
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

CMD ["python", "main.py"]
