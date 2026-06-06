# ── Stage 1: Frontend build ────────────────────────────────────────────────
# Compiles JSX → plain JS with esbuild.  No Node.js ends up in the final image.
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend-src
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY frontend/src ./src
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────
FROM python:3.12-slim

# System deps:
#   ghostscript / poppler-utils  — PDF rasterisation
#   libpq-dev / gcc              — asyncpg / psycopg2 build deps
#   curl                         — healthcheck
#   antiword                     — legacy .doc text extraction
#   libreoffice-writer           — DOCX → PDF headless conversion (Phase D2)
#     fonts-liberation / fonts-dejavu-core — common font coverage for DOCX rendering
#   Note: add libreoffice-impress here when PPTX support is introduced (Phase D3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    poppler-utils \
    libpq-dev \
    gcc \
    curl \
    antiword \
    libreoffice-writer \
    libreoffice-java-common \
    default-jre-headless \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

# Let javaldx find the JVM — without JAVA_HOME it searches blindly and exits 1
RUN echo "export JAVA_HOME=$(readlink -f /usr/bin/java | sed 's|/bin/java||')" >> /etc/profile.d/java.sh
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

WORKDIR /app

# Install Python dependencies (layer-cached independently of app code)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend/ .

# Copy static frontend files (HTML + api.js)
COPY frontend/SecureDoc.html /frontend/SecureDoc.html
COPY frontend/api.js /frontend/api.js
# Copy compiled JS bundle produced by Stage 1
COPY --from=frontend-builder /frontend-src/dist/app.bundle.js /frontend/dist/app.bundle.js

RUN chmod +x entrypoint.sh

# Run as non-root to limit blast radius if the app is compromised.
# UID 1001 avoids conflicts with common system users.
RUN useradd -r -u 1001 -s /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
# Default: API server.  Worker overrides this CMD in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
