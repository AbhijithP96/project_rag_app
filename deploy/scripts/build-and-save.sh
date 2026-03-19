#!/bin/bash
# build-and-save.sh
# Run on internet machine to build images, pull Ollama
# and save everything as tarballs for airgap deployment
set -e

echo "=================================================="
echo " RAG App — Build and Save Docker Images"
echo " Run this on an internet-connected machine"
echo "=================================================="

PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUTPUT_DIR="$PROJECT_ROOT/deploy/dist"

echo ""
echo "Project root: $PROJECT_ROOT"
echo "Output dir:   $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

# pre-flight checks
echo ""
echo "Checking prerequisites..."

command -v docker >/dev/null || {
    echo "ERROR: Docker not installed"
    echo "Install: https://docs.docker.com/engine/install/"
    exit 1
}

command -v curl >/dev/null || {
    echo "ERROR: curl not found"
    exit 1
}

# check BGE reranker model exists
if [ ! -d "$PROJECT_ROOT/backend/models/bge-reranker-base" ]; then
    echo ""
    echo "ERROR: BGE reranker model not found."
    echo ""
    echo "Download it first:"
    echo "  pip install -U huggingface_hub"
    echo "  hf download BAAI/bge-reranker-base \\"
    echo "      --local-dir rag-backend/models/bge-reranker-base \\"
    echo "      --local-dir-use-symlinks False"
    exit 1
fi

echo "All prerequisites met ✓"

# 1. build backend image 
echo ""
echo "[1/6] Building backend Docker image..."

docker build \
    -t rag-backend:latest \
    -f "$PROJECT_ROOT/backend/Dockerfile" \
    "$PROJECT_ROOT/backend"

echo "rag-backend:latest built ✓"

# 2. build frontend image
echo ""
echo "[2/6] Building frontend Docker image..."

docker build \
    -t rag-frontend:latest \
    -f "$PROJECT_ROOT/frontend/Dockerfile" \
    "$PROJECT_ROOT/frontend"

echo "rag-frontend:latest built ✓"

# 3. pull Ollama image
echo ""
echo "[3/6] Pulling Ollama Docker image..."

docker pull ollama/ollama:latest
echo "ollama/ollama:latest pulled ✓"

# 4. pull Ollama models inside container
echo ""
echo "[4/6] Pulling Ollama models (llama3.2:3b + mxbai-embed-large)..."

# start a temporary ollama container to pull models
# models are saved into the named volume ollama_models
docker run -d \
    --name ollama-init \
    -v ollama_models:/root/.ollama \
    ollama/ollama:latest

echo "Waiting for Ollama container to start..."
for i in $(seq 1 20); do
    if docker exec ollama-init \
        ollama list >/dev/null 2>&1; then
        echo "Ollama container ready ✓"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "ERROR: Ollama container did not start"
        docker logs ollama-init
        docker rm -f ollama-init
        exit 1
    fi
    sleep 3
done

echo "Pulling llama3.2:3b (~2.0 GB)..."
docker exec ollama-init ollama pull llama3.2:3b

echo "Pulling mxbai-embed-large (~669 MB)..."
docker exec ollama-init ollama pull mxbai-embed-large:latest

echo "Installed models:"
docker exec ollama-init ollama list

# stop and remove init container
docker stop ollama-init
docker rm ollama-init
echo "Ollama models pulled into volume ✓"

# 5. save images to tar files
echo ""
echo "[5/6] Saving Docker images to tar files..."

docker save rag-backend:latest    -o "$OUTPUT_DIR/rag-backend.tar"
echo "  rag-backend.tar    $(du -sh "$OUTPUT_DIR/rag-backend.tar"    | cut -f1)"

docker save rag-frontend:latest   -o "$OUTPUT_DIR/rag-frontend.tar"
echo "  rag-frontend.tar   $(du -sh "$OUTPUT_DIR/rag-frontend.tar"   | cut -f1)"

docker save ollama/ollama:latest  -o "$OUTPUT_DIR/ollama.tar"
echo "  ollama.tar         $(du -sh "$OUTPUT_DIR/ollama.tar"         | cut -f1)"

echo "Images saved ✓"

# 6. export Ollama models volume
echo ""
echo "[6/6] Exporting Ollama models volume..."

# use a temporary alpine container to tar the volume contents
docker run --rm \
    -v ollama_models:/data \
    -v "$OUTPUT_DIR":/backup \
    alpine \
    tar czf /backup/ollama-models.tar.gz -C /data .

echo "  ollama-models.tar.gz  $(du -sh "$OUTPUT_DIR/ollama-models.tar.gz" | cut -f1)"
echo "Ollama models volume exported ✓"

# copy supporting files
echo ""
echo "Copying supporting files..."

cp "$PROJECT_ROOT/docker-compose.yml" "$OUTPUT_DIR/"
cp "$PROJECT_ROOT/deploy/.env"               "$OUTPUT_DIR/"
cp "$PROJECT_ROOT/deploy/scripts/load-and-run.sh" "$OUTPUT_DIR/"
chmod +x "$OUTPUT_DIR/load-and-run.sh"

# generate checksums
echo ""
echo "Generating checksums..."
cd "$OUTPUT_DIR"
sha256sum \
    rag-backend.tar \
    rag-frontend.tar \
    ollama.tar \
    ollama-models.tar.gz \
    > sha256sums.txt

cat sha256sums.txt

# create final tarball
echo ""
echo "Creating final tarball..."
cd "$PROJECT_ROOT/deploy"
tar czf rag-app-docker.tar.gz dist/

echo ""
echo "=================================================="
echo " Build complete!"
echo ""
echo " Output: deploy/rag-app-docker.tar.gz"
echo " Size:   $(du -sh rag-app-docker.tar.gz | cut -f1)"
echo ""
echo " Contents:"
printf "   %-30s %s\n" "rag-backend.tar"       "$(du -sh "$OUTPUT_DIR/rag-backend.tar"       | cut -f1)   FastAPI backend image"
printf "   %-30s %s\n" "rag-frontend.tar"      "$(du -sh "$OUTPUT_DIR/rag-frontend.tar"      | cut -f1)   React frontend image"
printf "   %-30s %s\n" "ollama.tar"            "$(du -sh "$OUTPUT_DIR/ollama.tar"            | cut -f1)   Ollama server image"
printf "   %-30s %s\n" "ollama-models.tar.gz"  "$(du -sh "$OUTPUT_DIR/ollama-models.tar.gz"  | cut -f1)   LLM + embedding models"
printf "   %-30s %s\n" "docker-compose.yml"    "                 Compose file"
printf "   %-30s %s\n" ".env"                  "                 Environment config"
printf "   %-30s %s\n" "load-and-run.sh"       "                 VM setup script"
echo ""
echo " Transfer to VM:"
echo "   cp deploy/rag-app-docker.tar.gz /media/usb/"
echo "=================================================="