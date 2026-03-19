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
# python must be installed
python3 --version

# Docker must be installed
docker --version
docker compose version

# verify you can run docker without sudo
docker ps
```

### 1.2 Download BGE reranker model
```bash
cd backend/

mkdir -p models/

pip install -U huggingface_hub

hf download BAAI/bge-reranker-base \
    --local-dir models/bge-reranker-base

# verify
du -sh models/bge-reranker-base/
# ~1.1 GB

cd ..
```

If download fails, create a HF token for your huggging_face account and run `hf auth login` to set up credentials and run the above command to download the cross-enocder model.

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

Most OS does not ship with docker.
You need to install it from offline packages.

Docker must be installed on the VM before loading images.
Since the VM has no internet access, follow the **offline / manual
installation** method from the official Docker docs.

**Official Docker installation guide:**
```
https://docs.docker.com/engine/install/
```

Select your OS from the list and go to section install from package / offline installation
Download the offline packge on the internet machine and transfer it to VM and then follow the rest of the instruction to install docker on empty VM.

```

### 2.3 Extract the bundle
```bash
tar -xf rag-app-docker.tar.gz
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
cd ..
./dist/load-and-run.sh
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

Create a `.env` file inside deploy folder.

The backend container can access your host filesystem
through the volume mount defined in `.env`:
```env
# .env — default mounts your home directory
HOST_DOCS_PATH=~

# or restrict to a specific folder
HOST_DOCS_PATH=/home/user/documents
```

Inside the container your host path is available at `/home`.

**Example:** if your documents are at `/home/user/docs/`
then inside the widget use the path:
```
/home/docs
```

**To change the mounted folder:**
```bash
# edit .env
nano .env
# change HOST_DOCS_PATH=/home/user/your-folder

# restart backend to apply
docker compose restart rag-backend
```
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

## Docker volumes

| Volume | Contents | Persists |
|--------|----------|---------|
| ollama_models | LLM + embedding model weights | ✅ |
| faiss_index | Document index (FAISS + BM25) | ✅ |
| bge_reranker | BGE reranker weights | ✅ |
| backend_logs | Application logs | ✅ |

All volumes survive `docker compose down`.
Only `docker compose down -v` removes them.