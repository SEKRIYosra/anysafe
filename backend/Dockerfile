# Use a secure, slim Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files & buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for caching layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY . ./backend

# Create a non-privileged system user for execution (Least Privilege Container)
RUN groupadd -r appgroup && useradd -r -g appgroup -s /sbin/nologin appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Expose API port
EXPOSE 8080

# Start server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
