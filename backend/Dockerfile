FROM python:3.12-slim

# Ghostscript + Poppler for pdf2image
RUN apt-get update && apt-get install -y \
    ghostscript \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
