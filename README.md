# RAG App — Airgap Docker Deployment Guide

## Overview

This guide deploys the RAG app on an airgapped RHEL9 VM
using Docker and Docker Compose. No internet required on the VM.

**Section 1** — Internet machine: build images and create bundle  
**Section 2** — VM: install Docker offline and run the app

## Usage

Clone the repository:
```bash
git clone https://github.com/AbhijithP96/project_rag_app.git
cd project_rag_app
```

---

## Section 1 — Internet Machine

### 1.1 Prerequisites
```bash
# Docker must be installed
docker --version
docker compose version

# verify you can run docker without sudo
docker ps
```

### 1.2 Download BGE reranker model
```bash
cd rag-backend/

pip install -U huggingface_hub

hf download BAAI/bge-reranker-base \
    --local-dir models/bge-reranker-base

# verify
du -sh models/bge-reranker-base/
# ~1.1 GB

cd ..
```

### 1.3 Build images and pull models
```bash
chmod +x deploy/scripts/build-and-save.sh
./deploy/scripts/build-and-save.sh
```

This script:
1. Builds `rag-backend:latest` Docker image
2. Builds `rag-frontend:latest` Docker image
3. Pulls `ollama/ollama:latest` Docker image
4. Starts a temporary Ollama container and pulls:
   - `llama3.2:3b` (~2.0 GB)
   - `mxbai-embed-large` (~669 MB)
5. Saves all three images as `.tar` files
6. Exports the Ollama models volume as `ollama-models.tar.gz`
7. Packages everything into `deploy/rag-app-docker.tar.gz`

**Expected duration:** 20–40 minutes

### 1.4 Transfer bundle to VM
```bash
# verify bundle was created
ls -lh deploy/rag-app-docker.tar.gz

# generate checksum
sha256sum deploy/rag-app-docker.tar.gz \
    > deploy/rag-app-docker.tar.gz.sha256

# transfer via USB
cp deploy/rag-app-docker.tar.gz        /media/usb/
cp deploy/rag-app-docker.tar.gz.sha256 /media/usb/

# or via SCP
scp deploy/rag-app-docker.tar.gz user@rhel9-vm:~/
```

---

## Section 2 — VM (no internet)

### 2.1 Verify bundle integrity
```bash
cp /media/usb/rag-app-docker.tar.gz ~/
cp /media/usb/rag-app-docker.tar.gz.sha256 ~/

sha256sum -c rag-app-docker.tar.gz.sha256
# expected: rag-app-docker.tar.gz: OK
```

### 2.2 Install Docker offline

RHEL9 does not ship Docker by default.
You need to install it from offline RPMs.

**On the internet machine — download Docker RPMs:**
```bash
# run this on internet machine before building bundle
# requires a RHEL/Fedora machine or container

mkdir -p deploy/dist/docker-rpms

# add Docker repo
sudo dnf config-manager \
    --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# download RPMs without installing
dnf download --resolve \
    --destdir=deploy/dist/docker-rpms \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

echo "Docker RPMs: $(ls deploy/dist/docker-rpms | wc -l) packages"
```

> **If internet machine is Ubuntu:**
> Use a RHEL9 container to download RPMs:
> ```bash
> docker run --rm \
>     -v $(pwd)/deploy/dist/docker-rpms:/rpms \
>     redhat/ubi9 \
>     bash -c "
>         dnf install -y dnf-plugins-core &&
>         dnf config-manager --add-repo \
>             https://download.docker.com/linux/rhel/docker-ce.repo &&
>         dnf download --resolve --destdir=/rpms \
>             docker-ce docker-ce-cli containerd.io \
>             docker-buildx-plugin docker-compose-plugin
>     "
> ```

**On the RHEL9 VM — install from RPMs:**
```bash
# extract bundle first
tar xzf rag-app-docker.tar.gz
cd dist/

# install Docker from offline RPMs
sudo dnf install --disablerepo='*' \
    docker-rpms/*.rpm \
    -y

# start and enable Docker service
sudo systemctl enable --now docker

# add your user to docker group (avoids sudo for docker commands)
sudo usermod -aG docker $USER

# apply group change without logout
newgrp docker

# verify
docker --version
docker compose version
```

### 2.3 Extract the bundle
```bash
# go into extracted dist directory
cd ~/dist/

ls
# rag-backend.tar  rag-frontend.tar  ollama.tar
# ollama-models.tar.gz  docker-compose.yml  .env
# load-and-run.sh  sha256sums.txt
```

### 2.4 Run the setup script
```bash
chmod +x load-and-run.sh
./load-and-run.sh
```

What the script does step by step:

**Step 1 — Load Docker images**
```
docker load -i rag-backend.tar      → rag-backend:latest
docker load -i rag-frontend.tar     → rag-frontend:latest
docker load -i ollama.tar           → ollama/ollama:latest
```

**Step 2 — Restore Ollama models**
```
Creates Docker volume: ollama_models
Extracts ollama-models.tar.gz into the volume
Models are available inside the ollama container
```

**Step 3 — Configure host filesystem**
```
Expands ~ in .env to your actual home directory
Your home folder is mounted read-only at /host/home
inside the backend container
```

**Step 4 — Start services**
```
docker compose up -d
Waits for Ollama health check
Waits for backend health check
```

### 2.5 Open the app

Open Firefox:
```
http://localhost:3000
```

---

## Indexing documents

The backend container can access your host filesystem
through the volume mount defined in `.env`:
```env
# .env — default mounts your home directory
HOST_DOCS_PATH=~

# or restrict to a specific folder
HOST_DOCS_PATH=/home/user/documents
```

Inside the container your host path is available at `/host/home`.

**Example:** if your documents are at `/home/user/thesis/docs/`
then inside the widget use the path:
```
/host/home/thesis/docs
```

**To change the mounted folder:**
```bash
# edit .env
nano .env
# change HOST_DOCS_PATH=/home/user/your-folder

# restart backend to apply
docker compose restart rag-backend
```

**To upload files directly** (alternative to path browsing):

The backend exposes an `/upload` endpoint. Use the widget's
file picker — files are uploaded into `/app/uploads/` inside
the container and can then be indexed.

---

## Useful commands

### Check service status
```bash
# all services
docker compose ps

# health endpoints
curl http://localhost:8000/health  | python3 -m json.tool
curl http://localhost:11434/api/tags | python3 -m json.tool
```

### View logs
```bash
# all services
docker compose logs -f

# individual services
docker compose logs -f rag-backend
docker compose logs -f rag-frontend
docker compose logs -f ollama
```

### Restart a service
```bash
docker compose restart rag-backend
docker compose restart rag-frontend
docker compose restart ollama
```

### Stop the app
```bash
# stop containers (keep data volumes)
docker compose down

# stop and remove all data (full reset)
docker compose down -v
```

---

## Troubleshooting

### Docker daemon not starting
```bash
sudo systemctl status docker
sudo journalctl -u docker -n 50

# common fix on RHEL9
sudo systemctl enable --now docker
```

### Images not loading
```bash
# verify tar files are not corrupted
sha256sum -c sha256sums.txt

# try loading individually
docker load -i rag-backend.tar
docker load -i rag-frontend.tar
docker load -i ollama.tar

# verify images loaded
docker images
```

### Ollama models missing after restore
```bash
# check volume exists
docker volume ls | grep ollama

# check contents
docker run --rm \
    -v ollama_models:/data \
    alpine ls /data

# re-restore
docker run --rm \
    -v ollama_models:/data \
    -v $(pwd):/backup \
    alpine tar xzf /backup/ollama-models.tar.gz -C /data

# restart ollama
docker compose restart ollama
sleep 10
docker exec rag-ollama ollama list
```

### Backend cannot see host files
```bash
# check .env
cat .env
# HOST_DOCS_PATH should be an absolute path

# verify mount is working
docker exec rag-backend ls /host/home

# update .env and restart
echo "HOST_DOCS_PATH=/home/$(whoami)" > .env
docker compose restart rag-backend
```

### GPU not detected
```bash
# check nvidia runtime
docker info | grep -i runtime

# test GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# if nvidia runtime not installed
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Port already in use
```bash
sudo ss -tlnp | grep -E "3000|8000|11434"
sudo fuser -k 3000/tcp
sudo fuser -k 8000/tcp
```

### Full reset
```bash
docker compose down -v
./load-and-run.sh
```

---

## Architecture
```
Browser (localhost:3000)
         │
         ▼
┌─────────────────────┐
│  rag-frontend       │  nginx serves React SPA
│  port 3000          │  proxies /api/* to backend
└──────────┬──────────┘
           │ /api/*
           ▼
┌─────────────────────┐
│  rag-backend        │  FastAPI
│  port 8000          │  FAISS + BM25 search
│                     │  BGE reranker
│  /host/home ──────────── host filesystem (read-only)
│  /app/faiss_index   │  persisted index
│  /app/models        │  BGE reranker weights
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ollama             │  LLM server
│  port 11434         │  llama3.2:3b
│                     │  mxbai-embed-large
└─────────────────────┘
```

## Docker volumes

| Volume | Contents | Persists |
|--------|----------|---------|
| ollama_models | LLM + embedding model weights | ✅ |
| faiss_index | Document index (FAISS + BM25) | ✅ |
| bge_reranker | BGE reranker weights | ✅ |
| backend_logs | Application logs | ✅ |

All volumes survive `docker compose down`.
Only `docker compose down -v` removes them.