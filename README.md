# Pokemon Card Value Analytic Tool (REGOKEMON) 🎴📊

> **Dashboard Analitika Data, Dual-Model Computer Vision & Estimasi Harga Wajar Kartu Pokémon untuk Marketplace**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![OpenAI CLIP](https://img.shields.io/badge/Model_1-CLIP_ViT--B%2F32-412991?style=flat&logo=openai&logoColor=white)](https://github.com/mlfoundations/open_clip)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Index-00599C?style=flat&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![YOLOv8](https://img.shields.io/badge/Model_2-YOLOv8_Grader-00FFFF?style=flat&logo=ultralytics&logoColor=black)](https://universe.roboflow.com/group-6-major-project/card-grader)
[![Supabase](https://img.shields.io/badge/Database-Supabase_Cloud-3ECF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![GitHub Actions](https://img.shields.io/badge/Cron_Job-Daily_Price_Tracker-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![API](https://img.shields.io/badge/Data_Source-pokemontcg.io-FFCB05?style=flat&logo=pokemon&logoColor=blue)](https://pokemontcg.io/)

---

## 📌 Ringkasan Proyek

**Pokemon Card Value Analytic Tool (REGOKEMON)** adalah sistem analitika data dan kecerdasan buatan berbasis **Dual-Model Computer Vision** yang dirancang untuk membantu penjual maupun pembeli kartu Pokémon pada **marketplace sekunder** (seperti Tokopedia, Shopee, eBay, atau komunitas kolektor lokal).

Sistem ini memecahkan 3 masalah fundamental dalam ekosistem perdagangan kartu TCG:
1. **Identifikasi Kartu Otomatis Skala Masif (Model 1):** Mengidentifikasi jenis kartu secara instan di antara **20.617 jenis kartu** resmi menggunakan representasi semantik visual **OpenAI CLIP (ViT-B/32)**, pencarian vektor **FAISS**, dan verifikasi mikro **ORB**.
2. **Penilaian Cacat Fisik Otomatis (Model 2):** Mendeteksi kerusakan fisik permukaan kartu (*scratch*, *edge wear*, *corner wear*, *bent/crease*) menggunakan **YOLOv8 Object Detection**.
3. **Valuasi Harga Pasar Wajar & Sinyal Transaksi:** Mengintegrasikan data harga historis dari Supabase Cloud dengan formula depresiasi kondisi untuk menghasilkan rekomendasi **BUY (Murah)**, **HOLD (Wajar)**, atau **SELL (Kemahalan)**.

---

## 🤖 Arsitektur Dual-Model Computer Vision

```mermaid
graph TD
    Input["Input Citra Kartu (Webcam / HP DroidCam / Upload Web)"] --> Preproc["Preprocessing & Geometry<br/>• Warp Rasio 63:88<br/>• 4-Way Auto-Orientation (0°/90°/180°/270°)<br/>• CLAHE Glare & Shadow Reduction"]
    
    Preproc --> M1["MODEL 1: Card Identifier<br/>(OpenAI CLIP ViT-B/32 + FAISS IndexFlatIP)"]
    Preproc --> M2["MODEL 2: Condition Grader<br/>(YOLOv8 Defect Detection via Roboflow API)"]
    
    M1 -->|Top-K Kandidat| ORB["Hybrid Fast ORB Re-Ranking<br/>(Verifikasi Teks, Nomor Seri & Cap Set)"]
    ORB --> Sigmoid["Kalibrasi Keyakinan Sigmoid<br/>(Margin Scaling Temperature tau=0.03)"]
    Sigmoid --> CardID["Identitas Kartu Terverifikasi<br/>(ID, Nama, Set, Seri, Rarity, Harga Dasar)"]
    
    M2 --> ConditionScore["F_condition Multiplier<br/>(Clean: 1.00x, Scratched: 0.85x, Edge: 0.80x, Bent: 0.65x)"]
    
    CardID --> Valuation["ANALYTICS ENGINE & FORMULA VALUASI<br/>P_final = P_base × M_variant × F_condition × F_market"]
    ConditionScore --> Valuation
    
    Supabase[("Supabase Cloud Database<br/>(20.617 Kartu, Set, & Price History)")] --> Valuation
    
    Valuation --> Output["Output Komprehensif:<br/>• Nilai Wajar Realistis (IDR & USD)<br/>• Deviasi Pasar & Sinyal Transaksi (BUY/HOLD/SELL)<br/>• Visual HUD & Grafik Tren Harga"]
```

---

### 1️⃣ Model 1: Card Identification Engine (CLIP ViT-B/32 + FAISS + ORB)

* **Backbone:** Vision Transformer **`openai/clip-vit-base-patch32` (`ViT-B/32`)** pra-latih pada 400 juta pasangan citra-teks.
* **Mengapa Vision Transformer (ViT), Bukan CNN Konvensional?**
  * **Global Self-Attention:** ViT membagi citra menjadi 49 patch ($7 \times 7$ grid berukuran $32 \times 32$ px) dan memproses korelasi visual secara serentak. Model menghubungkan posisi teks nama, simbol energi, dan ilustrasi karakter secara menyeluruh.
  * **Open-Set Metric Learning:** Tidak menggunakan layer klasifikasi *Softmax* yang kaku (20.000 kelas). Kartu baru cukup diekstrak vektor 512-D-nya dan dimasukkan ke indeks FAISS dalam hitungan detik tanpa perlu *retraining* model.
  * **Ketahanan Optik (Robustness):** Sangat tahan terhadap pantulan cahaya (*glare*) dari pelindung plastik (*sleeve*), sudut miring, dan variasi pencahayaan ruangan.
* **Vector Indexing (FAISS IndexFlatIP):**
  * Seluruh 20.617 kartu disimpan dalam format vektor 512 float32 ternormalisasi $L_2$ (`card_embeddings.index`, ukuran RAM hanya ~42 MB).
  * Menghitung *Cosine Similarity* secara paralel dalam waktu sub-milidetik (< 1 ms).
* **Two-Stage Re-Ranking (Fast ORB Keypoints):**
  * Kartu Pokémon memiliki kasus unik berupa **kartu reprint** (artwork karakter sama persis, tetapi beda nomor seri dan simbol set di bagian bawah).
  * Sistem menyaring kandidat teratas melalui FAISS, lalu mengekstrak fitur lokal mikro menggunakan **ORB (500 keypoints)** dengan bobot gabungan:
    $$\text{Score}_{\text{blended}} = 0.60 \times \text{Score}_{\text{CLIP}} + 0.40 \times \text{Score}_{\text{ORB}}$$
* **Kalibrasi Margin Sigmoid:**
  * Menghitung selisih margin skor ke *runner-up* kartu dengan nama berbeda ($\Delta$), lalu diskalakan dengan temperatur $\tau = 0.03$:
    $$P = \frac{100}{1 + e^{-\Delta / \tau}}$$
  * Menghindari *overconfidence* pada varian kartu yang mirip.
* **3 Varian Interface Model 1:**
  1. **`card_identifier_realtime.py` (Live Scanner HUD 30+ FPS):** Menggunakan arsitektur *Multithreaded Asynchronous Worker* (thread rendering kamera dipisah dari thread inferensi AI), *In-Memory ORB Cache*, dan *Temporal Smoothing* (buffer 7-frame konsensus). Latensi: **~83 ms di CPU** dan **~18 ms di GPU RTX 2050**.
  2. **`card_identifier_oncam.py` (Snapshot Camera):** Membuka webcam/IP Cam dengan tombol capture manual dan visualisasi target box.
  3. **`card_identifier_manual.py` (File Evaluasi Presisi):** Evaluasi foto statis melalui File Explorer atau CLI dengan Full 4-Way Auto-Orientation & Dual-View (Portrait + Square).

---

### 2️⃣ Model 2: Card Condition Grader (Defect Detection via YOLOv8)

* **Tujuan:** Mendeteksi dan melokalisasi jenis cacat fisik kartu secara objektif.
* **Metode:** YOLOv8 Object Detection terlatih pada dataset Roboflow `card-grader`.
* **Kelas Cacat Fisik & Pengali Depresiasi ($F_{condition}$):**
  * `Clean / Mint (Mulus)` → Multiplier = **1.00** *(Nilai penuh)*
  * `Scratched (Lecet Permukaan)` → Multiplier = **0.85** *(Penurunan 15%)*
  * `Edge Wear (Kikis Tepi)` → Multiplier = **0.80** *(Penurunan 20%)*
  * `Bent / Crease (Tertekuk)` → Multiplier = **0.65** *(Penurunan 35%)*

---

### 3️⃣ Formula Valuasi Harga Wajar Dinamis

$$P_{\text{final}} = P_{\text{base}} \times M_{\text{variant}} \times F_{\text{condition}} \times F_{\text{market}}$$

* **$P_{base}$:** Harga pasar efektif konsolidasi TCGPlayer & Cardmarket dari Supabase Cloud.
* **$M_{variant}$:** Pengali kelangkaan edisi khusus (Vintage sebelum tahun 2005: $+20\%$ s/d $+50\%$, Secret Rare/Promo: $+15\%$ s/d $+35\%$).
* **$F_{condition}$:** Pengali kondisi fisik objektif dari Model 2 YOLOv8.
* **$F_{market}$:** Atribut kondisi penjualan (Bahasa Inggris/Jepang vs Indonesia, kelengkapan Toploader/Sleeve).

---

## ⚡ Tolak Ukur Kuantitatif & Benchmark Komputasi

| Parameter Evaluasi | Nilai Benchmark | Catatan Implementasi |
|---|:---:|---|
| **Latensi Inferensi GPU (RTX 2050)** | **~18 ms** | CUDA PyTorch Tensor Stream (`card_identifier_realtime.py`) |
| **Latensi Inferensi CPU (Optimized)** | **~83 ms** | Single-View + In-Memory ORB Descriptor Caching |
| **Pencarian Indeks Vektor FAISS** | **< 1 ms** | `IndexFlatIP` untuk 20.617 kartu (~42 MB RAM) |
| **Frame Rate Kamera Live** | **30+ FPS** | Stabil berkat pemisahan *Asynchronous Worker Thread* |
| **Dimensi Representasi Vektor** | **512 Dimensi** | $L_2$-Normalized Hypersphere Embeddings |
| **Ukuran Dataset Katalog** | **20.617 Kartu** | Database resmi pokemontcg.io (1999–2024) |
| **Sinkronisasi Harga Harian** | **Otomatis Harian** | GitHub Actions Cron Job mengupdate harga pasar ke Supabase |

---

## 📊 Dataset & Database Cloud Supabase

| Entitas Data | Volume | Keterangan |
|---|:---:|---|
| **Katalog Kartu Bersih** | **20.617 baris** | Sinkron 1-to-1 di Supabase, CSV, dan JSON |
| **Ekspansi Rilis (Sets)** | **172 Set** | Base Set (1999) hingga ekspansi modern |
| **Gambar Terkompresi** | **20.617 JPG** | Resolusi 640×640 Lanczos di `backend/dataset/compressed_images/` |
| **Tabel Supabase Cloud** | **4 Tabel Relasional** | `sets`, `cards`, `card_prices`, `card_price_history` |
| **Cakupan Harga Efektif** | **95,48%** | 19.686 kartu memiliki data harga pasar aktif |
| **Median Harga Pasar** | **$0,96 (~Rp14.880)** | 50% kartu Pokémon bernilai $\le$ $1 USD (*Right-Skewed*) |

> [!TIP]
> Dokumentasi rinci mengenai variabel data, skema SQL, dan analisis statistik:
> * 📄 [`docs/clip_model_architecture_and_rationale.md`](docs/clip_model_architecture_and_rationale.md) — Arsitektur & rasional ilmiah CLIP ViT-B-32.
> * 📄 [`docs/dataset_dictionary.md`](docs/dataset_dictionary.md) — Kamus data 22 variabel CSV.
> * 📄 [`docs/supabase_database_dictionary.md`](docs/supabase_database_dictionary.md) — Skema database PostgreSQL Supabase.
> * 📄 [`docs/schema.sql`](docs/schema.sql) — Script DDL pembuatan tabel database.

---

## 🏗️ Struktur Repositori

```text
pokemon-card-value-analytic-tool/
├── .github/
│   └── workflows/
│       └── daily_price_cron.yml          # GitHub Actions cron pelacak harga harian otomatis
│
├── backend/                              # Backend Python, Database, & CV Engine
│   ├── app/                              # Modular REST API (FastAPI)
│   │   ├── main.py                       # Server Entrypoint (/identify, /analyze, /cards, /sets)
│   │   ├── cv_service.py                 # In-Memory Bridge (Model 1 CLIP + Model 2 YOLO)
│   │   ├── analytics_engine.py           # Formula Valuasi Harga Wajar & Sinyal Transaksi
│   │   └── schemas.py                    # Skema validasi Pydantic (Request, Response, Pricing)
│   │
│   ├── dataset/                          # Master Data & Asset Citra
│   │   ├── pokemon_cards_dataset_cleaned.csv  # Dataset Bersih (20.617 baris, 22 kolom)
│   │   ├── pokemon_cards_dataset_cleaned.json # Dataset JSON
│   │   ├── compressed_images/            # 20.617 gambar JPG 640x640 terkompresi
│   │   └── card-condition-dataset/       # Dataset Roboflow untuk pelatihan Model 2
│   │
│   ├── models/                           # Model AI & Engine Identifikasi
│   │   ├── card_identifier.py            # Engine Utama Model 1 (CLIP + FAISS + ORB + Sigmoid)
│   │   ├── card_identifier_realtime.py   # Live Scanner HUD 30+ FPS (Asynchronous Worker Thread)
│   │   ├── card_identifier_oncam.py      # Pemindai Snapshot Kamera Interaktif
│   │   ├── card_identifier_manual.py     # Pengujian Foto Statis (GUI File Explorer / CLI)
│   │   ├── card_condition_grader.py      # Engine Model 2 (Roboflow YOLOv8 Defect Detection)
│   │   ├── build_card_index.py           # Generator Vektor Indeks FAISS resmi (CLIP ViT-B-32)
│   │   ├── card_embeddings.index         # Binary Indeks FAISS (512-dim, 20.617 kartu, ~42 MB)
│   │   ├── card_id_map.json              # Pemetaan indeks FAISS ke card_id resmi
│   │   └── legacy_mobilenet/             # [Arsip] Baseline MobileNetV3 untuk studi komparasi
│   │
│   ├── notebooks/                        # Eksplorasi Analisis Data (Jupyter Notebooks)
│   │   ├── eda_research_tcg.ipynb        # Visualisasi distribusi data & pemodelan
│   │   └── valuation_analytics.ipynb     # Analisis mendalam pasar & arbitrase harga
│   │
│   ├── seed_supabase.py                  # Seeding dataset bersih ke Supabase Cloud
│   ├── daily_price_tracker.py            # Sinkronisasi harga harian dari pokemontcg.io
│   ├── compress_images.py                # Kompresi paralel gambar ke format JPG Lanczos
│   ├── requirements.txt                  # Dependensi Python Backend
│   └── .env                              # Konfigurasi API Keys & CAMERA_SOURCE
│
├── frontend/                             # Single Page Application (React 18 + Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── CatalogPage.jsx           # Katalog Interaktif 20.000+ kartu (Filter, Search, Sort)
│   │   │   ├── ScannerDashboard.jsx      # Live Scanner Web UI (Webcam Feed & Valuasi Instan)
│   │   │   ├── DashboardPage.jsx         # Analitika Data Pasar & Visualisasi Agregat
│   │   │   ├── UploadPage.jsx            # Upload Foto Statis & Deteksi Cacat YOLOv8
│   │   │   ├── HeroSection.jsx           # Banner Utama Interaktif
│   │   │   └── Navbar.jsx                # Navigasi Global
│   │   ├── App.jsx                       # Routing & State Manajer
│   │   └── main.jsx                      # Entrypoint React
│   └── package.json                      # Dependensi Node.js
│
├── docs/                                 # Dokumentasi Teknis Lengkap
└── README.md                             # Dokumentasi Utama Proyek
```

---

## 🚀 Panduan Menjalankan Sistem

### Persyaratan Awal:
* **Python 3.10 – 3.12** dengan virtual environment terisolasi (`pokemon_env`).
* **Node.js 18+** & npm.
* Kamera laptop atau Kamera HP melalui aplikasi **DroidCam**.

---

### 1. Menjalankan Live Scanner HUD (Real-Time 30+ FPS)

Mode ini adalah demonstrasi visual utama Model 1:
```powershell
# Jalankan dengan environment Python proyek:
& "D:\pokemon_env\Scripts\python.exe" backend/models/card_identifier_realtime.py
```
* **Kamera HP (DroidCam):** Atur variabel `CAMERA_SOURCE=http://<IP_HP>:4747/video` di [backend/.env](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/.env).
* **Webcam Laptop:** Atur `CAMERA_SOURCE=0` di [backend/.env](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/.env).
* **Shortcut Keyboard saat HUD Berjalan:**
  * `[Spasi]` : Freeze / Unfreeze frame pemindaian.
  * `[M]` : Toggle mode Fullscreen.
  * `[R]` : Rotasi orientasi tampilan (0° / 90° / 180° / 270°).
  * `[F]` : Mengirim sinyal Autofokus ke kamera HP.
  * `[Q]` : Keluar dari aplikasi.

---

### 2. Menjalankan Backend Server (FastAPI)

```powershell
cd backend
& "D:\pokemon_env\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
```
* Server berjalan di: `http://127.0.0.1:8000`
* Dokumentasi Interaktif (Swagger UI): `http://127.0.0.1:8000/docs`
* **Endpoints Utama:**
  * `POST /identify` : Identifikasi cepat Model 1 (Base64 citra kamera).
  * `POST /analyze` : Analisis lengkap citra statis (Model 1 + Model 2 YOLOv8).
  * `GET  /cards` : Katalog kartu Pokémon (mendukung parameter `search`, `supertype`, `rarity`, `set_id`, `sort_by`, `page`, `limit`).
  * `GET  /sets` : Daftar seluruh set kartu untuk filter dropdown.
  * `GET  /cards/{card_id}/history` : Riwayat tren harga harian untuk grafik pasar.
  * `GET  /health` : Healthcheck status server.

---

### 3. Menjalankan Frontend Web Portal (React + Vite)

Buka terminal baru:
```powershell
cd frontend
npm install
npm run dev
```
Buka browser di: **`http://localhost:5173`**
* **Navigasi Halaman:**
  * **CATALOG (`#catalog`):** Eksplorasi 20.000+ kartu lengkap dengan foto, nama, nomor set, dan harga pasar wajar.
  * **DASHBOARD (`#dashboard`):** Pindai kartu langsung melalui browser menggunakan webcam, visualisasikan grafik pergerakan harga historis, dan terima rekomendasi transaksi (BUY/HOLD/SELL).
  * **UPLOAD / INSPECT:** Unggah berkas foto kartu dari galeri untuk analisis cacat fisik komprehensif.

---

### 4. Pengujian Model & Skrip Tambahan

* **Uji Foto Manual (GUI File Explorer):**
  ```powershell
  & "D:\pokemon_env\Scripts\python.exe" backend/models/card_identifier_manual.py
  ```
* **Membangun Ulang Indeks Vektor FAISS:**
  ```powershell
  & "D:\pokemon_env\Scripts\python.exe" backend/models/build_card_index.py
  ```
* **Jalankan Pelacak Harga Harian:**
  ```powershell
  & "D:\pokemon_env\Scripts\python.exe" backend/daily_price_tracker.py
  ```

---

## 📜 Lisensi & Atribusi

* **Metadata Kartu & Harga Pasar:** [pokemontcg.io REST API](https://pokemontcg.io/)
* **Vision Transformer Backbone (Model 1):** [OpenAI CLIP (OpenCLIP)](https://github.com/mlfoundations/open_clip)
* **Dataset Cacat Fisik (Model 2):** [Roboflow Universe — Card Grader](https://universe.roboflow.com/group-6-major-project/card-grader)
* **Dataset Centering Tambahan:** [GemSnipe Pokemon Centering Measurements](https://gemsnipe.com/) (Open-Source CC BY 4.0 via Contributor Issue #1)
* **Vector Retrieval Engine:** [Meta AI FAISS](https://github.com/facebookresearch/faiss)
* **Cloud Database:** [Supabase PostgreSQL](https://supabase.com/)
