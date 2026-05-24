# ============================================================
# SBERT News Search API -- Dockerfile (Complete Solution)
# Module 4 Branch Project
#
# Build:  docker build -t sbert-search .
# Run:    docker run -p 5001:5001 sbert-search
# ============================================================

FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr (important for Docker logs)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy requirements first for Docker layer caching --
# dependencies change less often than source code, so this
# layer gets cached and reused across builds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project source code into the container
COPY . .

# Document the port the API listens on
EXPOSE 5001

# Default command: start the Flask server
CMD ["python", "server.py"]
