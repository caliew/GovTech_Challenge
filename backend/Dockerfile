# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Create writable data directory for SQLite database
RUN mkdir -p /app/data

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY backend/requirements.txt /app/backend/requirements.txt

# Install python dependencies (Linux has pre-compiled wheels for all packages)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

# Copy all backend source code
COPY backend /app/backend
COPY .env /app/.env

# Expose port
EXPOSE 8000

# Run FastAPI backend using Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
