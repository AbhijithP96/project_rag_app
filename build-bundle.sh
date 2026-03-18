#!/bin/bash
# build-bundle.sh
# Run on internet machine to package everything for RHEL9 airgap deployment
set -e

echo "=================================================="
echo " RAG App — Build Airgap Bundle"
echo " Run this on an internet-connected machine"
echo "=================================================="

PROJECT_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BUNDLE_DIR="$PROJECT_ROOT/deploy/bundle/rag-app-bundle"
PREP_DIR="$PROJECT_ROOT/deploy/bundle-prep"

echo ""
echo "Project root: $PROJECT_ROOT"
echo "Bundle dir:   $BUNDLE_DIR"

# ── pre-flight checks ──────────────────────────────────
echo ""
echo "Checking prerequisites..."

command -v python3 >/dev/null || { echo "ERROR: python3 not found"; exit 1; }
command -v node    >/dev/null || { echo "ERROR: node not found";    exit 1; }
command -v npm     >/dev/null || { echo "ERROR: npm not found";     exit 1; }
command -v curl    >/dev/null || { echo "ERROR: curl not found";    exit 1; }

# check BGE reranker exists
if [ ! -d "$PROJECT_ROOT/rag-backend/models/bge-reranker-base" ]; then
    echo ""
    echo "ERROR: BGE reranker model not found at:"
    echo "  rag-backend/models/bge-reranker-base/"
    echo ""
    echo "Download it first:"
    echo "  pip install huggingface_hub"
    echo "  huggingface-cli download BAAI/bge-reranker-base \\"
    echo "      --local-dir rag-backend/models/bge-reranker-base \\"
    echo "      --local-dir-use-symlinks False"
    exit 1
fi

# check Node.js tarball exists in bundle-prep
NODE_TARBALL=$(find "$PREP_DIR/node" -name "node-v*-linux-x64.tar.xz" 2>/dev/null | head -1)
if [ -z "$NODE_TARBALL" ]; then
    echo ""
    echo "ERROR: Node.js tarball not found."
    echo ""
    echo "Download from: https://nodejs.org/en/download"
    echo "Select: Linux x64 Prebuilt Binary (.tar.xz)"
    echo "Save to: deploy/bundle-prep/node/"
    echo ""
    echo "Or run:"
    echo "  mkdir -p deploy/bundle-prep/node"
    echo "  curl -Lo deploy/bundle-prep/node/node-v20.18.0-linux-x64.tar.xz \\"
    echo "      https://nodejs.org/dist/v20.18.0/node-v20.18.0-linux-x64.tar.xz"
    exit 1
fi

# check Ollama models are pre-pulled
if [ ! -d "$PREP_DIR/ollama/models" ] || \
   [ -z "$(ls "$PREP_DIR/ollama/models" 2>/dev/null)" ]; then
    echo ""
    echo "ERROR: Ollama models not found at deploy/bundle-prep/ollama/models/"
    echo ""
    echo "Pull models first — see Section 1.5 of README-AIRGAP.md"
    exit 1
fi

echo "All prerequisites met ✓"
echo "  Node.js tarball: $(basename "$NODE_TARBALL")"
echo "  BGE reranker:    $(du -sh "$PROJECT_ROOT/rag-backend/models/bge-reranker-base" | cut -f1)"
echo "  Ollama models:   $(du -sh "$PREP_DIR/ollama/models" | cut -f1)"

# ── clean and create directories ──────────────────────
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"/{python,node,ollama,backend,frontend,logs}
mkdir -p "$BUNDLE_DIR/backend"/{logs,faiss_index}
mkdir -p "$BUNDLE_DIR/ollama/models"

# ── 1. copy Python RPMs ───────────────────────────────
echo ""
echo "[1/7] Copying Python 3.11 RPMs..."

if [ -d "$PREP_DIR/python-rpms" ] && \
   [ -n "$(ls "$PREP_DIR/python-rpms"/*.rpm 2>/dev/null)" ]; then
    cp "$PREP_DIR/python-rpms/"*.rpm "$BUNDLE_DIR/python/"
    echo "Python RPMs copied ✓ ($(ls "$BUNDLE_DIR/python" | wc -l) packages)"
else
    echo "WARNING: Python RPMs not found in deploy/bundle-prep/python-rpms/"
    echo "The VM must have Python 3.9+ available from RHEL9 DVD"
    echo "Or see Section 1.4 of README to download RPMs"
fi

# ── 2. copy Node.js tarball ───────────────────────────
echo ""
echo "[2/7] Copying Node.js pre-built binary..."

cp "$NODE_TARBALL" "$BUNDLE_DIR/node/"
echo "Node.js tarball copied ✓ ($(basename "$NODE_TARBALL"))"

# ── 3. copy Ollama + models ───────────────────────────
echo ""
echo "[3/7] Copying Ollama tarball and models..."

cp "$PREP_DIR/ollama/ollama-linux-amd64.tar.gz" \
    "$BUNDLE_DIR/ollama/"

cp -r "$PREP_DIR/ollama/models" \
    "$BUNDLE_DIR/ollama/"

echo "Ollama tarball copied ✓"
echo "Ollama models copied ✓ ($(du -sh "$BUNDLE_DIR/ollama/models" | cut -f1))"

# ── 4. install frontend deps + copy ───────────────────
echo ""
echo "[4/7] Installing frontend dependencies and copying..."

cd "$PROJECT_ROOT/frontend"

echo "Running npm ci..."
npm ci

echo "Copying frontend files to bundle..."
cp -r node_modules/ "$BUNDLE_DIR/frontend/node_modules/"
cp -r src/          "$BUNDLE_DIR/frontend/src/"
cp package.json     "$BUNDLE_DIR/frontend/"
cp index.html       "$BUNDLE_DIR/frontend/"

[ -f package-lock.json ] && cp package-lock.json "$BUNDLE_DIR/frontend/"
[ -f vite.config.ts ]    && cp vite.config.ts    "$BUNDLE_DIR/frontend/"
[ -f tsconfig.json ]     && cp tsconfig.json     "$BUNDLE_DIR/frontend/"
[ -f tsconfig.node.json ] && cp tsconfig.node.json "$BUNDLE_DIR/frontend/"

# also build dist/ for production fallback
echo "Building production dist/..."
npm run build
cp -r dist/ "$BUNDLE_DIR/frontend/dist/"

echo "Frontend copied ✓"
echo "  node_modules: $(du -sh "$BUNDLE_DIR/frontend/node_modules" | cut -f1)"
echo "  dist:         $(du -sh "$BUNDLE_DIR/frontend/dist" | cut -f1)"

# ── 5. create Python venv ─────────────────────────────
echo ""
echo "[5/7] Creating Python virtual environment..."

cd "$PROJECT_ROOT/rag-backend"

python3 -m venv "$BUNDLE_DIR/backend/venv"
source "$BUNDLE_DIR/backend/venv/bin/activate"

pip install --upgrade pip wheel setuptools --quiet
pip install -r requirements.txt --quiet

echo "Downloading spacy language model..."
python3 -m spacy download en_core_web_lg

echo "Verifying packages..."
python3 -c "import fastapi"               && echo "  fastapi              ✓"
python3 -c "import langchain_ollama"      && echo "  langchain_ollama     ✓"
python3 -c "import faiss"                 && echo "  faiss                ✓"
python3 -c "import sentence_transformers" && echo "  sentence_transformers ✓"
python3 -c "import rank_bm25"             && echo "  rank_bm25            ✓"
python3 -c "import spacy"                 && echo "  spacy                ✓"

deactivate
echo "Python venv created ✓ ($(du -sh "$BUNDLE_DIR/backend/venv" | cut -f1))"

# ── 6. copy backend source + BGE reranker ─────────────
echo ""
echo "[6/7] Copying backend source files..."

cd "$PROJECT_ROOT/rag-backend"

SOURCE_FILES=(
    main.py worker.py rag_pipeline.py
    retriever.py indexer.py document_loader.py
    pii_filter.py logger.py models.py
    config.py requirements.txt
)

for f in "${SOURCE_FILES[@]}"; do
    if [ -f "$f" ]; then
        cp "$f" "$BUNDLE_DIR/backend/"
    else
        echo "  WARNING: $f not found"
    fi
done

# copy BGE reranker
cp -r models/ "$BUNDLE_DIR/backend/models/"

# create .env
cat > "$BUNDLE_DIR/backend/.env" << 'EOF'
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
EMBEDDING_MODEL=mxbai-embed-large
RERANKER_PATH=./models/bge-reranker-base
LOG_LEVEL=INFO
MAX_CONCURRENT_REQUESTS=3
TOKEN_BUDGET=8192
TEMPERATURE=0.1
RERANK_THRESHOLD=0.3
PII_REDACTION=true
CONTENT_HASHING=true
HYBRID_SEARCH=true
RERANKING=true
EOF

echo "Backend source copied ✓"
echo "  BGE reranker: $(du -sh "$BUNDLE_DIR/backend/models/bge-reranker-base" | cut -f1)"

# ── 7. create start / stop / install scripts ──────────
echo ""
echo "[7/7] Creating scripts..."

# ── install-on-vm.sh ──────────────────────────────────
cat > "$BUNDLE_DIR/install-on-vm.sh" << 'INSTALLEOF'
#!/bin/bash
# install-on-vm.sh
# Run on RHEL9 VM to install all dependencies
set -e

BUNDLE_DIR=$(cd "$(dirname "$0")" && pwd)

echo "=================================================="
echo " RAG App — Install Dependencies on RHEL9 VM"
echo "=================================================="

# ── 1. install Python 3.11 ────────────────────────────
echo ""
echo "[1/4] Installing Python 3.11..."

if python3.11 --version >/dev/null 2>&1; then
    echo "Python 3.11 already installed ✓ ($(python3.11 --version))"
else
    if ls "$BUNDLE_DIR/python/"*.rpm >/dev/null 2>&1; then
        sudo dnf install --disablerepo='*' \
            "$BUNDLE_DIR/python/"*.rpm \
            -y 2>/dev/null || \
        sudo dnf install --disablerepo='*' \
            --allowerasing \
            "$BUNDLE_DIR/python/"*.rpm -y

        sudo alternatives --install \
            /usr/bin/python3 python3 \
            /usr/bin/python3.11 1 2>/dev/null || true
    else
        echo "WARNING: Python RPMs not in bundle"
        echo "Using system Python: $(python3 --version)"
    fi

    python3 --version && echo "Python installed ✓" || {
        echo "ERROR: Python not available"
        exit 1
    }
fi

# ── 2. install Node.js from pre-built binary ──────────
echo ""
echo "[2/4] Installing Node.js from pre-built binary..."

if node --version 2>/dev/null | grep -q "^v20"; then
    echo "Node.js 20 already installed ✓ ($(node --version))"
else
    NODE_TARBALL=$(find "$BUNDLE_DIR/node" \
        -name "node-v*-linux-x64.tar.xz" | head -1)

    if [ -z "$NODE_TARBALL" ]; then
        echo "ERROR: Node.js tarball not found in bundle/node/"
        exit 1
    fi

    echo "Installing $(basename "$NODE_TARBALL")..."
    sudo tar xf "$NODE_TARBALL" \
        -C /usr/local \
        --strip-components=1

    # verify
    node --version && echo "Node.js installed ✓ ($(node --version))" || {
        # fallback — add to PATH
        echo 'export PATH=/usr/local/bin:$PATH' >> ~/.bashrc
        source ~/.bashrc
        node --version && echo "Node.js installed ✓" || {
            echo "ERROR: Node.js installation failed"
            exit 1
        }
    }

    npm --version && echo "npm installed ✓ ($(npm --version))"
fi

# ── 3. install Ollama ─────────────────────────────────
echo ""
echo "[3/4] Installing Ollama..."

if command -v ollama >/dev/null 2>&1; then
    echo "Ollama already installed ✓ ($(ollama --version))"
else
    if [ ! -f "$BUNDLE_DIR/ollama/ollama-linux-amd64.tar.gz" ]; then
        echo "ERROR: ollama-linux-amd64.tar.gz not found in bundle"
        exit 1
    fi

    echo "Extracting Ollama to /usr (official method)..."
    sudo tar x \
        -C /usr \
        -f "$BUNDLE_DIR/ollama/ollama-linux-amd64.tar.gz"

    ollama --version && echo "Ollama installed ✓" || {
        echo "ERROR: Ollama installation failed"
        exit 1
    }
fi

# copy model files
echo "Copying Ollama models to ~/.ollama/..."
mkdir -p ~/.ollama
cp -r "$BUNDLE_DIR/ollama/models" ~/.ollama/
echo "Models copied ✓"

# install as system service
sudo tee /etc/systemd/system/ollama.service > /dev/null << EOF
[Unit]
Description=Ollama LLM Server
After=network.target

[Service]
Type=simple
User=$USER
Environment=HOME=$HOME
Environment=OLLAMA_MODELS=$HOME/.ollama/models
ExecStart=/usr/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ollama
echo "Ollama service installed and started ✓"

# wait and verify
sleep 5
echo "Verifying models..."
ollama list

# ── 4. verify Python venv ─────────────────────────────
echo ""
echo "[4/4] Verifying Python virtual environment..."

source "$BUNDLE_DIR/backend/venv/bin/activate"
python3 -c "
packages = [
    'fastapi', 'langchain', 'langchain_ollama',
    'faiss', 'sentence_transformers',
    'rank_bm25', 'pypdf', 'spacy'
]
for p in packages:
    try:
        __import__(p)
        print(f'  {p:<25} ✓')
    except ImportError:
        print(f'  {p:<25} ✗  MISSING')
"
deactivate

# make scripts executable
chmod +x "$BUNDLE_DIR/start.sh"
chmod +x "$BUNDLE_DIR/stop.sh"

echo ""
echo "=================================================="
echo " Installation complete!"
echo ""
echo " Start the app:"
echo "   cd $BUNDLE_DIR"
echo "   ./start.sh"
echo ""
echo " Or run manually for demo:"
echo "   Terminal 1:  cd backend && source venv/bin/activate && python3 main.py"
echo "   Terminal 2:  cd frontend && npm run dev"
echo ""
echo " Then open Firefox: http://localhost:5173"
echo "=================================================="
INSTALLEOF

# ── start.sh ──────────────────────────────────────────
cat > "$BUNDLE_DIR/start.sh" << 'STARTEOF'
#!/bin/bash
# start.sh — start Ollama + backend + frontend
set -e

BUNDLE_DIR=$(cd "$(dirname "$0")" && pwd)
LOG_DIR="$BUNDLE_DIR/logs"

mkdir -p "$LOG_DIR"
mkdir -p "$BUNDLE_DIR/backend/logs"
mkdir -p "$BUNDLE_DIR/backend/faiss_index"

echo "=================================================="
echo " RAG App — Starting"
echo "=================================================="

# ── 1. Ollama ──────────────────────────────────────────
echo ""
echo "[1/3] Starting Ollama..."

if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama already running ✓"
else
    sudo systemctl start ollama 2>/dev/null || {
        export OLLAMA_MODELS="$HOME/.ollama/models"
        nohup ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        echo $! > "$BUNDLE_DIR/ollama.pid"
    }

    for i in $(seq 1 20); do
        if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "Ollama ready ✓"
            break
        fi
        if [ $i -eq 20 ]; then
            echo "ERROR: Ollama did not start"
            echo "Check: sudo systemctl status ollama"
            exit 1
        fi
        printf "  waiting... (%ds)\r" $((i * 3))
        sleep 3
    done
fi

echo "Models available:"
ollama list

# ── 2. backend ────────────────────────────────────────
echo ""
echo "[2/3] Starting backend..."

cd "$BUNDLE_DIR/backend"
source venv/bin/activate

nohup python3 main.py \
    > "$BUNDLE_DIR/backend/logs/backend.log" 2>&1 &
echo $! > "$BUNDLE_DIR/backend.pid"

for i in $(seq 1 24); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend ready ✓"
        break
    fi
    if [ $i -eq 24 ]; then
        echo "ERROR: Backend did not start"
        echo "Check: tail -f $BUNDLE_DIR/backend/logs/backend.log"
        deactivate
        exit 1
    fi
    printf "  waiting... (%ds)\r" $((i * 5))
    sleep 5
done

deactivate

# ── 3. frontend ───────────────────────────────────────
echo ""
echo "[3/3] Starting frontend (npm run dev)..."

cd "$BUNDLE_DIR/frontend"

nohup npm run dev -- --host \
    > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$BUNDLE_DIR/frontend.pid"

sleep 4

if kill -0 "$(cat "$BUNDLE_DIR/frontend.pid")" 2>/dev/null; then
    echo "Frontend ready ✓"
else
    echo "ERROR: Frontend did not start"
    echo "Check: tail -f $LOG_DIR/frontend.log"
    exit 1
fi

echo ""
echo "=================================================="
echo " RAG App is running!"
echo ""
echo "  Open in Firefox:  http://localhost:5173"
echo "  Backend health:   http://localhost:8000/health"
echo "  Ollama models:    http://localhost:11434/api/tags"
echo ""
echo "  Logs:"
echo "    Backend:   tail -f $BUNDLE_DIR/backend/logs/backend.log"
echo "    Frontend:  tail -f $LOG_DIR/frontend.log"
echo "    Ollama:    tail -f $LOG_DIR/ollama.log"
echo ""
echo "  Stop:  ./stop.sh"
echo "=================================================="
STARTEOF

# ── stop.sh ───────────────────────────────────────────
cat > "$BUNDLE_DIR/stop.sh" << 'STOPEOF'
#!/bin/bash
# stop.sh — stop backend and frontend (Ollama keeps running)

BUNDLE_DIR=$(cd "$(dirname "$0")" && pwd)

echo "Stopping RAG App..."
echo ""

stop_pid() {
    local name="$1"
    local pidfile="$2"
    if [ -f "$pidfile" ]; then
        PID=$(cat "$pidfile")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            sleep 1
            kill -0 "$PID" 2>/dev/null && kill -9 "$PID" 2>/dev/null || true
            echo "  $name stopped ✓"
        else
            echo "  $name was not running"
        fi
        rm -f "$pidfile"
    else
        echo "  $name pid file not found"
    fi
}

stop_pid "Frontend" "$BUNDLE_DIR/frontend.pid"
stop_pid "Backend"  "$BUNDLE_DIR/backend.pid"

# Ollama runs as system service — leave it running
echo "  Ollama left running (systemd service)"
echo "  To stop Ollama: sudo systemctl stop ollama"
echo ""
echo "Done. To restart: ./start.sh"
STOPEOF

chmod +x \
    "$BUNDLE_DIR/install-on-vm.sh" \
    "$BUNDLE_DIR/start.sh" \
    "$BUNDLE_DIR/stop.sh"

echo "Scripts created ✓"

# ── package ────────────────────────────────────────────
echo ""
echo "Packaging bundle..."

cd "$PROJECT_ROOT/deploy/bundle"
tar czf rag-app-bundle.tar.gz rag-app-bundle/
sha256sum rag-app-bundle.tar.gz > rag-app-bundle.tar.gz.sha256

echo ""
echo "=================================================="
echo " Build complete!"
echo ""
echo " Bundle:     deploy/bundle/rag-app-bundle.tar.gz"
echo " Checksum:   deploy/bundle/rag-app-bundle.tar.gz.sha256"
echo " Size:       $(du -sh rag-app-bundle.tar.gz | cut -f1)"
echo ""
echo " Contents:"
echo "   node/           $(du -sh "$BUNDLE_DIR/node"                   | cut -f1)   Node.js binary tarball"
echo "   python/         $(du -sh "$BUNDLE_DIR/python"                 | cut -f1)   Python RPMs"
echo "   ollama/         $(du -sh "$BUNDLE_DIR/ollama"                 | cut -f1)   Ollama + models"
echo "   backend/venv/   $(du -sh "$BUNDLE_DIR/backend/venv"           | cut -f1)   Python packages"
echo "   backend/models/ $(du -sh "$BUNDLE_DIR/backend/models"         | cut -f1)   BGE reranker"
echo "   frontend/       $(du -sh "$BUNDLE_DIR/frontend/node_modules"  | cut -f1)   node_modules"
echo ""
echo " Transfer to VM:"
echo "   cp deploy/bundle/rag-app-bundle.tar.gz /media/usb/"
echo "   cp deploy/bundle/rag-app-bundle.tar.gz.sha256 /media/usb/"
echo "=================================================="