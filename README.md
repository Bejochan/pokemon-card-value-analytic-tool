# Pokemon Card Value Analytic Tool (REGOKEMON) 🎴📊

> **Dashboard Analitika Data, Triple-Engine AI (Vision & Time-Series) & Estimasi Harga Wajar Kartu Pokémon untuk Marketplace**

[![Python](https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![OpenAI CLIP](https://img.shields.io/badge/Model_1-CLIP_ViT--B%2F32-412991?style=flat&logo=openai&logoColor=white)](https://github.com/mlfoundations/open_clip)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Index-00599C?style=flat&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![YOLO26s](https://img.shields.io/badge/Model_2-YOLO26s_800px-00FFFF?style=flat&logo=ultralytics&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![Amazon Chronos](https://img.shields.io/badge/Model_3-Amazon_Chronos--Bolt-FF9900?style=flat&logo=amazon&logoColor=white)](https://github.com/amazon-science/chronos-forecasting)
[![Supabase](https://img.shields.io/badge/Database-Supabase_Cloud-3ECF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![GitHub Actions](https://img.shields.io/badge/Cron_Job-Daily_Price_Tracker-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![API](https://img.shields.io/badge/Data_Source-pokemontcg.io-FFCB05?style=flat&logo=pokemon&logoColor=blue)](https://pokemontcg.io/)

---

## 📌 Ringkasan Proyek

**Pokemon Card Value Analytic Tool (REGOKEMON)** adalah sistem analitika data dan kecerdasan buatan berbasis **Triple-Engine AI & Prescriptive Analytics** yang dirancang untuk membantu penjual maupun pembeli kartu Pokémon pada **marketplace sekunder** (seperti Tokopedia, Shopee, eBay, TCGPlayer, atau komunitas kolektor lokal).

Sistem ini memecahkan 4 masalah fundamental dalam ekosistem perdagangan kartu koleksi (TCG):
1. **Identifikasi Kartu Otomatis Skala Masif (Model 1):** Mengidentifikasi jenis kartu secara instan di antara **20.617 jenis kartu** resmi menggunakan representasi semantik visual **OpenAI CLIP (ViT-B/32)**, pencarian vektor berkecepatan tinggi **FAISS**, dan verifikasi mikro **ORB**.
2. **Penilaian Cacat Fisik Otomatis (Model 2):** Mendeteksi dan melokalisasi kerusakan fisik permukaan kartu (*scratch*, *edge wear*, *corner wear*) pada tampak depan dan belakang menggunakan **YOLO26s (v6.1 - 800px)** dengan pipeline terisolasi (*perspective auto-alignment*, *rounded-card silhouette masking*, *veiling glare normalization*, *LAB CLAHE*, dan *cross-class NMS*).
3. **Peramalan Tren Deret Waktu & Sinyal Preskriptif (Model 3):** Memproyeksikan pergerakan harga 7 hari ke depan beserta pita ketidakpastian probabilistik (P10, P50, P90) dan menghasilkan sinyal trading preskriptif **BUY (Undervalued)**, **HOLD (Fair Market)**, atau **SELL (Overvalued)** menggunakan foundation model **Amazon Chronos-Bolt**.
4. **Valuasi Harga Pasar Wajar Dinamis:** Mengintegrasikan data harga historis dari Supabase Cloud dengan formula depresiasi kondisi fisik untuk menghasilkan estimasi nilai riil yang objektif.

---

## 🤖 Arsitektur Triple-Engine AI & Analytics

```mermaid
graph TD
    Input["Input Citra Kartu (Webcam HUD / HP DroidCam / Web Upload Dual-Side)"] --> CanvasResize["Client Canvas 1280px Resize (JPEG 0.88)<br/>Memangkas Payload 97% di Sisi Klien"]
    
    CanvasResize --> Split{"Pipeline Preprocessing Terpisah di RAM"}
    
    Split -->|Citra Alami 0px Margin| M1["MODEL 1: Card Identifier<br/>(OpenAI CLIP ViT-B/32 + FAISS IndexFlatIP)"]
    Split -->|Warp 63:88 + Margin 120px + Rounded Mask + CLAHE| M2["MODEL 2: Condition Grader<br/>(Local YOLO26s 800px + Two-Tier NMS)"]
    
    M1 -->|Top-8 Pool Kandidat| ORB["Hybrid Fast ORB Re-Ranking<br/>(Verifikasi Teks, Nomor Seri & Cap Set)"]
    ORB --> Sigmoid["Kalibrasi Keyakinan Sigmoid<br/>(Margin Scaling Temperature tau=0.03)"]
    Sigmoid --> CardID["Identitas Kartu Terverifikasi<br/>(ID, Nama, Set, Seri, Rarity, Harga Dasar)"]
    
    M2 --> ConditionScore["F_condition Multiplier<br/>(Depan & Belakang: Clean 1.0x, Scratched 0.85x, Edge/Corner 0.80x, Bent 0.65x)"]
    
    MemoryCache[("In-Memory Price Master RAM (0 ms)<br/>& Supabase Cloud Fallback")] --> CardID
    Supabase[("Supabase Cloud Database<br/>(20.617 Kartu & Price History)")] --> Hist["card_price_history<br/>(Riwayat Harga Harian Transaksi)"]
    
    Hist --> Resample["Calendar Daily Resampling<br/>(Forward-Fill Missing Trading Days)"]
    Resample --> M3["MODEL 3: Time-Series Forecaster<br/>(Amazon Chronos-Bolt Mini Foundation Model)"]
    M3 --> Forecast["Pita Kuantil 7 Hari (P10, P50, P90)<br/>& AI Dynamic Confidence Metric"]
    
    CardID --> Valuation["ANALYTICS ENGINE & FORMULA VALUASI<br/>P_final = P_base × M_variant × F_condition × F_market"]
    ConditionScore --> Valuation
    Forecast --> Valuation
    
    Valuation --> Output["Output Komprehensif:<br/>• Nilai Wajar Realistis (IDR & USD)<br/>• Proyeksi Kuantil 7 Hari (P10/P50/P90)<br/>• Sinyal Transaksi Preskriptif (BUY/HOLD/SELL)<br/>• Visual HUD & Grafik Tren Interaktif"]
```

---

### 1️⃣ Model 1: Card Identification Engine (CLIP ViT-B/32 + FAISS + ORB)

* **Backbone:** Vision Transformer **`openai/clip-vit-base-patch32` (`ViT-B/32`)** pra-latih pada 400 juta pasangan citra-teks.
* **Mengapa Vision Transformer (ViT), Bukan CNN Konvensional?**
  * **Global Self-Attention:** ViT membagi citra menjadi 49 patch (7 × 7 grid berukuran 32 × 32 px) dan memproses korelasi visual secara serentak. Model menghubungkan posisi teks nama, simbol energi, dan ilustrasi karakter secara menyeluruh.
  * **Open-Set Metric Learning:** Tidak menggunakan layer klasifikasi *Softmax* yang kaku (20.000 kelas). Kartu baru cukup diekstrak vektor 512-D-nya dan dimasukkan ke indeks FAISS dalam hitungan detik tanpa perlu *retraining* model.
  * **Ketahanan Optik (Robustness):** Sangat tahan terhadap pantulan cahaya (*glare*) dari pelindung plastik (*sleeve*), sudut miring, dan variasi pencahayaan ruangan.
* **Vector Indexing (FAISS IndexFlatIP):**
  * Seluruh 20.617 kartu disimpan dalam format vektor 512 float32 ternormalisasi L2 (`card_embeddings.index`, ukuran RAM hanya ~42 MB).
  * Menghitung *Cosine Similarity* secara paralel dalam waktu sub-milidetik (< 1 ms).
* **Two-Stage Re-Ranking (Fast ORB Keypoints):**
  * Kartu Pokémon memiliki kasus unik berupa **kartu reprint** (artwork karakter sama persis, tetapi beda nomor seri dan simbol set di bagian bawah).
  * Sistem menyaring kandidat teratas melalui FAISS, lalu mengekstrak fitur lokal mikro menggunakan **ORB (500 keypoints)** dengan bobot gabungan:
    ```
    Score_blended = 0.60 × Score_CLIP + 0.40 × Score_ORB
    ```
  * **Optimalisasi Pool Size 8:** Menggunakan pool top-8 untuk verifikasi mikro ORB yang terbukti mempertahankan akurasi 93,8% sekaligus menghemat latensi disk I/O >1.000 ms dibandingkan evaluasi 100 pool.
* **Kalibrasi Margin Sigmoid:**
  * Menghitung selisih margin skor ke *runner-up* kartu dengan nama berbeda (Δ), lalu diskalakan dengan temperatur τ = 0.03:
    ```
    P = 100 / (1 + exp(-Δ / τ))
    ```
  * Menghindari *overconfidence* pada varian kartu yang mirip.
* **Optimalisasi Throughput & Latensi Tinggi:**
  * **Client-Side Canvas 1280px Pre-Resizing:** Browser otomatis mengompresi foto mentah smartphone (10–15 MB) menjadi ~150–300 KB tanpa kehilangan fitur penting, memangkas waktu transfer HTTP sebesar 97%.
  * **Zero-Latency In-Memory Price Resolution (0 ms):** Mengutamakan pencarian harga dari master dataset RAM (20.617 kartu), melenyapkan jeda jaringan Supabase 300–800 ms.
  * **Background Pre-Warming:** Memuat dan memanaskan bobot CLIP dan YOLO saat server FastAPI booting, melenyapkan *cold-start* bagi pengguna.
  * **Offline Mode Isolation:** Mengunci `HF_HUB_OFFLINE=1` untuk mencegah handshake remote ke server Hugging Face saat model diinisialisasi.
* **3 Varian Interface Model 1:**
  1. **`card_identifier_realtime.py` (Live Scanner HUD 30+ FPS):** Menggunakan arsitektur *Multithreaded Asynchronous Worker* (thread rendering kamera dipisah dari thread inferensi AI), *In-Memory ORB Cache*, dan *Temporal Smoothing* (buffer 7-frame konsensus). Latensi: **~83 ms di CPU** dan **~18 ms di GPU RTX 2050**.
  2. **`card_identifier_oncam.py` (Snapshot Camera):** Membuka webcam/IP Cam dengan tombol capture manual dan visualisasi target box.
  3. **`card_identifier_manual.py` (File Evaluasi Presisi):** Evaluasi foto statis melalui File Explorer atau CLI dengan Full 4-Way Auto-Orientation & Dual-View (Portrait + Square).
* **Dokumentasi Lengkap:** Pelajari arsitektur dan perbandingan performa di [`docs/clip_model_architecture_and_rationale.md`](docs/clip_model_architecture_and_rationale.md).

---

### 2️⃣ Model 2: Card Condition Grader (Local YOLO26s 800px & Dual-Side Defect Inspection)

* **Tujuan:** Mendeteksi, melokalisasi, dan mengukur tingkat keparahan cacat fisik kartu secara objektif untuk penentuan grade kondisi fisik dan diskon harga.
* **Arsitektur Model:**
  * **Model Utama (`models/best-model-v6-card-condition.pt`):** Menggunakan arsitektur **YOLO26s** dengan resolusi inferensi native **800px** (`imgsz=800`). Dilatih dengan augmentasi *tuned scale* dan penyeimbangan loss (`box=7.5`, `cls=1.2`), menghasilkan performa benchmark tertinggi (**mAP50 = 0.4277**, *Corner Wear* 0.602, *Edge Wear* 0.087, *Card* 0.995).
  * **Fallback Otomatis (`models/best-model-v5-card-condition.pt`):** Fallback otomatis ke bobot Model V5 (YOLO11s) jika bobot V6 tidak tersedia.
  * **Cloud Fallback:** Terintegrasi dengan endpoint Roboflow Cloud Inference API (`card-grader`) sebagai cadangan jaringan opsional.
* **Pipeline Preprocessing Terpisah (Dedicated In-Memory Pipeline):**
  Untuk menjaga integritas Model 1, Model 2 mengeksekusi pipeline terpisah di memori RAM tanpa mengubah citra input asli:
  1. **Perspective Alignment & Auto-Crop (`auto_detect_card`):** Mendeteksi 4 sudut kartu dan melakukan *perspective warp* ke rasio standar 63:88 (600×837 px) ditambah **margin luar 120 px** (`(20, 20, 22)`) agar aus tepi dan sudut dapat dideteksi secara akurat.
  2. **Rounded-Card Silhouette Masking:** Menerapkan mask bentuk kartu asli dengan radius sudut lengkung 3,2 mm (standar kartu Pokémon) pada foto berlatar terang/putih, melenyapkan segitiga putih di 4 sudut luar yang dapat memicu *false positive*.
  3. **Veiling Glare Normalization:** Mengoreksi *black-point* yang terangkat akibat pantulan latar putih secara adaptif sebelum CLAHE agar kontras warna biru/tepi kartu tetap pekat.
  4. **Adaptive Unsharp Masking & LAB CLAHE (`enhance_card_for_defect`):** Memeriksa variansi Laplacian (`sharpness < 70`); citra yang agak *soft/blur* ditajamkan secara kondisional, lalu ditingkatkan kontras lokalnya via CLAHE (*clipLimit=2.5*, *tileGridSize=8×8*) pada kanal L di ruang warna LAB.
  5. **Two-Tier NMS Deduplication:** Mengombinasikan NMS per-kelas (`iou_threshold=0.4`) dan NMS lintas-kelas (`cross_class_iou=0.75`) untuk mencegah kotak *bounding box* bertumpuk pada sudut atau tepi yang sama.
* **Dual-Side Inspection (Tampak Depan & Tampak Belakang):**
  * Mendukung inspeksi cacat pada kedua sisi kartu (`detect_card_defects_dual_side`). Cacat di sisi belakang (seperti goresan *Poké Ball*, *edge whitening*, dan kikisan sudut) terintegrasi langsung ke dalam laporan kondisi akhir.
* **Kelas Cacat Fisik & Pengali Depresiasi (F_condition):**
  * Model YOLO mendeteksi 4 kelas utama: `Card`, `Corner Wear`, `Edge Wear`, dan `Scratch`.
  * `Clean / Mint (Mulus)` → Multiplier = **1.00** *(Diskon 0% : Near Mint / Mint)*
  * `Scratched (Goresan Permukaan)` → Multiplier = **0.85** *(Diskon 15% : Lightly Played)*
  * `Edge Wear / Corner Wear (Kikis Tepi / Sudut)` → Multiplier = **0.80** *(Diskon 20% : Moderately Played)*
  * `Bent / Crease (Lipatan / Tekukan)` → Multiplier = **0.65** *(Diskon 35% : Heavily Played, aturan penalti struktural)*
  * `Akumulasi Cacat Ganda` → Multiplier akumulatif dengan batas bawah (*floor*) = **0.40** *(Diskon hingga 60% : Damaged)*
* **Dokumentasi Lengkap:** Pelajari arsitektur dan evaluasi performa di [`docs/yolo_model_architecture_and_rationale.md`](docs/yolo_model_architecture_and_rationale.md).

---

### 3️⃣ Model 3: Industrial Time-Series Forecasting (Amazon Chronos-Bolt Mini)

* **Backbone:** Time-Series Foundation Model **`amazon/chronos-bolt-mini`** (AWS Research, 2024) berbasis arsitektur Transformer Encoder-Decoder (T5).
* **Mengapa Foundation Model Deret Waktu, Bukan Pendekatan Klasik?**
  * **Zero-Shot Pre-Trained:** Chronos-Bolt telah dipra-latih pada miliaran titik data deret waktu sintetis dan riil lintas domain industri. Model mampu mengenali tren harga dan volatilitas tanpa perlu *fine-tuning* manual per-kartu.
  * **Probabilistic Quantile Ribbons (P10, P50, P90):** Alih-alih tebakan angka tunggal (*point estimate*), Chronos-Bolt menghasilkan rentang kuantil probabilistik:
    * **P10 (Pessimistic Floor):** Batas bawah harga jika terjadi aksi jual atau koreksi likuiditas.
    * **P50 (Median Baseline):** Estimasi harga paling mungkin di masa depan.
    * **P90 (Optimistic Ceiling):** Batas atas harga jika minat beli melonjak.
  * **Kecepatan Inferensi Sub-Detik (~30 ms):** Menggunakan *direct multi-step patch prediction*, Chronos-Bolt Mini memproyeksikan seluruh cakrawala 7 hari secara serentak tanpa akumulasi eror autoregresif.
* **Pipeline Standardisasi Kalender Harian (Daily Forward-Fill Resampling):**
  * Mengisi celah hari transaksi yang kosong dengan metode *forward-fill* (`ffill`) pada frekuensi harian `D`, memastikan deret waktu teratur sebelum diproses oleh model Transformer.
* **Logika Keputusan Pasar Preskriptif (Dynamic Trading Tunnel):**
  * Membandingkan harga listing penjual saat ini terhadap rentang kuantil dinamis H+1:
    * `Listing Price < P10(H+1)` → **BUY (Undervalued)** : Peluang beli di bawah lantai harga wajar.
    * `P10(H+1) <= Listing Price <= P90(H+1)` → **HOLD (Fair Market)** : Harga berada dalam toleransi wajar pasar.
    * `Listing Price > P90(H+1)` → **SELL (Overvalued)** : Harga listing terlalu mahal di atas batas atas wajar.
* **Metrik Keyakinan AI Dinamis (Confidence Metric):**
  * Dihitung matematis dari rasio dispersi: `Spread Ratio = (P90 - P10) / P50`. Jika pita sempit, AI Confidence tinggi (~95%); jika pasar bergejolak liar, pita melebar dan confidence turun secara transparan.
* **Dokumentasi Lengkap:** Pelajari arsitektur dan justifikasi teknis di [`docs/chronos_model_architecture_and_rationale.md`](docs/chronos_model_architecture_and_rationale.md).

---

### 4️⃣ Formula Valuasi Harga Wajar Dinamis

```
P_final = P_base × M_variant × F_condition × F_market
```

* **P_base:** Harga pasar efektif konsolidasi TCGPlayer & Cardmarket dari Supabase Cloud.
* **M_variant:** Pengali vintage edisi khusus era awal Wizards of the Coast (rilis sebelum tahun 2005: +20%).
* **F_condition:** Pengali kondisi fisik objektif dari Model 2 YOLO (1.00x hingga floor 0.40x).
* **F_market:** Pengali kondisi pasar transaksi (default 1.00; disiapkan untuk diferensiasi kemasan/bahasa).

---

## ⚡ Tolak Ukur Kuantitatif & Benchmark Komputasi

| Parameter Evaluasi | Nilai Benchmark | Catatan Implementasi |
|---|:---:|---|
| **Latensi Upload Manual Web** | **~1.000 – 1.400 ms** | Integrasi penuh (Canvas 1280px + Model 1 CLIP + Model 2 YOLO26s + Valuasi) |
| **Ukuran Payload Foto Klien** | **150 – 300 KB** | HTML5 Canvas JPEG 0.88 (dipangkas ~97% dari 10–15 MB) |
| **Akurasi Pengenalan Kartu Riil (Model 1)** | **93,8%** | Uji empiris foto manual smartphone (15/16 kartu teridentifikasi tepat) |
| **mAP50 Deteksi Cacat Fisik (Model 2)** | **0.4277 (42,77%)** | YOLO26s 800px Tuned (Tertinggi di antara V3 0.4095 dan V5 0.4048) |
| **Pencarian Harga Pasar (In-Memory)** | **0,00 ms** | Akses instan dari master CSV 20.617 kartu di RAM (Zero-Latency) |
| **Latensi Inferensi Model 1 (GPU RTX 2050)** | **~18 ms** | CUDA PyTorch Tensor Stream (`card_identifier_realtime.py`) |
| **Latensi Inferensi Model 1 (CPU Optimized)** | **~83 ms** | Single-View + In-Memory ORB Descriptor Caching |
| **Pencarian Indeks Vektor FAISS** | **< 1 ms** | `IndexFlatIP` untuk 20.617 kartu (~42 MB RAM) |
| **Latensi Inferensi Model 3 Chronos-Bolt (GPU)** | **~25 - 35 ms** | Peramalan kuantil 7 hari per kartu (`chronos_forecaster.py`) |
| **Latensi Inferensi Model 3 Chronos-Bolt (CPU)** | **~180 ms** | Standalone inference tanpa akselerasi CUDA |
| **Frame Rate Kamera Live** | **30+ FPS** | Stabil berkat pemisahan *Asynchronous Worker Thread* |
| **Dimensi Representasi Vektor** | **512 Dimensi** | L2-Normalized Hypersphere Embeddings (CLIP ViT-B/32) |
| **Ukuran Dataset Katalog** | **20.617 Kartu** | Database resmi pokemontcg.io (1999–2026) |
| **Cakrawala Peramalan (Horizon)** | **7 Hari (H+1 s/d H+7)** | Proyeksi multi-kuantil P10, P50, P90 |
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
| **Median Harga Pasar** | **$0,96 (~Rp14.880)** | 50% kartu Pokémon bernilai <= $1 USD (*Right-Skewed*) |

> [!TIP]
> Dokumentasi teknis rinci mengenai arsitektur model, spesifikasi API, variabel data, dan skema SQL:
> * 📄 [`docs/clip_model_architecture_and_rationale.md`](docs/clip_model_architecture_and_rationale.md) : Arsitektur & rasional teknis Model 1 (CLIP ViT-B/32 + FAISS + ORB).
> * 📄 [`docs/yolo_model_architecture_and_rationale.md`](docs/yolo_model_architecture_and_rationale.md) : Arsitektur & rasional teknis Model 2 (Local YOLO26s 800px Condition Grader).
> * 📄 [`docs/chronos_model_architecture_and_rationale.md`](docs/chronos_model_architecture_and_rationale.md) : Arsitektur & rasional teknis Model 3 (Amazon Chronos-Bolt Mini).
> * 📄 [`docs/api_specification.md`](docs/api_specification.md) : Spesifikasi teknis 14 REST API endpoints, kontrak payload & schema.
> * 📄 [`docs/dataset_dictionary.md`](docs/dataset_dictionary.md) : Kamus data 22 variabel CSV.
> * 📄 [`docs/dataset_summary_and_metrics.md`](docs/dataset_summary_and_metrics.md) : Ringkasan statistik & metrik teknis.
> * 📄 [`docs/supabase_database_dictionary.md`](docs/supabase_database_dictionary.md) : Skema database PostgreSQL Supabase.
> * 📄 [`docs/schema.sql`](docs/schema.sql) : Script DDL pembuatan tabel database.

---

## 🏗️ Struktur Repositori

```text
pokemon-card-value-analytic-tool/
├── .github/
│   └── workflows/
│       └── daily_price_cron.yml          # GitHub Actions cron pelacak harga harian otomatis
│
├── backend/                              # Backend Python, Database, & AI Engine
│   ├── app/                              # Modular REST API (FastAPI)
│   │   ├── main.py                       # Server Entrypoint (/identify, /analyze, /cards, /sets, /forecast, /dashboard)
│   │   ├── cv_service.py                 # In-Memory Bridge (Model 1 CLIP + Model 2 YOLO26s Dual-Side & Preprocessing Terpisah)
│   │   ├── analytics_engine.py           # Formula Valuasi Harga Wajar, Chronos Forecaster, & Sinyal Pasar
│   │   ├── currency_service.py           # Layanan sinkronisasi kurs USD ke IDR dengan fallback rate
│   │   └── schemas.py                    # Skema validasi Pydantic (Request, Response, Forecast, Pricing)
│   │
│   ├── dataset/                          # Master Data & Asset Citra
│   │   ├── pokemon_cards_dataset_cleaned.csv  # Dataset Bersih (20.617 baris, 22 kolom)
│   │   ├── pokemon_cards_dataset_cleaned.json # Dataset JSON (20.617 entitas kartu)
│   │   ├── compressed_images/            # 20.617 gambar JPG 640x640 Lanczos terkompresi
│   │   ├── val_samples/                  # Sampel gambar validasi pengujian lokal
│   │   └── card_condition_dataset.yaml   # Konfigurasi kelas defect YOLO
│   │
│   ├── models/                           # Model AI & Engine Identifikasi
│   │   ├── best-model-v6-card-condition.pt # Bobot PyTorch utama YOLO26s (800px tuned) Condition Grader
│   │   ├── best-model-v5-card-condition.pt # Bobot PyTorch fallback YOLO11s Condition Grader
│   │   ├── card_condition.py             # Engine & CLI Tester Model 2 (Auto-Alignment, Rounded Masking, CLAHE, NMS)
│   │   ├── card_identifier.py            # Engine Utama Model 1 (CLIP + FAISS + Top-8 ORB + Sigmoid)
│   │   ├── card_identifier_realtime.py   # Live Scanner HUD 30+ FPS (Asynchronous Worker Thread)
│   │   ├── card_identifier_oncam.py      # Pemindai Snapshot Kamera Interaktif
│   │   ├── card_identifier_manual.py     # Pengujian Foto Statis (GUI File Explorer / CLI)
│   │   ├── card_condition_grader.py      # Engine Model 2 (Roboflow YOLO Defect Detection fallback)
│   │   ├── chronos_forecaster.py         # Engine Model 3 (Amazon Chronos-Bolt Mini Time-Series Forecaster)
│   │   ├── build_card_index.py           # Generator Vektor Indeks FAISS resmi (CLIP ViT-B-32)
│   │   ├── calibrate_confidence.py       # Kalibrasi temperatur sigmoid margin confidence (tau=0.03)
│   │   ├── live_card_condition_test.py   # Skrip pengujian deteksi cacat secara on-cam
│   │   ├── card_embeddings.index         # Binary Indeks FAISS (512-dim, 20.617 kartu, ~42 MB)
│   │   ├── card_id_map.json              # Pemetaan indeks FAISS ke card_id resmi
│   │   └── legacy_mobilenet/             # [Arsip] Baseline MobileNetV3 untuk studi komparasi
│   │
│   ├── notebooks/                        # Eksplorasi Analisis Data (11 Jupyter Notebooks)
│   │   ├── analitik_harga_kartu_pokemon.ipynb      # Analisis pergerakan harga & distribusi kelangkaan
│   │   ├── eda_condition_card_roboflow.ipynb       # Eksplorasi dataset Roboflow Card Grader
│   │   ├── eda_heatmap.ipynb                       # Korelasi fitur dan matriks panas data pasar
│   │   ├── eda_pokemon_images.ipynb                # Inspeksi dimensi, rasio, dan kualitas gambar kartu
│   │   ├── eda_pokemon_json.ipynb                  # Ekstraksi dan pemetaan struktur JSON pokemontcg.io
│   │   ├── eda_research_tcg.ipynb                  # Visualisasi distribusi data & pemodelan awal
│   │   ├── forecasting_model.ipynb                 # Eksperimen peramalan deret waktu & regresi tabular
│   │   ├── model_comparison_card_identifier.ipynb  # Komparasi akurasi MobileNetV3 vs CLIP ViT-B-32
│   │   ├── test_card_condition_grader.ipynb        # Pengujian deteksi cacat Roboflow fallback
│   │   ├── test_card_condition_retrain.ipynb       # Pelatihan ulang dan evaluasi mAP model YOLO
│   │   └── valuation_analytics.ipynb               # Analisis mendalam formula valuasi & pasar
│   │
│   ├── seed_supabase.py                  # Seeding dataset bersih ke Supabase Cloud
│   ├── daily_price_tracker.py            # Sinkronisasi harga harian dari pokemontcg.io
│   ├── fetch_pokemon_data.py             # Script unduh katalog mentah dari pokemontcg.io v2 API
│   ├── clean_csv_broken_links.py         # Pembersihan tautan CDN yang mati (53 link)
│   ├── export_broken_links.py            # Export audit laporan broken links
│   ├── compress_images.py                # Kompresi paralel gambar ke format JPG Lanczos
│   ├── test_api_endpoints.py             # Uji integrasi endpoint REST API
│   ├── test_realtime_simulation.py       # Simulasi pemindaian kamera real-time
│   ├── requirements.txt                  # Dependensi Python Backend
│   └── .env                              # Konfigurasi API Keys & CAMERA_SOURCE
│
├── frontend/                             # Single Page Application (React 19 + Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPage.jsx            # Pemindai Langsung (Live HUD, Camera Selector, Guide-Box Crop) & Upload Inspeksi Foto Statis
│   │   │   ├── ScannerDashboard.jsx      # Detail Valuasi & Hasil Inspeksi (Riwayat Harga, Proyeksi Chronos, Grade Cacat Fisik)
│   │   │   ├── CatalogPage.jsx           # Katalog Interaktif 20.617 Kartu Resmi (Filter Set, Search, Sort, Kurs USD/IDR)
│   │   │   ├── DashboardPage.jsx         # Analitika Pasar, Distribusi Kelangkaan, Leaderboard Karakter & Tren Historis
│   │   │   ├── Marketplace.jsx           # Simulasi Marketplace Sekunder, Keranjang Transaksi & Integrasi Valuasi Wajar
│   │   │   ├── HeroSection.jsx           # Landing Viewport Interaktif
│   │   │   └── Navbar.jsx                # Navigasi Global & Sinkronisasi URL Hash
│   │   ├── config/
│   │   │   └── api.js                    # Konfigurasi Dinamis Endpoint Backend API
│   │   ├── App.jsx                       # Routing SPA Berbasis Hash (#home, #upload, #result, #catalog, #dashboard, #marketplace)
│   │   └── main.jsx                      # Entrypoint React
│   └── package.json                      # Dependensi Node.js
│
├── docs/                                 # Dokumentasi Teknis Lengkap
│   ├── clip_model_architecture_and_rationale.md    # Arsitektur & Analisis Model 1 (CLIP ViT-B-32 + FAISS + ORB)
│   ├── yolo_model_architecture_and_rationale.md    # Arsitektur & Analisis Model 2 (YOLO26s 800px Condition Grader)
│   ├── chronos_model_architecture_and_rationale.md # Arsitektur & Analisis Model 3 (Amazon Chronos-Bolt Mini)
│   ├── api_specification.md              # Spesifikasi 14 REST API Endpoints & Kontrak Data
│   ├── dataset_dictionary.md             # Kamus Data 22 Variabel CSV
│   ├── dataset_summary_and_metrics.md    # Statistik & Metrik Dataset Master
│   ├── supabase_database_dictionary.md   # Dokumentasi Database Supabase
│   └── schema.sql                        # Script DDL Relasional Database
├── vercel.json                           # Konfigurasi deployment frontend Vercel
└── README.md                             # Dokumentasi Utama Proyek
```

---

## 🚀 Panduan Menjalankan Sistem

### Persyaratan Awal:
* **Python 3.10 – 3.12** dengan virtual environment (`.venv`).
* **Node.js 18+** & npm.
* Kamera laptop atau Kamera HP melalui aplikasi **DroidCam**.

---

### 1. Menjalankan Live Scanner HUD (Real-Time 30+ FPS)

Mode ini adalah demonstrasi visual utama Model 1:
```powershell
# Jalankan dengan environment Python aktif:
python backend/models/card_identifier_realtime.py
```
* **Kamera HP (DroidCam):** Atur variabel `CAMERA_SOURCE=http://<IP_HP>:4747/video` di `backend/.env`.
* **Webcam Laptop:** Atur `CAMERA_SOURCE=0` di `backend/.env`.
* **Shortcut Keyboard saat HUD Berjalan:**
  * `[Spasi]` : Freeze / Unfreeze frame pemindaian.
  * `[M]` : Toggle mode Fullscreen.
  * `[R]` : Rotasi orientasi tampilan (0° / 90° / 180° / 270°).
  * `[F]` : Mengirim sinyal Autofokus ke kamera HP.
  * `[Q]` : Keluar dari aplikasi.

---

### 2. Pengujian Model 2 Condition Grader (CLI & Visual Window)

Untuk menguji deteksi cacat fisik tampak depan dan belakang secara mandiri menggunakan YOLO26s (800px):
```powershell
python backend/models/card_condition.py "path/ke/foto_depan.jpg" "path/ke/foto_belakang.jpg"
```
* Skrip akan otomatis meluruskan kartu (*perspective alignment*), mengaplikasikan *rounded mask* dan CLAHE, mendeteksi cacat fisik dengan NMS, serta menampilkan jendela OpenCV visualisasi dua sisi berdampingan.

---

### 3. Menjalankan Backend Server (FastAPI)

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
* Server berjalan di: `http://127.0.0.1:8000`
* Dokumentasi Interaktif (Swagger UI): `http://127.0.0.1:8000/docs`
* **Endpoints Utama:**
  * `POST /identify` : Identifikasi cepat Model 1 On-Cam (Base64 citra kamera).
  * `POST /upload/identify` : Versi Multipart Form-Data untuk identifikasi Model 1.
  * `POST /analyze` : Analisis lengkap citra statis (Model 1 CLIP + Model 2 YOLO26s depan & belakang + Valuasi harga wajar).
  * `POST /upload/analyze` : Versi Multipart Form-Data untuk analisis lengkap dual-side.
  * `GET  /cards` : Katalog kartu Pokémon (mendukung parameter `search`, `supertype`, `rarity`, `set_id`, `sort_by`, `page`, `limit`).
  * `GET  /sets` : Daftar seluruh set kartu untuk filter dropdown.
  * `GET  /cards/{card_id}/history` : Riwayat tren harga harian untuk grafik pasar.
  * `GET  /cards/{card_id}/forecast` : Proyeksi harga kuantil 7 hari (P10, P50, P90) dan sinyal preskriptif via Amazon Chronos-Bolt.
  * `POST /cards/{card_id}/condition` : Deteksi cacat fisik kartu mandiri via YOLO (Base64).
  * `POST /upload/cards/{card_id}/condition` : Deteksi cacat fisik kartu mandiri via Multipart Form-Data.
  * `GET  /dashboard` : Statistik agregat pasar, pergerakan tren, dan kartu terpopuler.
  * `GET  /currency` : Status kurs live USD ke IDR dan waktu pembaruan terakhir.
  * `GET  /health` : Healthcheck status server.

---

### 4. Menjalankan Frontend Web Portal (React + Vite)

Buka terminal baru:
```powershell
cd frontend
npm install
npm run dev
```
Buka browser di: **`http://localhost:5173`**
* **Navigasi Halaman:**
  * **HOME (`#home`):** Tampilan beranda interaktif dengan visualisasi aset dan pintasan akses cepat pemindai kartu.
  * **PEMINDAI LANGSUNG / UPLOAD (`#upload`):** Pindai kartu fisik langsung via webcam atau kamera smartphone (fitur pemilih kamera eksternal/DroidCam, dynamic guide-box crop, sensor fokus Laplacian, dan buffer konsensus) atau unggah foto tampak depan dan belakang untuk inspeksi cacat fisik komprehensif via YOLO26s.
  * **HASIL VALUASI (`#result`):** Rincian penilaian kartu, grafik tren harga historis, peramalan probabilistik 7 hari Amazon Chronos-Bolt (P10, P50, P90), laporan cacat fisik dua sisi, dan rekomendasi preskriptif (BUY / HOLD / SELL).
  * **CATALOG (`#catalog`):** Eksplorasi 20.617 kartu resmi dengan filter set kronologis, pencarian nama, filter supertype/rarity, serta konversi kurs otomatis USD dan IDR.
  * **DASHBOARD (`#dashboard`):** Analitika pasar, distribusi kelangkaan populasi riil, analisis korelasi atribut terhadap harga pasar, dan leaderboard karakter bernilai tinggi.
  * **MARKETPLACE (`#marketplace`):** Simulasi transaksi marketplace sekunder dengan integrasi valuasi nilai pasar wajar secara real-time.

---

### 5. Pengujian Model & Skrip Tambahan

* **Uji Peramalan Amazon Chronos-Bolt:**
  ```powershell
  python backend/models/chronos_forecaster.py
  ```
* **Uji Foto Manual (GUI File Explorer):**
  ```powershell
  python backend/models/card_identifier_manual.py
  ```
* **Membangun Ulang Indeks Vektor FAISS:**
  ```powershell
  python backend/models/build_card_index.py
  ```
* **Jalankan Pelacak Harga Harian:**
  ```powershell
  python backend/daily_price_tracker.py
  ```

---

## 📜 Lisensi & Atribusi

* **Metadata Kartu & Harga Pasar:** [pokemontcg.io REST API](https://pokemontcg.io/)
* **Vision Transformer Backbone (Model 1):** [OpenAI CLIP (OpenCLIP)](https://github.com/mlfoundations/open_clip)
* **Dataset Cacat Fisik (Model 2):** [Roboflow Universe: Card Grader Dataset](https://universe.roboflow.com/)
* **Dataset Referensi Tambahan (Model 2):** [GemSnipe Pokemon Centering Measurements](https://gemsnipe.com/) (Open-Source CC BY 4.0 via Contributor Issue #1)
* **Time-Series Foundation Model (Model 3):** [Amazon Chronos-Bolt (AWS Research)](https://github.com/amazon-science/chronos-forecasting)
* **Vector Retrieval Engine:** [Meta AI FAISS](https://github.com/facebookresearch/faiss)
* **Cloud Database:** [Supabase PostgreSQL](https://supabase.com/)
