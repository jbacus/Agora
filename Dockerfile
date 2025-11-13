# ============================================
# Multi-Stage Dockerfile for Virtual Debate Panel
# ============================================
# Inspired by Near-to-Far and COdePILOT production patterns
# Stage 1: Builder - Process data and generate embeddings (optional)
# Stage 2: Runtime - FastAPI application

# ============================================
# Stage 1: Builder (Optional - for build-time preprocessing)
# ============================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config
COPY config/ config/
COPY scripts/ scripts/
COPY src/ src/

# Copy raw data if available (optional - for build-time embedding generation)
# Uncomment this section when you're ready for production preprocessing
# COPY data/raw/ data/raw/
# RUN python scripts/preprocess_all_authors.py
# RUN python scripts/batch_generate_embeddings.py

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data/chroma_db /app/logs && \
    chown -R appuser:appuser /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ config/
COPY src/ src/
COPY scripts/ scripts/

# Copy preprocessed data from builder (if available)
# COPY --from=builder /build/data/processed/ data/processed/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables (can be overridden at runtime)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV API_HOST=0.0.0.0
ENV API_PORT=8080
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
