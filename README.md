# Pokemon Card Value Analytic Tool (REGOKEMON) 🎴📊

> **Dashboard Analitika Data, Dual-Model Computer Vision & Estimasi Harga Wajar Kartu Pokémon untuk Marketplace**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
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

**Pokemon Card Value Analytic Tool (REGOKEMON)** adalah sistem analitika data dan intelijen buatan berbasis **Dual-Model Computer Vision** yang dirancang untuk membantu penjual maupun pembeli kartu Pokémon pada **marketplace umum** (seperti Tokopedia, Shopee, eBay, atau forum jual-beli lokal). 

Sistem ini menyelesaikan 3 permasalahan utama dalam transaksi kartu koleksi TCG:
1. **Identifikasi Kartu Otomatis (Model 1):** Mengenali jenis kartu secara presisi dan instan (< 10 ms) dari foto kamera HP atau webcam di antara **20.617 jenis kartu** menggunakan representasi visual **OpenAI CLIP (ViT-B-32)** dan indeks vektor **FAISS**.
2. **Estimasi Kondisi Fisik Otomatis (Model 2):** Mengidentifikasi cacat fisik kartu (lecet, tertekuk, aus pinggir) secara objektif menggunakan Computer Vision berbasis **YOLOv8**.
3. **Valuasi Harga Pasar Wajar & Sinyal Transaksi:** Menghitung deviasi harga penawaran marketplace dibanding harga pasar wajar (*fair market price*) dan memberikan rekomendasi **BUY (Beli)**, **HOLD (Tahan)**, atau **SELL (Kemahalan)**.

---

## 🤖 Arsitektur Dual-Model Computer Vision

Sistem ini menggunakan **2 Model Computer Vision independen** yang bekerja secara terintegrasi untuk menghasilkan analisis kartu yang akurat:

```text
[ Foto Kartu dari Kamera HP / IP Webcam / Upload ]
                         │
                         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ 1. SMART STATIC FRAME & 4-WAY AUTO-ORIENTATION           │
 │    - Panduan bingkai portrait standar kartu (rasio 63:88)│
 │    - Deteksi ketajaman real-time (Laplacian variance)    │
 │    - Rotasi otomatis 4 arah (0°, 90°, 180°, 270°)        │
 └───────────────────────────┬──────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
 ┌─────────────────────────────┐   ┌─────────────────────────────┐
 │ MODEL 1: Card Identifier    │   │ MODEL 2: Condition Grader   │
 │ (Default: OpenAI CLIP)      │   │ (Defect Detection)          │
 ├─────────────────────────────┤   ├─────────────────────────────┤
 │ • Backbone: CLIP ViT-B-32   │   │ • YOLOv8 / Roboflow         │
 │ • FAISS IndexFlatIP (512-d) │   │ • Deteksi Kerusakan Fisik:  │
 │ • Database: 20.617 Kartu    │   │   - Clean / Mint (1.00x)    │
 │ • Hybrid ORB Re-ranking     │   │   - Scratched (0.85x)       │
 │ • Pencarian sub-milidetik   │   │   - Edge Wear (0.80x)       │
 │ • Alternative: MobileNetV3  │   │   - Bent/Crease (0.65x)     │
 └─────────────┬───────────────┘   └─────────────┬───────────────┘
                │                                 │
                └────────────────┬────────────────┘
                                 │
                                 ▼
 ┌──────────────────────────────────────────────────────────┐
 │ ANALYTICS ENGINE & VALUATION FORMULA                     │
 │ - Sinkronisasi Harga Pasar Supabase Cloud (20.617 kartu) │
 │ - Menghitung P_final (Harga Pasar Wajar Realistis)       │
 │ - Menghitung Deviasi Harga Penawaran Marketplace         │
 │ - Menghasilkan Sinyal Transaksi: BUY / HOLD / SELL       │
 └──────────────────────────────────────────────────────────┘
```

### 1️⃣ Model 1: Card Identification Engine (Default: OpenAI CLIP ViT-B-32)
* **Tujuan:** Mengenali **jenis kartu** (Nama, Set, Nomor Seri, Rarity) dari foto input di antara 20.617 kartu acuan.
* **Arsitektur Default (Produksi):** **OpenAI CLIP (Vision Transformer ViT-B-32)** pre-trained kontrastif pada 400M pasangan gambar-teks.
  * **Mengapa CLIP?** Model klasifikasi umum seperti MobileNetV3 dilatih pada ImageNet (foto objek riil dunia nyata), sehingga rentan salah mengenali ilustrasi 2D bergaya anime/fanart dan sangat sensitif terhadap pencahayaan. CLIP memahami semantik grafis dan variasi ilustrasi secara mendalam, menghasilkan akurasi pencocokan visual yang jauh lebih tinggi.
* **Fitur Utama Engine:**
  1. **512-Dimension Visual Embeddings:** Representasi fitur visual yang padat dan sangat diskriminatif.
  2. **FAISS IndexFlatIP:** Indeks pencarian vektor berbasis *Cosine Similarity* yang memproses 20.617 kartu dalam hitungan sub-milidetik.
  3. **4-Way Smart Auto-Orientation:** Secara cerdas mengevaluasi sudut rotasi kartu (0°, 90°, 180°, 270°) terhadap FAISS, sehingga kartu yang difoto miring atau terbalik otomatis ditegakkan sebelum identifikasi.
  4. **Hybrid ORB Verification:** Verifikasi fitur lokal (ORB keypoints) pada Top-50 kandidat FAISS untuk membedakan kartu reprint atau varian foil yang memiliki layout mirip.
* **Alternative Baseline Model (MobileNetV3):**
  Implementasi lama berbasis MobileNetV3 diarsipkan di folder `backend/models/legacy_mobilenet/` untuk kebutuhan studi komparasi (*ablation study*) dan analisis performa pada laporan akademik.

### 2️⃣ Model 2: Card Condition Grader Engine (Defect Detection)
* **Tujuan:** Mendeteksi **cacat dan kondisi fisik** kartu secara objektif.
* **Metode ML:** *YOLOv8 Object Detection / Bounding Box Segmentation*.
* **Dataset Training:** Dataset Roboflow Universe `card-grader` (tersimpan di `backend/dataset/card-condition-dataset/`).
* **Kelas Cacat Fisik & Multiplier Kondisi ($F_{condition}$):**
  * `Clean / Mint (Mulus)` $\rightarrow$ Multiplier = **1.00** *(Tanpa Potongan Harga)*
  * `Scratched / Lecet` $\rightarrow$ Multiplier = **0.85** *(Diskon 15%)*
  * `Edge Wear / Aus Pinggir` $\rightarrow$ Multiplier = **0.80** *(Diskon 20%)*
  * `Bent / Tertekuk / Crease` $\rightarrow$ Multiplier = **0.65** *(Diskon 35%)*

---

## 📊 Dataset, Metrik Pasar & Database Cloud

Regokemon menggunakan master dataset yang telah melalui proses kurasi ketat (*data cleaning & image verification*):

| Statistik Dataset | Nilai | Keterangan |
|---|:---:|---|
| **Total Kartu Bersih Siap Pakai** | **20.617 kartu** | Konsisten 1-to-1 antara Supabase, CSV, JSON, & File Gambar Fisik |
| **Total Edisi Set (Expansions)** | **172 Set** | Base Set (1999) hingga ekspansi terbaru *30th Celebration* (2026) |
| **Aset Master Gambar Mentah** | **20.617 file PNG** | Tersimpan di `backend/dataset/raw_images/` |
| **Aset Gambar Terkompresi** | **20.617 file JPG** | Resolusi 640×640 Lanczos di `backend/dataset/compressed_images/` |
| **Kartu Broken Links (Dieliminasi)** | **53 kartu (0,26%)** | Tautan mati CDN pokemontcg.io (tercatat di `broken_links_report.csv`) |
| **Database Cloud Produksi** | **Supabase (PostgreSQL)** | 4 tabel: `sets`, `cards`, `card_prices`, `card_price_history` |
| **Cakupan Harga Efektif Pasar** | **95,48% (19.686 kartu)** | Memiliki harga pasar gabungan TCGPlayer & Cardmarket |
| **Median Harga Pasar Riil** | **$0,96 (~Rp14.880)** | 50% kartu Pokémon di pasar bernilai $\le$ $1 USD (*Right-Skewed*) |
| **Kartu Termahal di Dataset** | **$4.500,00 (~Rp70 Juta)** | *Lugia - Aquapolis (Rare Secret)* |

> [!TIP]
> Rincian analisis statistik distribusi harga, kuartil ($Q_1, Q_3, P_{99}$), dan arsitektur data tersedia lengkap di:  
> 📄 [`docs/dataset_summary_and_metrics.md`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/docs/dataset_summary_and_metrics.md) dan [`docs/dataset_dictionary.md`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/docs/dataset_dictionary.md).

---

## ⚙️ Formula Valuasi Harga Wajar ($P_{final}$)

Aplikasi ini menggabungkan 4 kategori parameter utama untuk menghasilkan nilai estimasi harga pasar wajar yang realistis:

$$P_{final} = P_{base} \times M_{variant} \times F_{condition} \times F_{market}$$

* **$P_{base}$ (Harga Dasar Pasar):** Diambil dari `effective_market_price` (kombinasi `tcgplayer.market` dan `cardmarket.avg30` dari database Supabase/CSV).
* **$M_{variant}$ (Pengali Varian & Vintage):** 
  * Vintage (Tahun rilis $< 2005$): Multiplier $+20\%$ hingga $+50\%$.
  * Special Subtype / Edisi Khusus (Pikachu bertopi, Promo, VMAX, Secret Rare): Multiplier $+15\%$ s/d $+35\%$.
* **$F_{condition}$ (Faktor Kondisi Fisik - Model 2 YOLOv8):**
  * `Clean / Mint` = $1.00$ | `Scratched` = $0.85$ | `Edge Wear` = $0.80$ | `Bent / Crease` = $0.65$
* **$F_{market}$ (Faktor Attributes Marketplace):**
  * Bahasa: English/Japanese = $1.00$ | Bahasa Indonesia = $0.85$
  * Proteksi: Loose = $1.00$ | In-Sleeve/Toploader = $1.05$ | Sealed Pack = $1.25$

---

## 🏗️ Struktur Repositori

```text
pokemon-card-value-analytic-tool/
├── .github/
│   └── workflows/
│       └── daily_price_cron.yml          # GitHub Actions cron otomatis pelacak harga harian
│
├── backend/                              # Backend Python, Database, & CV Engine
│   ├── app/
│   │   ├── analytics_engine.py           # Mesin kalkulasi harga wajar & sinyal rekomendasi
│   │   ├── cv_detector.py                # Pipeline Model 1 (CLIP) & Model 2 (YOLOv8)
│   │   └── main.py                       # REST API Server (FastAPI)
│   ├── dataset/                          # Master Dataset & Berkas Citra
│   │   ├── pokemon_cards_dataset_cleaned.csv  # CSV Bersih (20.617 baris, 22 kolom fitur)
│   │   ├── pokemon_cards_dataset_cleaned.json # JSON Bersih (20.617 item)
│   │   ├── broken_links_report.csv       # Laporan deterministik 53 tautan gambar mati
│   │   ├── raw_images/                   # 20.617 gambar master PNG asli
│   │   ├── compressed_images/            # 20.617 gambar JPG 640x640 terkompresi
│   │   └── card-condition-dataset/       # Dataset Roboflow untuk pelatihan Model 2
│   ├── models/                           # Engine Model 1 Resmi & Vektor Indeks
│   │   ├── card_identifier.py            # Engine Model 1 (CLIP ViT-B-32 + FAISS + ORB)
│   │   ├── card_identifier_oncam.py       # Pemindai kamera langsung (Webcam / IP Webcam HP)
│   │   ├── card_identifier_manual.py     # Skrip pengujian foto manual dengan GUI File Explorer
│   │   ├── build_card_index.py           # Skrip pembuat indeks FAISS resmi berbasis CLIP
│   │   ├── card_embeddings.index         # Vektor index FAISS (512-dim, 20.617 kartu)
│   │   ├── card_id_map.json              # Pemetaan indeks FAISS ke card_id resmi
│   │   └── legacy_mobilenet/             # [Arsip] Baseline MobileNetV3 untuk komparasi
│   ├── notebooks/                        # Eksplorasi Analisis Data (Jupyter Notebooks)
│   │   ├── eda_research_tcg.ipynb        # Riset data, visualisasi sebaran & pemodelan
│   │   └── valuation_analytics.ipynb     # Analisis mendalam valuasi & arbitrase pasar
│   ├── clean_csv_broken_links.py         # Skrip filter validasi status HTTP tautan gambar
│   ├── export_broken_links.py            # Skrip audit & ekspor kartu bertautan rusak
│   ├── pokemon_cards_dataset_download.py # Skrip pengunduh paralel ribuan gambar master PNG
│   ├── compress_images.py                # Skrip kompresi gambar paralel ke format JPG
│   ├── json_to_csv.py                    # Skrip sinkronisasi & ekstraksi JSON mentah ke CSV
│   ├── seed_supabase.py                  # Skrip seeding dataset bersih ke database Supabase
│   ├── daily_price_tracker.py            # Engine sinkronisasi harga harian dari pokemontcg.io
│   ├── .env.example                      # Template konfigurasi variabel lingkungan
│   └── requirements.txt                  # Dependensi library Python backend
│
├── frontend/                             # User Interface (React / Vite)
│   ├── src/
│   │   ├── components/                   # Komponen UI (Scanner, PriceChart, SignalBadge)
│   │   ├── App.jsx                       # Komponen Utama Dashboard Web
│   │   └── main.jsx                      # Entrypoint React Client
│   └── package.json                      # Dependensi Node.js frontend
│
├── docs/                                 # Dokumentasi Teknis & Kamus Data
│   ├── dataset_summary_and_metrics.md    # Ringkasan eksekutif, statistik harga & metrik dataset
│   ├── dataset_dictionary.md             # Kamus data & skema 22 variabel fitur dataset CSV
│   ├── supabase_database_dictionary.md   # Skema relasional & kamus tabel Supabase Cloud
│   └── schema.sql                        # Script SQL DDL pembuatan tabel database Supabase
│
├── .gitignore                            # Filter virtual env, index binary, & secret credentials
└── README.md                             # Dokumentasi Utama Repositori GitHub
```

---

## 🚀 Panduan Penggunaan & Eksekusi

### 1. Pemindaian Kartu Kamera Langsung (Live On-Cam)
Mendukung webcam laptop maupun **Kamera HP (via IP Webcam)** yang didefinisikan di berkas `.env` (`CAMERA_SOURCE`):
```bash
python backend/models/card_identifier_oncam.py
```
* **Spasi / Klik:** Mengambil gambar (*capture*) pada kotak panduan.
* **Q:** Keluar dari pemindai.

### 2. Pengujian Foto Kartu Manual (Manual File Scanner)
Dapat dijalankan secara interaktif dengan jendela File Explorer atau langsung lewat command line:
```bash
# Mode Interaktif (Jendela Dialog File Explorer):
python backend/models/card_identifier_manual.py

# Mode Otomatis dengan Validasi Kartu Target:
python backend/models/card_identifier_manual.py path/foto_kartu.jpg --expected_card_id me55-15
```

### 3. Membangun Ulang Indeks Vektor CLIP (Saat Menambah Kartu)
```bash
python backend/models/build_card_index.py
```

### 4. Menjalankan Pelacak Harga Harian (Daily Price Tracker)
```bash
# Mengambil harga harian terbaru dari API dan menyimpannya ke Supabase:
python backend/daily_price_tracker.py
```

---

## 🌐 Menjalankan Full-Stack Application

### 1. Backend Server (FastAPI)
```bash
cd backend
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m app.main
```
*(Backend API berjalan di `http://localhost:8000`)*

### 2. Frontend Dashboard (React / Vite)
```bash
cd frontend
npm install
npm run dev
```
*(Frontend berjalan di `http://localhost:5173`)*

---

## 📜 Lisensi & Atribusi

* **Dataset Metadata & Harga Pasar:** [pokemontcg.io API](https://pokemontcg.io/)
* **Vision Backbone (Model 1):** [OpenAI CLIP (OpenCLIP)](https://github.com/mlfoundations/open_clip)
* **Dataset Kondisi Kartu (Model 2):** [Roboflow Universe — Card Grader](https://universe.roboflow.com/group-6-major-project/card-grader)
* **Vector Search Engine:** [Meta AI FAISS](https://github.com/facebookresearch/faiss)
* **Cloud Database:** [Supabase PostgreSQL](https://supabase.com/)
