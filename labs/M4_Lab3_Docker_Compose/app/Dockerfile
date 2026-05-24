# FreshBasket Delay Predictor -- Streamlit Dashboard Image (M4 Lab 3 Compose variant)
# Loads pre-trained .pkl artifacts directly from ./artifacts/. No DB / S3 / MLflow.
#
# Build:   docker build -t freshbasket-dashboard .
# Run:     docker run -p 8501:8501 freshbasket-dashboard

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching: edits to app.py / artifacts don't bust this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code AND artifacts/ (the .pkl files the app loads at startup)
COPY app.py ./
COPY artifacts/ ./artifacts/

EXPOSE 8501

# Health check uses Python stdlib (python:3.12-slim doesn't ship curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).status == 200 else 1)"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
