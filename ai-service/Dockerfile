# ── AI Service Dockerfile — Chapter 4.6.1 ──
# Tech: FastAPI + PyTorch + Neo4j + FAISS (PDF 3.9.1)

FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only (lightweight)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu --no-cache-dir

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for models and data
RUN mkdir -p trained_models data

# Expose port
EXPOSE 8002

# Copy entrypoint and make executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run entrypoint (waits for product-service, builds FAISS, starts FastAPI)
CMD ["/app/entrypoint.sh"]

