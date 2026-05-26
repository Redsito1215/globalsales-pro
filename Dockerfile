FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/config ./backend/config
COPY backend/etl ./backend/etl
COPY backend/api ./backend/api
COPY frontend ./frontend
COPY scripts ./scripts

RUN mkdir -p /app/data/raw /app/data/parquet

EXPOSE 5000 8000
