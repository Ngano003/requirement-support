# Backend Dockerfile for Requirements Support AI System

FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    watchdog

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data/requirements /data/sessions

# Expose port
EXPOSE 8001

# Run with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# Production stage
FROM base as production

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data/requirements /data/sessions

# Expose port
EXPOSE 8001

# Run without reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
