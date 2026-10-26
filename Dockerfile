# Web UI
FROM node:24-bookworm-slim AS web

WORKDIR /web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# Python dependencies
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

# Copy application code and the built UI
COPY src/ src/
COPY --from=web /web/dist /app/web/dist

ENV API_HOST=0.0.0.0
ENV WEB_ROOT=/app/web/dist

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "echo"]
