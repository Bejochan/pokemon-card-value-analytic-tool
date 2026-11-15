# =====================================================================
# DOCKERFILE BACKEND REGOKEMON
# Server: FastAPI + PyTorch CPU + Ultralytics YOLO26s + Chronos Forecaster
# =====================================================================

FROM python:3.11-slim

# Mencegah penulisan berkas .pyc dan memastikan output log langsung tampil di konsol
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PORT=8000

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

# Instal dependensi PyTorch versi CPU untuk efisiensi ukuran container dan stabilitas lintas-platform
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode backend ke dalam container
COPY . /app

# Port FastAPI
EXPOSE 8000

# Healthcheck otomatis untuk orkestrator (Docker Compose / Swarm / Kubernetes / Cloud Run)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Jalankan server FastAPI via Uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

