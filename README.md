# Pokemon Card Value Analytic Tool (REGOKEMON) 🎴📊

> **Dashboard Analitika Data, Dual-Model Computer Vision & Estimasi Harga Wajar Kartu Pokémon untuk Marketplace**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Index-00599C?style=flat&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Roboflow-00FFFF?style=flat&logo=ultralytics&logoColor=black)](https://universe.roboflow.com/group-6-major-project/card-grader)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![API](https://img.shields.io/badge/Data_Source-pokemontcg.io-FFCB05?style=flat&logo=pokemon&logoColor=blue)](https://pokemontcg.io/)

---

## 📌 Ringkasan Proyek

**Pokemon Card Value Analytic Tool (REGOKEMON)** adalah sistem analitika data dan intelijen buatan berbasis **Dual-Model Computer Vision** yang dirancang untuk membantu penjual maupun pembeli kartu Pokémon pada **marketplace umum** (seperti Tokopedia, Shopee, eBay, atau forum jual-beli lokal). 

Sistem ini menyelesaikan 3 permasalahan utama dalam transaksi kartu koleksi TCG:
1. **Identifikasi Kartu Otomatis:** Mengenali jenis kartu secara instan (< 5 ms) dari foto kamera HP dari total **19.926 jenis kartu**.
2. **Estimasi Kondisi Fisik Otomatis:** Mengidentifikasi cacat fisik kartu (lecet, tertekuk, aus pinggir) secara objektif menggunakan Computer Vision.
3. **Valuasi Harga Pasar Wajar & Sinyal Transaksi:** Menghitung deviasi harga penawaran marketplace dibanding harga pasar wajar (*fair market price*) dan memberikan rekomendasi **BUY (Beli)**, **HOLD (Tahan)**, atau **SELL (Kemahalan)**.

---

## 🤖 Arsitektur Dual-Model Computer Vision

Sistem ini menggunakan **2 Model Computer Vision independen** yang bekerja secara sekuensial untuk menghasilkan analisis kartu yang akurat:

```text
[ Foto Kartu dari Kamera HP / Upload ]
                 │
                 ▼
 ┌───────────────────────────────────────────────┐
 │ 1. PRE-PROCESSING & ALIGNMENT (OpenCV)         │
 │    - Deteksi kontur & batas luar kartu        │
 │    - Perspective Transform (Warp / Meluruskan)│
 └───────────────────────┬───────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
 ┌───────────────────────────┐   ┌───────────────────────────┐
 │ MODEL 1: Card Identifier  │   │ MODEL 2: Condition Grader │
 │ (Fine-Grained Retrieval)  │   │ (Defect Detection)        │
 ├───────────────────────────┤   ├───────────────────────────┤
 │ • Deep Feature Embedding  │   │ • YOLOv8 / Roboflow       │
 │   (MobileNetV3 / ResNet)  │   │ • Deteksi Kerusakan:      │
 │ • FAISS Vector Search     │   │   - Clean / Mint (1.00x)  │
 │ • Database: 19.926 Kartu  │   │   - Scratched (0.85x)     │
 │ • Pencarian < 5 ms        │   │   - Edge Wear (0.80x)     │
 │                           │   │   - Bent/Crease (0.65x)   │
 └─────────────┬─────────────┘   └─────────────┬─────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
 ┌───────────────────────────────────────────────┐
 │ ANALYTICS ENGINE & VALUATION FORMULA          │
 │ - Menghitung P_final (Harga Pasar Wajar)      │
 │ - Menghitung Deviasi Harga Penawaran          │
 │ - Menghasilkan Sinyal: BUY / HOLD / SELL      │
 └───────────────────────────────────────────────┘
```

### 1️⃣ Model 1: Card Identification Engine (Visual Vector Search)
* **Tujuan:** Mengenali **jenis kartu** (Nama, Set, Nomor, Rarity) dari foto input di antara 19.926 kartu acuan.
* **Metode ML:** *One-Shot Metric Learning / Deep Feature Embedding + FAISS Indexing*.
* **Cara Kerja:**
  1. Image Feature Extractor (MobileNetV3 / ResNet) mengubah piksel gambar kartu menjadi vektor fitur 512-dimensi ($E = f_\theta(X)$).
  2. Vektor fitur di-index menggunakan **FAISS (Facebook AI Similarity Search)** untuk pencarian cepat berbasis *Cosine Similarity / Euclidean Distance*.
  3. Mengembalikan Top-K kandidat kartu teratas beserta persentase kemiripannya (*confidence score*).
* **Ukuran & Performa:** Indexing 19.926 kartu hanya memakan memori RAM **~40 MB** dengan latensi pencarian **< 5 ms**.

### 2️⃣ Model 2: Card Condition Grader Engine (Defect Detection)
* **Tujuan:** Mendeteksi **cacat dan kondisi fisik** kartu secara fisik.
* **Metode ML:** *YOLOv8 Object Detection / Bounding Box Segmentation*.
* **Dataset Training:** Dataset Roboflow Universe `card-grader` (tersimpan di `backend/dataset/card-condition-dataset/`).
* **Kelas Cacat Fisik & Multiplier Kondisi ($F_{condition}$):**
  * `Clean / Mint (Mulus)` $\rightarrow$ Multiplier = **1.00** *(Tanpa Potongan Harga)*
  * `Scratched / Lecet` $\rightarrow$ Multiplier = **0.85** *(Diskon 15%)*
  * `Edge Wear / Aus Pinggir` $\rightarrow$ Multiplier = **0.80** *(Diskon 20%)*
  * `Bent / Tertekuk / Crease` $\rightarrow$ Multiplier = **0.65** *(Diskon 35%)*

---

## 📊 Dataset & Pipeline Analitika Data

| Statistik Dataset | Nilai | Keterangan |
|---|:---:|---|
| **Total Kartu Bersih** | **19.926 kartu** | 100% konsisten 1-to-1 antara CSV, JSON, & Gambar Fisik |
| **Total Gambar Fisik** | **19.926 file JPG** | Tersimpan di `backend/dataset/compressed_images/` |
| **Gambar Master PNG** | **19.926 file PNG** | Tersimpan di `backend/dataset/raw_images/` |
| **Coverage Harga Pasar** | **96.29%** | 19.186 dari 19.926 kartu memiliki histori harga aktif |
| **Total Kolom Fitur CSV** | **22 Kolom** | Rarity, Supertype, Subtypes, Types, HP, Release Year, TCGPlayer, Cardmarket, Effective Market Price |

> [!NOTE]
> **Penanganan Kasus Khusus File System:**
> Kartu **Unown ? (`ex10-?`)** dari edisi *Unseen Forces (2005)* memiliki karakter `?` yang dilarang di Windows File System (`< > : " / \ | ? *`). Berkas gambarnya otomatis dipetakan kembali dari `question_hires.jpg` ke ID `ex10-?` sehingga dataset genap 19.926 kartu secara sempurna.

---

## ⚙️ Parameter Penilaian & Formula Valuation

Aplikasi ini menggabungkan 4 kategori parameter utama untuk menghasilkan nilai estimasi harga pasar wajar yang realistis:

### Formula Perhitungan Harga Wajar Akhir ($P_{final}$)

$$P_{final} = P_{base} \times M_{variant} \times F_{condition} \times F_{market}$$

* **$P_{base}$ (Harga Dasar Pasar):** Diambil dari `effective_market_price` (kombinasi `tcgplayer.market` dan `cardmarket.avg30` dari dataset clean).
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
├── backend/                              # Python Backend & Computer Vision Engine
│   ├── app/
│   │   ├── analytics_engine.py           # Mesin kalkulasi harga wajar & sinyal rekomendasi
│   │   ├── cv_detector.py                # Pipeline Model 1 (FAISS) & Model 2 (YOLOv8)
│   │   └── main.py                       # REST API (FastAPI)
│   ├── dataset/                          # Master Dataset & File Gambar
│   │   ├── pokemon_cards_dataset_cleaned.csv  # CSV Cleaned (19.926 baris, 22 kolom)
│   │   ├── pokemon_cards_dataset_cleaned.json # JSON Cleaned (19.926 item)
│   │   ├── compressed_images/            # 19.926 gambar JPG terkompresi
│   │   ├── raw_images/                   # 19.926 gambar PNG master
│   │   └── card-condition-dataset/       # Dataset Roboflow untuk Model 2
│   ├── models/                           # Bobot Model & FAISS Vector Index (.index)
│   ├── notebooks/                        # Jupyter Notebooks (EDA & Visualisasi Data)
│   ├── fetch_pokemon_data.py             # Skrip penarikan API pokemontcg.io
│   ├── json_to_csv.py                    # Skrip ekstraksi, pembersih, & pemeta dataset
│   ├── compress_images.py                # Skrip kompresi gambar
│   ├── .env.example                      # Template variabel lingkungan
│   └── requirements.txt                  # Dependensi library Python backend
│
├── frontend/                             # User Interface (React / Vite)
│   ├── src/
│   │   ├── components/                   # Komponen UI (Scanner, PriceChart, SignalBadge)
│   │   ├── App.jsx                       # Komponen Utama Dashboard Web
│   │   └── main.jsx                      # Entrypoint React Client
│   └── package.json                      # Dependensi Node.js frontend
│
├── docs/                                 # Dokumentasi proyek & konsep pendukung
│   └── dataset_dictionary.md             # Kamus data & skema 22 variabel dataset
├── .gitignore                            # Filter venv, node_modules, cache, & secret .env
└── README.md                             # Dokumentasi Utama Repositori GitHub
```

---

## 🚀 Cara Menjalankan Aplikasi

### 1. Persiapan Backend (Python)

1. Masuk ke folder `backend/`:
   ```bash
   cd backend
   ```
2. Buat dan aktifkan virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```
3. Install dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```
4. Mengompres & Memperbarui Dataset (Jika diperlukan):
   ```bash
   python json_to_csv.py
   ```
5. Jalankan Server API Backend:
   ```bash
   python -m app.main
   ```
   *(Backend akan berjalan pada `http://localhost:8000`)*

### 2. Persiapan Frontend (React)

1. Masuk ke folder `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependensi Node.js:
   ```bash
   npm install
   ```
3. Jalankan server pengembangan frontend:
   ```bash
   npm run dev
   ```
   *(Frontend akan berjalan pada `http://localhost:5173`)*

---

## 📜 Lisensi & Attribution

* **Dataset Metadata & Harga:** [pokemontcg.io API](https://pokemontcg.io/)
* **Dataset Kondisi Kartu:** [Roboflow Universe — Card Grader](https://universe.roboflow.com/group-6-major-project/card-grader)
* **Vector Search Engine:** [Meta AI FAISS](https://github.com/facebookresearch/faiss)



