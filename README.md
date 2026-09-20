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
[![API](https://img.shields.io/badge/Data_Source-pokemontcg.io-FFCB05?style=flat&logo=pokemon&logoColor=blue)](https://pokemontcg.io/)

---

## 📌 Ringkasan Proyek

**Pokemon Card Value Analytic Tool (REGOKEMON)** adalah sistem analitika data dan intelijen buatan berbasis **Dual-Model Computer Vision** yang dirancang untuk membantu penjual maupun pembeli kartu Pokémon pada **marketplace umum** (seperti Tokopedia, Shopee, eBay, atau forum jual-beli lokal). 

Sistem ini menyelesaikan 3 permasalahan utama dalam transaksi kartu koleksi TCG:
1. **Identifikasi Kartu Otomatis (Model 1):** Mengenali jenis kartu secara presisi dan instan (< 10 ms) dari foto kamera HP atau webcam di antara **20.426 jenis kartu** menggunakan representasi visual **OpenAI CLIP (ViT-B-32)**.
2. **Estimasi Kondisi Fisik Otomatis (Model 2):** Mengidentifikasi cacat fisik kartu (lecet, tertekuk, aus pinggir) secara objektif menggunakan Computer Vision berbasis **YOLOv8**.
3. **Valuasi Harga Pasar Wajar & Sinyal Transaksi:** Menghitung deviasi harga penawaran marketplace dibanding harga pasar wajar (*fair market price*) dan memberikan rekomendasi **BUY (Beli)**, **HOLD (Tahan)**, atau **SELL (Kemahalan)**.

---

## 🤖 Arsitektur Dual-Model Computer Vision

Sistem ini menggunakan **2 Model Computer Vision independen** yang bekerja secara sekuensial untuk menghasilkan analisis kartu yang akurat:

```text
[ Foto Kartu dari Kamera HP / IP Webcam / Upload ]
                         │
                         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ 1. SMART STATIC FRAME & 4-WAY AUTO-ORIENTATION           │
 │    - Panduan bingkai portrait standar kartu (rasio 63:88)│
 │    - Deteksi ketajaman real-time (Laplacian variance)    │
 │    - Rotasi otomatis 4 arah (0°, 90°, 180°, 270°)        │
 └────────────────────────────┬─────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
 ┌─────────────────────────────┐   ┌─────────────────────────────┐
 │ MODEL 1: Card Identifier    │   │ MODEL 2: Condition Grader   │
 │ (Default: OpenAI CLIP)      │   │ (Defect Detection)          │
 ├─────────────────────────────┤   ├─────────────────────────────┤
 │ • Backbone: CLIP ViT-B-32   │   │ • YOLOv8 / Roboflow         │
 │ • FAISS IndexFlatIP (512-d) │   │ • Deteksi Kerusakan Fisik:  │
 │ • Database: 20.426 Kartu    │   │   - Clean / Mint (1.00x)    │
 │ • Hybrid ORB Re-ranking     │   │   - Scratched (0.85x)       │
 │ • Pencarian sub-milidetik   │   │   - Edge Wear (0.80x)       │
 │ • Alternative: MobileNetV3  │   │   - Bent/Crease (0.65x)     │
 └──────────────┬──────────────┘   └──────────────┬──────────────┘
                │                                 │
                └────────────────┬────────────────┘
                                 │
                                 ▼
 ┌──────────────────────────────────────────────────────────┐
 │ ANALYTICS ENGINE & VALUATION FORMULA                     │
 │ - Sinkronisasi Harga Pasar Supabase Cloud (20.426 kartu) │
 │ - Menghitung P_final (Harga Pasar Wajar Realistis)       │
 │ - Menghitung Deviasi Harga Penawaran Marketplace         │
 │ - Menghasilkan Sinyal: BUY / HOLD / SELL                 │
 └──────────────────────────────────────────────────────────┘
```

### 1️⃣ Model 1: Card Identification Engine (Default: OpenAI CLIP ViT-B-32)
* **Tujuan:** Mengenali **jenis kartu** (Nama, Set, Nomor Seri, Rarity) dari foto input di antara 20.426 kartu acuan.
* **Arsitektur Default (Produksi):** **OpenAI CLIP (Vision Transformer ViT-B-32)** pre-trained kontrastif pada 400M pasangan gambar-teks.
  * **Mengapa CLIP?** Model klasifikasi umum seperti MobileNetV3 dilatih pada ImageNet (foto objek riil dunia nyata seperti anjing, mobil, dsb), sehingga rentan salah mengenali ilustrasi 2D bergaya anime/fanart dan sensitif terhadap cahaya. CLIP memahami semantik grafis dan variasi ilustrasi secara mendalam, menghasilkan akurasi pencocokan yang jauh lebih tinggi.
* **Fitur Utama Engine:**
  1. **512-Dimension Visual Embeddings:** Representasi fitur visual yang padat dan sangat diskriminatif.
  2. **FAISS IndexFlatIP:** Indeks pencarian vektor berbasis *Cosine Similarity* yang memproses 20.426 kartu dalam hitungan sub-milidetik.
  3. **4-Way Smart Auto-Orientation:** Secara cerdas mengevaluasi sudut rotasi kartu (0°, 90°, 180°, 270°) terhadap FAISS, sehingga kartu yang difoto miring atau terbalik otomatis ditegakkan sebelum identifikasi.
  4. **Hybrid ORB Verification:** Verifikasi fitur lokal (ORB keypoints) pada Top-50 kandidat FAISS untuk membedakan kartu reprint atau varian foil yang memiliki layout mirip.
* **Alternative Baseline Model (MobileNetV3):**
  Implementasi lama berbasis MobileNetV3 diarsipkan di folder `backend/models/legacy_mobilenet/` untuk kebutuhan studi komparasi (*ablation study*) dan analisis performa pada laporan tugas akhir.

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

## 📊 Dataset & Database Supabase Cloud

| Statistik Dataset | Nilai | Keterangan |
|---|:---:|---|
| **Total Kartu Bersih** | **20.426 kartu** | Konsisten 1-to-1 antara Supabase, CSV, JSON, & Gambar Fisik |
| **Total Gambar Terkompresi** | **20.426 file JPG** | Tersimpan di `backend/dataset/compressed_images/` |
| **Gambar Master PNG** | **20.426 file PNG** | Tersimpan di `backend/dataset/raw_images/` |
| **Database Produksi** | **Supabase Cloud (PostgreSQL)** | 3 tabel terelasi: `sets`, `cards`, `card_prices` |
| **Coverage Harga Pasar** | **96.29%** | 19.186 dari 20.426 kartu memiliki histori harga aktif |
| **Total Kolom Fitur CSV** | **22 Kolom** | Rarity, Supertype, Subtypes, Types, HP, Release Year, TCGPlayer, Cardmarket, Effective Market Price |

> [!NOTE]
> **Penanganan Kasus Khusus Windows File System:**
> Kartu **Unown ? (`ex10-?`)** dari edisi *Unseen Forces (2005)* memiliki karakter `?` yang dilarang pada sistem berkas Windows (`< > : " / \ | ? *`). Berkas gambarnya otomatis dipetakan kembali dari `question_hires.jpg` ke ID `ex10-?` sehingga dataset tetap sinkron 20.426 kartu tanpa kehilangan data.

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
├── backend/                              # Python Backend, Database & Computer Vision Engine
│   ├── app/
│   │   ├── analytics_engine.py           # Mesin kalkulasi harga wajar & sinyal rekomendasi
│   │   ├── cv_detector.py                # Pipeline Model 1 (CLIP) & Model 2 (YOLOv8)
│   │   └── main.py                       # REST API (FastAPI)
│   ├── dataset/                          # Master Dataset & Berkas Citra
│   │   ├── pokemon_cards_dataset_cleaned.csv  # CSV Cleaned (20.426 baris, 22 kolom)
│   │   ├── pokemon_cards_dataset_cleaned.json # JSON Cleaned (20.426 item)
│   │   ├── compressed_images/            # 20.426 gambar JPG terkompresi
│   │   └── card-condition-dataset/       # Dataset Roboflow untuk Model 2
│   ├── models/                           # Engine Model 1 Resmi & Vektor Indeks
│   │   ├── card_identifier.py            # Engine resmi Model 1 (CLIP ViT-B-32 + FAISS + ORB)
│   │   ├── card_identifier_oncam.py       # Pemindai kamera langsung (Webcam / IP Webcam HP)
│   │   ├── card_identifier_manual.py     # Skrip pengujian foto manual dengan GUI File Explorer
│   │   ├── build_card_index.py           # Skrip pembuat indeks FAISS resmi berbasis CLIP
│   │   ├── card_embeddings.index         # Vektor index FAISS (512-dim, 20.426 kartu) [di-ignore git]
│   │   ├── card_id_map.json              # Pemetaan indeks ke card_id resmi
│   │   └── legacy_mobilenet/             # [Arsip] Baseline alternatif MobileNetV3 untuk komparasi
│   │       ├── README.md                 # Dokumentasi penggunaan baseline MobileNet
│   │       ├── card_identifier.py        # Engine MobileNetV3 lama
│   │       ├── card_identifier_oncam.py  # Pemindai kamera MobileNet lama
│   │       └── card_identifier_manual.py # Pemindai manual MobileNet lama
│   ├── seed_supabase.py                  # Skrip migrasi & seeding data ke Supabase Cloud
│   ├── json_to_csv.py                    # Skrip ekstraksi, pembersih, & normalisasi dataset
│   ├── compress_images.py                # Skrip kompresi gambar dataset
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
├── docs/                                 # Dokumentasi proyek & kamus data
│   └── dataset_dictionary.md             # Kamus data & skema 22 variabel dataset
├── .gitignore                            # Filter virtual env, index binary, & secret .env
└── README.md                             # Dokumentasi Utama Repositori GitHub
```

---

## 🚀 Panduan Menjalankan Model 1 (Card Identifier)

### 1. Pemindaian Kamera Langsung (Live On-Cam)
Mendukung webcam laptop maupun **Kamera HP (via IP Webcam)** yang didefinisikan di berkas `.env` (`CAMERA_SOURCE`):
```bash
# Jalankan pemindai kamera:
python backend/models/card_identifier_oncam.py
```
* **Spasi / Klik:** Mengambil gambar (*capture*) pada kotak panduan.
* **Q:** Keluar dari pemindai.

### 2. Pengujian Foto Kartu Manual (Manual File Scanner)
Dapat dijalankan secara interaktif dengan jendela File Explorer atau langsung lewat command line:
```bash
# Mode Interaktif (Jendela File Explorer):
python backend/models/card_identifier_manual.py

# Mode Otomatis dengan Validasi Kartu:
python backend/models/card_identifier_manual.py path/foto_kartu.jpg --expected_card_id sv8pt5-77
```

### 3. Membangun Ulang Indeks Vektor CLIP (Jika Menambah Kartu Baru)
```bash
python backend/models/build_card_index.py
```

### 4. Menjalankan Baseline MobileNet (Untuk Studi Komparasi Laporan)
```bash
python backend/models/legacy_mobilenet/card_identifier_manual.py path/foto_kartu.jpg --expected_card_id sv8pt5-77
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
*(Backend berjalan di `http://localhost:8000`)*

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
