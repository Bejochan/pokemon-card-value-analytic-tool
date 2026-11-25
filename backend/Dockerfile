# =====================================================================
# DOCKERFILE BACKEND REGOKEMON
# Server: FastAPI + PyTorch CPU + Ultralytics YOLO26s + Chronos Forecaster
# =====================================================================

FROM python:3.11-slim

# Mencegah penulisan berkas .pyc, memastikan log tampil langsung, dan menentukan lokasi cache model
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HF_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch \
    XDG_CACHE_HOME=/app/.cache \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

# Instal dependensi sistem Linux yang dibutuhkan oleh OpenCV dan runtime PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Salin berkas dependensi terlebih dahulu agar memanfaatkan cache layer Docker
COPY requirements.txt .

# Instal PyTorch versi CPU lalu seluruh dependensi backend (extra-index mencegah unduhan wheel CUDA)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Unduh bobot CLIP ViT-B/32 (Model 1) dan Amazon Chronos-Bolt Mini (Model 3) ke cache image
# agar image mandiri dapat berjalan secara offline tanpa mengunduh model saat startup
RUN HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python -c "import torch, open_clip; from chronos import ChronosBoltPipeline; open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai', device='cpu'); ChronosBoltPipeline.from_pretrained('amazon/chronos-bolt-mini', device_map='cpu', dtype=torch.float32)"

# Aktifkan mode offline HuggingFace/Transformers untuk runtime container
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Salin seluruh kode dan artefak runtime backend ke dalam container
COPY . /app

# Port FastAPI
EXPOSE 8000

# Healthcheck otomatis untuk orkestrator (Docker Compose / Swarm / Kubernetes / Cloud Run)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Jalankan server FastAPI via Uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

