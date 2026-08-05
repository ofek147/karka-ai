# Playwright official image — comes with Chromium + all system deps pre-installed
# Ubuntu Jammy (22.04) base — stable, well-tested on Railway
FROM mcr.microsoft.com/playwright/python:v1.47.0-noble

WORKDIR /app

# WeasyPrint system deps (Ubuntu Jammy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libfontconfig1 \
    fonts-liberation \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (layer cache)
COPY backend/requirements.txt .
# cache-bust: 2026-08-05
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

EXPOSE 8000

# Shell form so $PORT env var expands correctly on Railway
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
