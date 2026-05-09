FROM python:3.12-slim

# System deps: PDF rasterization (poppler + ghostscript), Postgres client, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    poppler-utils \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (layer-cached independently of app code)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend/ .

# Copy frontend so FastAPI StaticFiles can serve it at /static (path /frontend)
COPY frontend/ /frontend/

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
# Default: API server.  Worker overrides this CMD in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
