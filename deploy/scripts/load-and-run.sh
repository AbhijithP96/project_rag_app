#!/bin/bash
# load-and-run.sh
# Run on RHEL9 VM to load images and start the app
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "=================================================="
echo " RAG App — Load and Run on RHEL9 VM"
echo "=================================================="

# ── check Docker is installed ─────────────────────────
echo ""
echo "Checking Docker..."

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed."
    echo ""
    echo "Install Docker offline — see README Section 2.2"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1 && \
   ! command -v docker compose >/dev/null 2>&1; then
    echo "ERROR: Docker Compose not found."
    echo "Install docker-compose-plugin — see README Section 2.2"
    exit 1
fi

echo "Docker $(docker --version) ✓"

# check if running without sudo
if ! docker ps >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to Docker daemon."
    echo "Either run with sudo or add user to docker group:"
    echo "  sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi

# ── check GPU ─────────────────────────────────────────
echo ""
echo "Checking GPU..."

GPU_AVAILABLE=false
if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_AVAILABLE=true
    echo "GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null)"
    echo "GPU available ✓"
else
    echo "No NVIDIA GPU detected — running in CPU mode"
    echo "Removing GPU section from docker-compose.yml..."
    # remove the GPU deploy section from compose file
    sed -i '/deploy:/,/capabilities: \[gpu\]/d' "$SCRIPT_DIR/docker-compose.yml"
fi

# ── verify required files ─────────────────────────────
echo ""
echo "Verifying bundle files..."

REQUIRED_FILES=(
    rag-backend.tar
    rag-frontend.tar
    ollama.tar
    ollama-models.tar.gz
    docker-compose.yaml
    .env
)

for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$f" ]; then
        echo "ERROR: $f not found in $(pwd)"
        echo "Make sure you extracted the full bundle"
        exit 1
    fi
    echo "  $f ✓"
done

# ── verify checksums ──────────────────────────────────
if [ -f "$SCRIPT_DIR/sha256sums.txt" ]; then
    echo ""
    echo "Verifying checksums..."
    cd "$SCRIPT_DIR"
    sha256sum -c sha256sums.txt
    echo "Checksums verified ✓"
fi

# ── 1. load Docker images ─────────────────────────────
echo ""
echo "[1/4] Loading Docker images..."

docker load -i "$SCRIPT_DIR/rag-backend.tar"
echo "  rag-backend:latest  ✓"

docker load -i "$SCRIPT_DIR/rag-frontend.tar"
echo "  rag-frontend:latest ✓"

docker load -i "$SCRIPT_DIR/ollama.tar"
echo "  ollama/ollama:latest ✓"

echo "All images loaded ✓"
echo ""
echo "Available images:"
docker images | grep -E "rag-backend|rag-frontend|ollama"

# ── 2. restore Ollama models volume ───────────────────
echo ""
echo "[2/4] Restoring Ollama models..."

# create the volume if it does not exist
docker volume create ollama_models 2>/dev/null || true

# restore models from tarball into the volume
docker run --rm \
    -v ollama_models:/data \
    -v "$SCRIPT_DIR":/backup \
    alpine \
    tar xzf /backup/ollama-models.tar.gz -C /data

echo "Ollama models restored ✓"

# ── 3. configure host filesystem mount ────────────────
echo ""
echo "[3/4] Configuring host filesystem access..."

echo ""
echo "The backend needs access to your documents folder."
echo "Default: your home directory (~) is mounted at /host/home"
echo "inside the backend container."
echo ""
echo "To change which folder is accessible, edit .env:"
echo "  HOST_DOCS_PATH=/path/to/your/docs"
echo ""
echo "Current setting:"
grep HOST_DOCS_PATH "$SCRIPT_DIR/.env" || \
    echo "  HOST_DOCS_PATH=~ (default)"

# expand ~ in .env if present
sed -i "s|HOST_DOCS_PATH=~|HOST_DOCS_PATH=$HOME|g" \
    "$SCRIPT_DIR/.env"

echo ""
echo "Host path mounted into container at: /host/home"
echo "Index documents using path: /host/home/your/docs/folder"

# ── 4. start services ─────────────────────────────────
echo ""
echo "[4/4] Starting services..."

cd "$SCRIPT_DIR"
docker compose up -d

echo ""
echo "Waiting for services to be ready..."

# wait for Ollama
echo "Waiting for Ollama..."
for i in $(seq 1 20); do
    if docker exec rag-ollama \
        ollama list >/dev/null 2>&1; then
        echo "Ollama ready ✓"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "ERROR: Ollama did not start"
        docker logs rag-ollama | tail -20
        exit 1
    fi
    printf "  waiting... (%ds)\r" $((i * 3))
    sleep 3
done

# wait for backend
echo "Waiting for backend..."
for i in $(seq 1 24); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend ready ✓"
        break
    fi
    if [ "$i" -eq 24 ]; then
        echo "ERROR: Backend did not start"
        docker logs rag-backend | tail -20
        exit 1
    fi
    printf "  waiting... (%ds)\r" $((i * 5))
    sleep 5
done

echo "Frontend starting..."
sleep 5

echo ""
echo "=================================================="
echo " RAG App is running!"
echo ""
echo "  Open in browser:  http://localhost:3000"
echo "  Backend health:   http://localhost:8000/health"
echo "  Ollama models:    http://localhost:11434/"
echo ""
echo "  Documents:  mount your docs folder into the container"
echo "    edit .env → HOST_DOCS_PATH=/path/to/docs"
echo "    then: docker compose restart rag-backend"
echo "    index using path: /host/home/..."
echo ""
echo "  Logs:"
echo "    docker compose logs -f rag-backend"
echo "    docker compose logs -f rag-frontend"
echo "    docker compose logs -f ollama"
echo ""
echo "  Stop:        docker compose down"
echo "  Full reset:  docker compose down -v"
echo "=================================================="