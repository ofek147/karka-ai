FROM python:3.12-slim

WORKDIR /app

# Install deps first (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

EXPOSE 8000

# Shell form so $PORT env var expands correctly on Railway
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
