FROM python:3.11-slim

WORKDIR /app

# Air-gap: block HuggingFace Hub network access at OS level
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_PROGRESS_BARS=1

# install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --timeout=600 \
    --retries=5 \
    -r requirements.txt

# copy application code
COPY . .

# create directories
RUN mkdir -p faiss_index

# expose port
EXPOSE 8000

# health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python3", "main.py"]