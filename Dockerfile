# Playwright official image — comes with Chromium + all system deps pre-installed
# Ubuntu Jammy (22.04) base — stable, well-tested on Railway
FROM mcr.microsoft.com/playwright/python:v1.47.0-noble

WORKDIR /app

# Install deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

EXPOSE 8000

# Shell form so $PORT env var expands correctly on Railway
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
