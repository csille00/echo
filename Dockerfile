# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy package metadata (hatchling requires README.md at build time)
COPY pyproject.toml README.md .
COPY src/ src/

# Install dependencies
RUN uv pip install --system --no-cache -e ".[ocr-google-vision,ocr-tesseract,embeddings-google,llm-cleanup]"

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Install tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "journal_search"]
