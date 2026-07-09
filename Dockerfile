FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend:/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/auth ./backend/auth
COPY backend/config ./backend/config
COPY backend/etl ./backend/etl
COPY backend/api ./backend/api
COPY backend/shared ./backend/shared
COPY paquetes ./paquetes
COPY frontend ./frontend

RUN mkdir -p /app/data/raw /app/data/parquet

EXPOSE 5000 8000
