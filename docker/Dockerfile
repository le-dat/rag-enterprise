# ==========================================
# Stage 1: Build stage (compiles dependencies)
# ==========================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install compilation tools needed for C extension builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Set up virtual environment
RUN uv venv /.venv

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --no-cache-dir --python /.venv/bin/python -r requirements.txt

# ==========================================
# Stage 2: Runtime stage (minimal and secure)
# ==========================================
FROM python:3.12-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    PATH="/.venv/bin:$PATH" \
    PYTHONPATH="/app"

WORKDIR /app

# Install curl for healthcheck utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /.venv /.venv

# Create non-root application group and user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -d /app -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app

# Run all subsequent instructions as non-root user
USER appuser

# Pre-download fastembed models to non-root home directory (/app/.cache/fastembed)
# Run this BEFORE copying the app files so code changes do not invalidate this layer.
RUN python -c "from fastembed import TextEmbedding, SparseTextEmbedding; \
TextEmbedding(model_name='BAAI/bge-small-en-v1.5'); \
SparseTextEmbedding(model_name='prithivida/Splade_PP_en_v1')"

# Copy application files (set owner to appuser)
COPY --chown=appuser:appgroup . .

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501

# Default runtime command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
