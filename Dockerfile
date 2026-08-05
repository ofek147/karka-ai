FROM python:3.12-slim

WORKDIR /app

# WeasyPrint system deps (verified list for Debian Bookworm / python:3.12-slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libfontconfig1 \
    libffi8 \
    fonts-liberation \
    fonts-noto \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

EXPOSE 8000

# Shell form so $PORT env var expands correctly on Railway
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
