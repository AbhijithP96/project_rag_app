# RAG App — Airgap Deployment Guide

## Overview

This guide covers the complete process for deploying the RAG app
on an airgapped RHEL9 VM with no internet access.

**Section 1** — Internet machine: download and package everything  
**Section 2** — RHEL9 VM: install dependencies and run the app

### What gets bundled

| Component | Size | Description |
|-----------|------|-------------|
| Node.js binary | ~30 MB | Pre-built Node.js 20 tarball |
| Python 3.11 RPMs | ~50 MB | Python + build tools |
| Ollama tarball | ~50 MB | Ollama server binary |
| llama3.2:3b | ~2.0 GB | LLM for generation |
| mxbai-embed-large | ~670 MB | Embedding model |
| Python venv | ~3.0 GB | All pip packages installed |
| BGE reranker | ~1.1 GB | Reranker model weights |
| node_modules | ~300 MB | Frontend npm dependencies |
| Frontend source | ~5 MB | React source + config files |
| Backend source | ~1 MB | Python source files |
| **Total** | **~7–8 GB** | |

---

## Usage:

Clone the repositiory
```bash
git clone https://github.com/AbhijithP96/project_rag_app.git
cd project_rag_app
```

## Section 1 — Internet Machine

### 1.1 Prerequisites
```bash
# verify these are installed on the internet machine
python3 --version    # 3.11+
node --version       # any version — just for building
npm --version
curl --version

# install HuggingFace CLI for BGE reranker download
pip install huggingface_hub
```

### 1.2 Download BGE reranker model

Must be done before running the build script:
```bash
cd rag-backend/

hf download BAAI/bge-reranker-base \
    --local-dir models/bge-reranker-base 
```

### 1.3 Download Node.js pre-built binary

Go to the official Node.js download page and download the
Linux x64 pre-built binary tarball:
```
https://nodejs.org/en/download
```

Select:
- Version: **20 LTS** (recommended)
- OS: **Linux**
- Architecture: **x64**
- Package: **Prebuilt Binaries** → `.tar.xz`

simply download from the browser at `nodejs.org/en/download`
and move to `deploy/bundle-prep/`.

### 1.4 Download Python 3.11 RPMs for RHEL9
```bash
# install dnf-plugins if not present (run on RHEL/Fedora machine)
# if on Ubuntu/Debian — skip this, copy RPMs from a RHEL machine
sudo dnf install -y dnf-plugins-core 2>/dev/null || true

mkdir -p deploy/bundle-prep/python-rpms

dnf download --resolve \
    --destdir="deploy/bundle-prep/python-rpms" \
    python3.11 \
    python3.11-pip \
    python3.11-devel \
    python3.11-setuptools \
    python3.11-wheel \
    gcc \
    gcc-c++ \
    make \
    libffi-devel \
    openssl-devel 2>/dev/null || \
dnf download --resolve \
    --destdir="deploy/bundle-prep/python-rpms" \
    python3 python3-pip python3-devel gcc gcc-c++ make

echo "RPMs downloaded: $(ls deploy/bundle-prep/python-rpms | wc -l) packages"
```

> **If your internet machine is not RHEL/Fedora:**
> Run the `dnf download` commands on any RHEL9 machine
> (even another VM with internet) and copy the RPM files.
> Alternatively, RHEL9 DVD ISO contains Python 3.9 which
> also works — see note in Section 2.3.

### 1.5 Download Ollama and pull models

Download Ollama from [here](https://docs.ollama.com/linux)
```bash
curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | sudo tar x -C /usr
```

Then Pull Ollama models

```bash
ollama pull llama3.2:3b

ollama pull mxbai-embed-large:latest 
```

### 1.6 Run the build script
```bash
chmod +x deploy/scripts/build-bundle.sh
./deploy/scripts/build-bundle.sh
```

The build script will:
1. Copy pre-downloaded Node.js tarball into bundle
2. Copy pre-downloaded Python RPMs into bundle
3. Copy pre-pulled Ollama + models into bundle
4. Install frontend dependencies (`npm ci`)
5. Copy `node_modules/` and frontend source into bundle
6. Create Python virtual environment with all packages
7. Copy backend source + BGE reranker model
8. Create `start.sh` and `stop.sh` scripts
9. Package everything into `rag-app-bundle.tar.gz`

**Expected duration:** 15–25 minutes (mostly pip install)

### 1.7 Transfer bundle to VM
```bash
# verify bundle was created
ls -lh deploy/bundle/rag-app-bundle.tar.gz

# generate checksum
sha256sum deploy/bundle/rag-app-bundle.tar.gz \
    > deploy/bundle/rag-app-bundle.tar.gz.sha256

# transfer via USB (recommended for airgap)
cp deploy/bundle/rag-app-bundle.tar.gz          /media/usb/
cp deploy/bundle/rag-app-bundle.tar.gz.sha256   /media/usb/

# or via SCP if network available during initial setup
scp deploy/bundle/rag-app-bundle.tar.gz \
    user@rhel9-vm:~/
```

---

## Section 2 — RHEL9 VM (no internet)

### 2.1 Verify bundle integrity
```bash
# copy from USB if needed
cp /media/usb/rag-app-bundle.tar.gz ~/
cp /media/usb/rag-app-bundle.tar.gz.sha256 ~/

# verify checksum
sha256sum -c rag-app-bundle.tar.gz.sha256
# expected: rag-app-bundle.tar.gz: OK

# check size
du -sh rag-app-bundle.tar.gz
# expected: 7-8 GB
```

### 2.2 Extract the bundle
```bash
# extract (takes a few minutes)
tar xzf rag-app-bundle.tar.gz

cd rag-app-bundle/

# verify structure
ls
# python/  node/  ollama/  backend/  frontend/
# install-on-vm.sh  start.sh  stop.sh
```

### 2.3 Install Python 3.11
```bash
# install from bundled RPMs — no internet needed
sudo dnf install --disablerepo='*' \
    python/*.rpm \
    -y

# verify
python3.11 --version
# expected: Python 3.11.x

# set as default python3
sudo alternatives --install \
    /usr/bin/python3 python3 \
    /usr/bin/python3.11 1

python3 --version
# expected: Python 3.11.x
```

> **Note:** If RPM install fails due to dependency conflicts try:
> ```bash
> sudo dnf install --disablerepo='*' \
>     --allowerasing \
>     python/*.rpm -y
> ```
>
> RHEL9 ships Python 3.9 by default. If Python 3.11 RPMs are
> not in the bundle, Python 3.9 will work — the venv was built
> on the same Python version as your internet machine, so make
> sure to match versions.

### 2.4 Install Node.js from pre-built binary

The bundle contains a pre-built Node.js tarball from nodejs.org.
No RPMs, no package manager — just extract and add to PATH.
```bash
# check what Node.js tarball is in the bundle
ls node/
# node-v20.18.0-linux-x64.tar.xz

# extract to /usr/local
sudo tar xf node/node-v*.tar.xz \
    -C /usr/local \
    --strip-components=1

# verify
node --version
# expected: v20.x.x

npm --version
# expected: 10.x.x

# if node/npm not found — add to PATH manually
echo 'export PATH=/usr/local/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

node --version
```

### 2.5 Install Ollama
```bash
# install using official method — extract tarball to /usr
sudo tar x \
    -C /usr \
    -f ollama/ollama-linux-amd64.tar.gz

# verify
ollama --version
```

### 2.6 Copy Ollama model files
```bash
# create ollama model directory
mkdir -p ~/.ollama

# copy pre-pulled models from bundle (~2.7 GB)
echo "Copying models (this takes a moment)..."
cp -r ollama/models ~/.ollama/

# verify model files are present
echo "Model blobs:"
ls ~/.ollama/models/blobs/ | head -5

echo "Model manifests:"
ls ~/.ollama/models/manifests/registry.ollama.ai/library/
# expected: llama3.2  mxbai-embed-large
```

### 2.7 Start Ollama and verify models
```bash
# install as system service so it starts on boot
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

# wait for it to start
sleep 5

# verify models are available
ollama list
# expected:
# NAME                       SIZE
# llama3.2:3b                2.0 GB
# mxbai-embed-large:latest   669 MB

# quick test — generation
echo "Testing LLM..."
ollama run llama3.2:3b "say hello in exactly one word" --nowordwrap
# expected: Hello

# test embeddings
echo "Testing embeddings..."
curl -s http://localhost:11434/api/embeddings \
    -d '{"model":"mxbai-embed-large","prompt":"test"}' | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
dims = len(d.get('embedding', []))
print(f'Embedding dimensions: {dims}')
assert dims > 0, 'ERROR: empty embedding'
print('Embeddings working ✓')
"
```

### 2.8 Verify Python virtual environment

The venv is pre-built — no pip install needed:
```bash
source backend/venv/bin/activate

python3 -c "import fastapi"               && echo "fastapi              ✓"
python3 -c "import langchain"             && echo "langchain            ✓"
python3 -c "import langchain_ollama"      && echo "langchain_ollama     ✓"
python3 -c "import faiss"                 && echo "faiss                ✓"
python3 -c "import sentence_transformers" && echo "sentence_transformers ✓"
python3 -c "import rank_bm25"             && echo "rank_bm25            ✓"
python3 -c "import pypdf"                 && echo "pypdf                ✓"
python3 -c "import spacy"                 && echo "spacy                ✓"

deactivate
```

### 2.9 Verify frontend node_modules
```bash
# node_modules is pre-installed — no npm install needed
ls frontend/node_modules/ | wc -l
# expected: 300+ packages

# verify vite is available
ls frontend/node_modules/.bin/vite
# expected: frontend/node_modules/.bin/vite
```

### 2.10 Start the backend
```bash
cd backend/
source venv/bin/activate

# start FastAPI backend
python3 main.py
```

Expected output:
```
15:00:01 | INFO | system | worker starting up...
15:00:03 | INFO | system | reranker warmed up
15:00:04 | INFO | system | LLM warmed up
15:00:04 | INFO | system | worker ready
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify in another terminal:
```bash
curl http://localhost:8000/health | python3 -m json.tool
# expected:
# {
#   "status": "ready",
#   "index_ready": false,
#   "active_jobs": 0,
#   "memory_percent": 49.0,
#   ...
# }
```

### 2.11 Start the frontend with npm run dev

Open a new terminal and run:
```bash
cd frontend/

# start Vite dev server
# node_modules is already present — no npm install needed
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### 2.12 Open the app in Firefox
```
http://localhost:5173
```

You should see the AskDocs widget with the dark terminal interface.

---

## Using the app

### Index documents

1. Click **index manager** to expand the panel
2. Click **browse & select folder**
3. Navigate to a folder containing your documents
4. Click **index** next to the folder or **index this folder**

Supported file types: `.pdf` `.md` `.txt` `.xlsx` `.html`

The index persists between restarts — unchanged files are
automatically skipped on re-index.

### Ask questions

Type a question in the input bar and press Enter or click ↑

The pipeline:
```
query → PII redaction → hybrid search (FAISS + BM25)
      → BGE reranker → LLM generation → SSE streaming
```

### Features visible in the demo

- **Citations** — hover `[1]` `[2]` badges to see source chunks
- **Context inspector** — right panel shows retrieved chunks + scores
- **Token budget** — progress bar above input shows token usage
- **Pipeline log** — click `▴ log` in status bar to see events
- **Theme toggle** — `◑` button switches dark/light mode
- **Error handling** — type `__err_retrieval__` to trigger error demo

---

