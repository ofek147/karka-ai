FROM python:3.12-slim

WORKDIR /app

# System deps for WeasyPrint + fonts only
# Playwright/Chromium not needed — pl_url from iplan is a direct PDF link (no JS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libfontconfig1 \
    fonts-liberation \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

EXPOSE 8000

# Shell form so $PORT env var expands correctly on Railway
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
