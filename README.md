# Pokemon Card Value Analytic Tool (PokeScan) 🎴📊

> **Dashboard Analitika Data & Tool Estimasi Harga Wajar Kartu Pokemon untuk Marketplace Umum**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Roboflow](https://img.shields.io/badge/Roboflow-Card--Grader-6700C7?style=flat&logo=roboflow&logoColor=white)](https://universe.roboflow.com/group-6-major-project/card-grader)
[![API](https://img.shields.io/badge/Data_Source-pokemontcg.io-FFCB05?style=flat&logo=pokemon&logoColor=blue)](https://pokemontcg.io/)

---

## 📌 Ringkasan Proyek

**Pokemon Card Value Analytic Tool** adalah sistem analitika data dan sistem cerdas berbasis Computer Vision yang dirancang untuk membantu penjual maupun pembeli kartu Pokemon pada **marketplace umum** (seperti Tokopedia, Shopee, eBay, atau forum jual-beli lokal). 

Sistem ini menyelesaikan permasalahan utama kolektor dan pengguna kasual:
1. **Risiko Overpricing:** Mengetahui harga pasar wajar (*fair market price*) berdasarkan kondisi riil kartu.
2. **Estimasi Kondisi Fisik Otomatis:** Menggunakan model deteksi Computer Vision dari Roboflow (`card-grader`) untuk mengenali kerusakan fisik seperti lecet, tertekuk, atau aus.
3. **Sinyal Keputusan Transaksi:** Memberikan rekomendasi **BUY (Beli)**, **HOLD (Tahan)**, atau **SELL (Jual/Kemahalan)** berbasis analisis tren harga harian dan deviasi dari harga wajar.

---

## ⚙️ Parameter Penilaian & Formula Valuation

Aplikasi ini menggabungkan 4 kategori parameter utama untuk menghasilkan nilai estimasi harga pasar wajar yang realistis:

```
                          [ INPUT PARAMETER ]
                                   │
 ┌──────────────────┬──────────────┴───────────────┬──────────────────┐
 │                  │                              │                  │
 ▼                  ▼                              ▼                  ▼
[ 1. Deteksi Fisik ] [ 2. Varian & Metadata ] [ 3. Attributes ] [ 4. Price Trend ]
- Mint / Mulus       - Rarity (Holo/Secret)    - Bahasa (EN/JP/ID) - TCGPlayer Market
- Scratched / Lecet  - Subtype (VMAX/Bertopi)  - Proteksi (Sleeve/ - Cardmarket Avg7
- Edge Wear / Aus    - Vintage Factor (1999)     Sealed Pack)       - Cardmarket Avg30
- Bent / Tertekuk
         │                  │                              │                  │
         └──────────────────┴──────────────┬───────────────┴──────────────────┘
                                           │
                                           ▼
                       [ KALKULASI HARGA PASAR WAJAR ]
                                           │
                                           ▼
                       [ REKOMENDASI BUY / HOLD / SELL ]
```

### Formula Perhitungan Harga Wajar Akhir ($P_{final}$)

$$P_{final} = P_{base} \times M_{variant} \times F_{condition} \times F_{market}$$

* **$P_{base}$ (Harga Dasar Pasar):** Diambil dari `tcgplayer.market` atau `cardmarket.avg30` via `pokemontcg.io` API.
* **$M_{variant}$ (Pengali Varian & Vintage):** 
  * Vintage (Tahun rilis < 2005): Multiplier $+20\%$ hingga $+50\%$.
  * Special Subtype / Edisi Khusus (Pikachu bertopi, Promo, VMAX, Secret Rare): Multiplier $+15\%$ s/d $+35\%$.
* **$F_{condition}$ (Faktor Kondisi Fisik - Roboflow `card-grader`):**
  * `Clean / Mint (Mulus)` = $1.00$ (Tanpa Potongan)
  * `Scratched / Lecet` = $0.85$ (Diskon 15%)
  * `Edge Wear / Aus Pinggir` = $0.80$ (Diskon 20%)
  * `Bent / Tertekuk / Crease` = $0.65$ (Diskon 35%)
* **$F_{market}$ (Faktor Attributes Marketplace):**
  * Bahasa: English/Japanese = $1.00$ | Bahasa Indonesia = $0.85$
  * Proteksi: Loose = $1.00$ | In-Sleeve/Toploader = $1.05$ | Sealed Pack = $1.25$

---

## 🏗️ Struktur Repositori

Repositori ini menggunakan pemisahan yang rapi dan modular antara `backend` dan `frontend`:

```text
pokemon-card-value-analytic-tool/
├── backend/                  # Python Backend & Computer Vision Engine
│   ├── app/
│   │   ├── analytics_engine.py # Mesin kalkulasi harga wajar & sinyal rekomendasi
│   │   ├── cv_detector.py      # Deteksi kondisi kartu fisik (Roboflow & OpenCV)
│   │   └── main.py             # Entrypoint REST API (FastAPI / Flask)
│   ├── dataset/                # Dataset JSON metadata & harga kartu (pokemontcg.io)
│   ├── models/                 # Model weights (.pt / .onnx / .pkl)
│   ├── notebooks/              # Jupyter Notebooks (api-pokemon.ipynb, EDA, Training)
│   ├── .env.example
│   └── requirements.txt        # Dependensi library Python backend
│
├── frontend/                 # User Interface (React / Vite)
│   ├── src/
│   │   ├── components/         # Komponen UI (CardScanner, PriceChart, SignalBadge)
│   │   ├── App.jsx             # Komponen Utama Dashboard Web
│   │   └── main.jsx            # Entrypoint React Client
│   └── package.json            # Dependensi Node.js frontend
│
├── docs/                     # Dokumentasi proyek & konsep pendukung
│   └── PokeScan_Project_Documentation.md
│
├── .gitignore                # Filter venv, node_modules, cache, dan weights (.pt)
└── README.md                 # Dokumentasi Repositori GitHub
```

---

## 🚀 Cara Menjalankan Aplikasi

### 1. Persiapan Backend (Python)

1. Masuk ke folder `backend/`:
   ```bash
   cd backend
   ```
2. Buat dan aktifkan virtual environment (opsional tapi disarankan):
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
4. Jalankan Server API Backend:
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

## 📊 Sumber Data & Model Machine Learning

* **Metadatas & Histori Harga:** [pokemontcg.io API](https://pokemontcg.io/) (15.000+ data kartu & snapshot harga harian TCGPlayer & Cardmarket).
* **Model Deteksi Kondisi Fisik:** [Roboflow Universe — Card Grader Dataset](https://universe.roboflow.com/group-6-major-project/card-grader).


