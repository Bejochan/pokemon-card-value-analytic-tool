# Dokumentasi Arsitektur Docker & Panduan Deployment Regokemon

> **Cakupan Dokumen:** Spesifikasi containerization multi-service (`backend/` dan `frontend/`), optimasi *offline cache* model AI, keamanan *build context*, publikasi **Docker Hub**, serta panduan menjalankan sistem secara menyeluruh.  
> **Repositori Docker Hub:**  
> - Backend (`bejochan/regokemon-backend:latest`): `https://hub.docker.com/r/bejochan/regokemon-backend`  
> - Frontend (`bejochan/regokemon-frontend:latest`): `https://hub.docker.com/r/bejochan/regokemon-frontend`

---

## 1. Daftar Isi
1. [Ikhtisar Arsitektur Container Multi-Service](#2-ikhtisar-arsitektur-container-multi-service)
2. [Prasyarat dan Cara Menjalankan Sistem (Dari Nol)](#3-prasyarat-dan-cara-menjalankan-sistem-dari-nol)
3. [Spesifikasi Service Backend (`backend/Dockerfile` & `.dockerignore`)](#4-spesifikasi-service-backend)
4. [Spesifikasi Service Frontend (`frontend/Dockerfile`, `nginx.conf`, `.dockerignore`)](#5-spesifikasi-service-frontend)
5. [Orkestrasi `docker-compose.yml` dan Konfigurasi Runtime](#6-orkestrasi-docker-composeyml-dan-konfigurasi-runtime)
6. [Pemeriksaan Kesehatan Layanan dan Pemecahan Masalah](#7-pemeriksaan-kesehatan-layanan-dan-pemecahan-masalah)

---

## 2. Ikhtisar Arsitektur Container Multi-Service

Seluruh komponen aplikasi Regokemon dikemas menjadi dua *container image* terpisah berplatform `linux/amd64` agar dapat dijalankan pada satu perintah `docker compose up -d` tanpa instalasi manual Python, PyTorch, maupun Node.js di perangkat penguji:

| Service | Nama Container | Image Docker Hub | Port Host -> Container | Fungsi Utama | Ukuran Lokal / Terkompresi Hub |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `backend` | `regokemon-backend` | `bejochan/regokemon-backend:latest` | `8000:8000` | REST API FastAPI (`3.1.0`), OpenCV preprocessing, CLIP + FAISS + ORB, YOLO26s (`800px`), dan Amazon Chronos-Bolt Mini | `4,93 GB` / `~1,35 GB` |
| `frontend` | `regokemon-frontend` | `bejochan/regokemon-frontend:latest` | `5173:80` | Web portal *Single Page Application* (React 19 + Vite) yang disajikan oleh Nginx Alpine | `115 MB` / `~34,9 MB` |

```text
[Browser Pengguna: http://localhost:5173]
          |
          v  (Static HTML/JS/CSS & SPA Fallback via Nginx :80)
[Container: regokemon-frontend (nginx:alpine)]
          |
          v  (HTTP REST API -> http://127.0.0.1:8000)
[Container: regokemon-backend (python:3.11-slim + FastAPI Uvicorn :8000)]
          |
          +--> Cache Offline Model 1 (CLIP ViT-B/32) & Model 3 (Chronos-Bolt Mini)
          +--> Bobot Lokal Model 2 (best-model-v6-card-condition.pt) & FAISS Index
          +--> Dataset Master Lokal (pokemon_cards_dataset_cleaned.csv, 20.617 kartu)
```

---

## 3. Prasyarat dan Cara Menjalankan Sistem (Dari Nol)

### 3.1. Prasyarat Perangkat
1. **Docker Desktop** (atau Docker Engine + Docker Compose v2) terpasang dan berstatus aktif (*Running*).
2. Port **`8000`** dan **`5173`** pada perangkat lokal dalam keadaan kosong (tidak dipakai oleh aplikasi lain).
3. Koneksi internet tersedia pada saat menjalankan sistem **pertama kali** untuk menarik *image* dari Docker Hub (setelah terunduh ke cache lokal, container dapat menyala ulang secara offline).
4. Tidak diperlukan instalasi Python, virtual environment, Node.js, maupun GPU NVIDIA/CUDA.

### 3.2. Cara A: Menjalankan via Repositori GitHub + Docker Hub (Disarankan)
1. Unduh (clone) repositori agar memperoleh berkas orkestrasi `docker-compose.yml`:
   ```powershell
   git clone https://github.com/Bejochan/pokemon-card-value-analytic-tool.git
   cd pokemon-card-value-analytic-tool
   ```
2. Tarik *image* publik dari Docker Hub dan nyalakan kedua layanan di latar belakang:
   ```powershell
   docker compose pull
   docker compose up -d
   ```
   *(Menjalankan `docker compose up -d` langsung tanpa `pull` juga otomatis menarik kedua image dari Docker Hub apabila belum ada di mesin lokal).*
3. Tunggu hingga status `regokemon-backend` menjadi **`healthy`** (kurang lebih 10 sampai 60 detik pada saat inisialisasi awal) lalu periksa status container:
   ```powershell
   docker compose ps
   ```
4. Buka layanan melalui browser:
   - **Aplikasi Web (Frontend):** `http://localhost:5173`
   - **Dokumentasi REST API (Swagger UI):** `http://127.0.0.1:8000/docs`
   - **Endpoint Healthcheck JSON:** `http://127.0.0.1:8000/health`
5. Menghentikan dan membersihkan container saat selesai digunakan:
   ```powershell
   docker compose down
   ```

### 3.3. Cara B: Menjalankan Tanpa `git clone` (Hanya dengan Docker Hub)
Apabila penguji hanya ingin menjalankan *image* langsung dari Docker Hub tanpa mengunduh seluruh kode sumber repositori:
1. Unduh satu berkas `docker-compose.yml` dari repositori ke sebuah folder kerja kosong, lalu jalankan `docker compose up -d` di dalam folder tersebut; **atau**
2. Jalankan masing-masing container secara manual via `docker run`:
   ```powershell
   docker run -d --name regokemon-backend -p 8000:8000 bejochan/regokemon-backend:latest
   docker run -d --name regokemon-frontend -p 5173:80 bejochan/regokemon-frontend:latest
   ```

### 3.4. Cara C: Membangun Ulang *Image* Secara Lokal (Development)
Jika ada perubahan kode di `backend/` atau `frontend/`, bangun ulang *image* dari `Dockerfile` lokal sebelum menyalakan container:
```powershell
docker compose up -d --build
```

---

## 4. Spesifikasi Service Backend

### 4.1. Strategi Build pada `backend/Dockerfile`
1. **Base Image & Dependensi Sistem:** Menggunakan `python:3.11-slim` serta menginstal `libgl1`, `libglib2.0-0`, `libgomp1`, dan `curl` yang dibutuhkan oleh OpenCV (`cv2`), runtime PyTorch/OpenMP, dan perintah *healthcheck*.
2. **Instalasi PyTorch CPU-Only:** Menginstal `torch` dan `torchvision` dari indeks resmi `https://download.pytorch.org/whl/cpu`, serta menambahkan `--extra-index-url https://download.pytorch.org/whl/cpu` saat memasang `requirements.txt`. Hal ini mencegah `pip` mengunduh paket CUDA berukuran bergiga-giga sehingga container dapat berjalan di laptop/server CPU standar.
3. **Pre-Caching Bobot Model untuk Mode Offline:**
   - Variabel lingkungan menetapkan lokasi cache internal di dalam image: `HF_HOME=/app/.cache/huggingface`, `TORCH_HOME=/app/.cache/torch`, `XDG_CACHE_HOME=/app/.cache`, dan `YOLO_CONFIG_DIR=/tmp/Ultralytics`.
   - Sebelum menyalin kode aplikasi, `Dockerfile` menjalankan langkah build dengan `HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0` untuk mengunduh bobot **CLIP ViT-B/32** (`openai`) dan **Amazon Chronos-Bolt Mini** (`amazon/chronos-bolt-mini`) langsung ke layer cache `/app/.cache/huggingface`.
   - Setelah unduhan selesai, variabel diubah menjadi `HF_HUB_OFFLINE=1` dan `TRANSFORMERS_OFFLINE=1` agar saat container dijalankan di mesin mana pun tidak lagi mencoba mengunduh model dari HuggingFace Hub saat startup.
4. **Aset Lokal yang Disertakan ke `/app`:**
   - Kode `backend/app/` dan `backend/models/`
   - Bobot lokal Model 2 YOLO26s (`models/best-model-v6-card-condition.pt`) dan fallback (`models/best-model-v5-card-condition.pt`)
   - Indeks vektor Model 1 (`models/card_embeddings.index` & `models/card_id_map.json`)
   - Dataset master katalog bersih (`dataset/pokemon_cards_dataset_cleaned.csv`, 20.617 kartu) untuk pencarian metadata dan *offline fallback*.

### 4.2. Proteksi Keamanan & Optimasi `backend/.dockerignore`
Untuk menjaga agar kredensial pribadi dan dataset mentah berukuran belasan gigabyte tidak masuk ke *image* Docker Hub, `backend/.dockerignore` mengecualikan:
- **Kredensial sensitif:** `.env` dan `.env.*` (kecuali `.env.example`), sehingga rahasia API atau database tidak pernah tersimpan di dalam layer image publik.
- **Dataset mentah & latihan non-runtime:** `dataset/raw_images/`, `dataset/compressed_images/`, `dataset/card-condition-dataset/`, `dataset/val_samples/`, `dataset/broken_links_report.csv`, `dataset/card_condition_dataset.yaml`, `dataset/pokemon_cards_dataset.json`, `dataset/pokemon_cards_dataset_cleaned.json`, dan `dataset/pokemon_cards_dataset.csv`.
- **Arsip model lama & file kerja sementara:** `models/legacy_mobilenet/`, `wheels/`, `scratch/`, `notebooks/`, `benchmark_realtime_results.json`, `**/__pycache__/`, `Dockerfile`, `.dockerignore`, serta berkas debug (`debug_*.jpg`, `debug_*.png`).
- **Hasil:** Konteks build (`COPY . /app`) menyusut hingga sekitar `86 MB` saat dikemas ke image.

---

## 5. Spesifikasi Service Frontend

### 5.1. Multi-Stage Build pada `frontend/Dockerfile`
1. **Stage 1 (`node:22-alpine AS builder`):**
   - Versi Node 22 Alpine digunakan agar memenuhi syarat minimum mesin **Vite 8 (`v8.2.2`)**.
   - Menyalin `package*.json` dan menjalankan `npm ci` sebelum menyalin source kode untuk memanfaatkan cache layer Docker.
   - Menerima argumen build `ARG VITE_API_BASE_URL=http://127.0.0.1:8000` yang disuntikkan saat `npm run build` menghasilkan bundel statis di `/app/dist`.
2. **Stage 2 (`nginx:alpine`):**
   - Menyalin konfigurasi `nginx.conf` serta isi `/app/dist` ke `/usr/share/nginx/html`.
   - Tidak membawa `node_modules` maupun compiler Node.js ke image produksi sehingga ukuran image hanya `115 MB` (terkompresi di Docker Hub sekitar `34,9 MB`).

### 5.2. Konfigurasi Server Web (`frontend/nginx.conf` & `.dockerignore`)
- **`nginx.conf`:** Mendengarkan port `80`, mengaktifkan kompresi `gzip` (JS/CSS/JSON/SVG), menetapkan `Cache-Control: public, immutable` selama 1 tahun pada folder `/assets/`, dan mengatur *SPA fallback* (`try_files $uri $uri/ /index.html;`) supaya seluruh rute UI tetap terbuka tanpa galat 404.
- **`frontend/.dockerignore`:** Mengecualikan `node_modules/`, `dist/`, `.env`, `.env.*` (kecuali `.env.example`), `.git/`, `Dockerfile`, dan `.dockerignore` (sementara `nginx.conf` tetap disertakan karena disalin ke stage Nginx).

---

## 6. Orkestrasi `docker-compose.yml` dan Konfigurasi Runtime

Pengaturan utama pada berkas [docker-compose.yml](../docker-compose.yml):
1. **Tanpa Bind-Mount Host untuk `models` dan `dataset`:** Volume bind-mount `./backend/models` dan `./backend/dataset` dihapus agar penguji yang menjalankan `docker compose up` dari Docker Hub tidak menimpa bobot model dan CSV di dalam container dengan folder host yang kosong.
2. **Urutan Startup (`depends_on` + `healthcheck`):**
   - Container `backend` memeriksa `curl -f http://localhost:8000/health` setiap 30 detik (`start_period: 60s`).
   - Container `frontend` memakai `condition: service_healthy` agar UI baru aktif setelah API siap menerima permintaan, serta memiliki *healthcheck* internal `wget -qO- http://127.0.0.1:80/`.
3. **Environment & Fallback Tanpa `.env`:**
   - Variabel bawaan di `docker-compose.yml` mengatur `PORT=8000`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `RATE_LIMIT_AI_PER_MINUTE=60`, serta `ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000`.
   - Apabila kredensial Supabase Cloud tidak disuntikkan ke container, modul `offline_service.py` otomatis melayani data katalog, riwayat fallback, dan dasbor pasar dari `pokemon_cards_dataset_cleaned.csv` di dalam container.

---

## 7. Pemeriksaan Kesehatan Layanan dan Pemecahan Masalah

| Perintah / Uji | Tujuan | Output Normal yang Diharapkan |
| :--- | :--- | :--- |
| `docker compose ps` | Melihat status running dan healthcheck kedua container | `regokemon-backend` berstatus `Up ... (healthy)`, `regokemon-frontend` berstatus `Up ... (healthy)` |
| `curl http://127.0.0.1:8000/health` | Verifikasi kesiapan API FastAPI, jumlah dataset, & status model | JSON `"status":"healthy"`, `"version":"3.1.0"`, `"master_cards_count":20617` *(nilai flag `models` menjadi `true` setelah proses warmup latar belakang atau pemanggilan endpoint `/identify`, `/analyze`, atau `/forecast` selesai)* |
| `docker compose logs -f backend` | Memantau log startup warmup CLIP, YOLO26s, dan Chronos-Bolt | Pesan `[OK] [Startup Warmup] Seluruh engine AI (CLIP + YOLO + Chronos) siap melayani inferensi tanpa jeda!` |
| `docker compose down` | Menghentikan container dan menghapus jaringan internal Compose | Kedua container berhenti dan jaringan `proyekpokemon_default` dihapus bersih |

