# 📡 Spesifikasi Teknis REST API Regokemon
## Dokumentasi Lengkap Endpoint, Kontrak Payload, dan Skema Data

> **Pokemon Card Value Analytic Tool (REGOKEMON) : API Reference**  
> **Server Engine:** FastAPI (Python 3.10 - 3.12, Uvicorn ASGI)  
> **Base URL Lokal:** `http://127.0.0.1:8000`  
> **Versi API:** `3.1.0`  
> **Dokumentasi Interaktif:** `/docs` (Swagger UI) & `/redoc` (ReDoc)  
> **Kebijakan CORS:** Whitelist asal terpercaya (`http://localhost:5173`, `http://localhost:3000`, `http://localhost:8000`), regex subdomain Vercel (`https://*.vercel.app`), dan konfigurasi variabel lingkungan `ALLOWED_ORIGINS`.  
> **Proteksi Keamanan:** Batas ukuran payload maksimum 15 MB (File & Base64) serta *in-memory sliding window rate limiting* terpisah: **300 req/menit** untuk endpoint scanner kamera ringan (`/identify`, `/upload/identify`) dan **60 req/menit** untuk endpoint AI berat (`/analyze`, `/forecast`, `/condition`).  

---

## 📌 Daftar Isi
1. [Ikhtisar Arsitektur API](#1-ikhtisar-arsitektur-api)
2. [Konfigurasi Base URL, Keamanan, & Environment](#2-konfigurasi-base-url-keamanan--environment)
3. [Daftar Lengkap Endpoint REST API](#3-daftar-lengkap-endpoint-rest-api)
4. [Spesifikasi Rinci per Endpoint](#4-spesifikasi-rinci-per-endpoint)
   - [A. Layanan Status & Healthcheck](#a-layanan-status--healthcheck)
   - [B. Layanan Computer Vision & Identifikasi Kartu](#b-layanan-computer-vision--identifikasi-kartu)
   - [C. Layanan Katalog & Eksplorasi Data](#c-layanan-katalog--eksplorasi-data)
   - [D. Layanan Analitika Deret Waktu & Peramalan](#d-layanan-analitika-deret-waktu--peramalan)
   - [E. Layanan Penilaian Kondisi Fisik Standalone](#e-layanan-penilaian-kondisi-fisik-standalone)
   - [F. Layanan Dashboard & Valuta Asing](#f-layanan-dashboard--valuta-asing)
5. [Skema Objek Data Bersama (Shared Schemas)](#5-skema-objek-data-bersama-shared-schemas)
6. [Standar Penanganan Error (HTTP Status Codes)](#6-standar-penanganan-error-http-status-codes)

---

## 🌐 1. Ikhtisar Arsitektur API

REST API Regokemon dirancang menggunakan framework **FastAPI** dengan arsitektur asinkron berbasis ASGI (*Asynchronous Server Gateway Interface*). API ini bertindak sebagai jembatan terpadu antara antarmuka pengguna (React Single Page Application) dengan tiga engine komputasi AI dan sistem data:
1. **Model 1 Engine:** Ekstraksi embedding visual OpenAI CLIP (ViT-B/32), pencarian vektor FAISS IndexFlatIP (20.617 kartu), dan verifikasi mikro ORB Re-Ranking.
2. **Model 2 Engine:** Deteksi cacat fisik lokal YOLO26s (800px) untuk tampak depan dan belakang kartu (`best-model-v6-card-condition.pt`).
3. **Model 3 Engine:** Peramalan deret waktu probabilistik Amazon Chronos-Bolt Mini (Pita Kuantil P10, P50, P90).
4. **Analytics Engine:** Formula valuasi harga wajar pasar dinamis, Offline CSV Fallback otomatis, dan sinkronisasi kurs live USD ke IDR.

---

## ⚙️ 2. Konfigurasi Base URL, Keamanan, & Environment

### Base URL
* **Lingkungan Pengembangan Lokal:** `http://127.0.0.1:8000`
* **Frontend Client Config:** [`frontend/src/config/api.js`](../frontend/src/config/api.js) membaca variabel lingkungan `VITE_API_BASE_URL`.

### Kebijakan Keamanan (Security Hardening)
1. **CORS Whitelist Terbatas:**
   * Menolak wildcard tidak aman `*` saat menggunakan credentials.
   * Default origins: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:8000`, `http://127.0.0.1:8000`.
   * Mendukung regex subdomain Vercel: `^https:\/\/.*\.vercel\.app$`.
   * Mendukung domain kustom melalui variabel lingkungan `ALLOWED_ORIGINS` (dipisahkan tanda koma).
2. **Pembatasan Ukuran Unggahan (Payload Size Limit):**
   * Berkas multipart maksimum: **15 MB** (`MAX_FILE_SIZE_BYTES = 15.728.640 bytes`).
   * String Base64 maksimum: **22 MB karakter** (~15 MB data biner citra).
   * Pelanggaran ukuran menghasilkan respons **HTTP 413 Payload Too Large**.
3. **Rate Limiting Terpisah (Sliding Window):**
   * **Jalur Scanner Kamera Ringan (`identify`):** `/identify` dan `/upload/identify` (CLIP ViT-B/32 sub-milidetik) dilindungi dengan kuota default **300 request per menit per IP** (`RATE_LIMIT_IDENTIFY_PER_MINUTE`) agar *realtime streaming* kamera tidak terputus HTTP 429.
   * **Jalur AI Berat (`heavy`):** `/analyze`, `/upload/analyze`, `/cards/{card_id}/forecast`, `/cards/{card_id}/condition`, dan `/upload/cards/{card_id}/condition` dilindungi dengan kuota default **60 request per menit per IP** (`RATE_LIMIT_AI_PER_MINUTE`).
   * Pelanggaran laju menghasilkan **HTTP 429 Too Many Requests** disertai header standar `Retry-After: <detik>`.
4. **Offline Resilience (Ketahanan Offline):**
   * Seluruh endpoint katalog (`/cards`, `/sets`, `/cards/{id}/history`, `/dashboard`) otomatis fallback ke data master lokal (`backend/dataset/pokemon_cards_dataset_cleaned.csv`) melalui `offline_service.py` jika koneksi ke Supabase terputus.

---

## 📋 3. Daftar Lengkap Endpoint REST API

| No | Metode | Endpoint | Deskripsi Ringkas | Tipe Payload | Proteksi AI / Limit |
| :---: | :---: | :--- | :--- | :---: | :---: |
| 1 | `GET` | `/` | Informasi status layanan, versi API, dan daftar endpoint | Tidak Ada | Bebas |
| 2 | `GET` | `/health` | Healthcheck kesiapan engine AI, database, dan kurs | Tidak Ada | Bebas |
| 3 | `POST` | `/identify` | Identifikasi cepat Model 1 On-Cam (Live Camera HUD) | JSON (Base64) | 15 MB / 300 req/menit |
| 4 | `POST` | `/upload/identify` | Identifikasi cepat Model 1 On-Cam versi berkas multipart | Multipart Form | 15 MB / 300 req/menit |
| 5 | `POST` | `/analyze` | Analisis komprehensif dua sisi (Model 1 + Model 2 YOLO) | JSON (Base64) | 15 MB / 60 req/menit |
| 6 | `POST` | `/upload/analyze` | Analisis komprehensif dua sisi versi berkas multipart | Multipart Form | 15 MB / 60 req/menit |
| 7 | `GET` | `/cards` | Eksplorasi katalog kartu (search, filter, pagination, sorting) | Query Params | Offline CSV Fallback |
| 8 | `GET` | `/sets` | Daftar seluruh ekspansi set rilis kartu Pokémon (172 set) | Query Params | Offline CSV Fallback |
| 9 | `GET` | `/cards/{card_id}/history` | Riwayat transaksi harga harian untuk visualisasi grafik | Path Param | Offline CSV Fallback |
| 10 | `GET` | `/cards/{card_id}/forecast` | Peramalan harga 7 hari Amazon Chronos-Bolt (P10, P50, P90) | Path Param | 60 req/menit |
| 11 | `POST` | `/cards/{card_id}/condition` | Penilaian cacat fisik kartu standalone via Base64 | JSON (Base64) | 15 MB / 60 req/menit |
| 12 | `POST` | `/upload/cards/{card_id}/condition` | Penilaian cacat fisik kartu standalone via Multipart | Multipart Form | 15 MB / 60 req/menit |
| 13 | `GET` | `/dashboard` | Agregasi dashboard pasar, leaderboard, rarity, era index, & likuiditas | Tidak Ada | Offline CSV Fallback |
| 14 | `GET` | `/currency` | Informasi status kurs live USD ke IDR dari cache RAM | Tidak Ada | Bebas |

---

## 🔬 4. Spesifikasi Rinci per Endpoint

### A. Layanan Status & Healthcheck

#### 1. `GET /`
Mengembalikan metadata status operasional server backend dan daftar endpoint resmi.
* **Request:** Tanpa parameter.
* **Response (200 OK):**
```json
{
  "app": "Regokemon Analytics API",
  "version": "3.1.0",
  "status": "online",
  "docs_url": "/docs",
  "endpoints": {
    "root_info": "GET /",
    "healthcheck": "GET /health",
    "oncam_identify": "POST /identify",
    "upload_identify": "POST /upload/identify",
    "full_analyze": "POST /analyze",
    "upload_analyze": "POST /upload/analyze",
    "cards_catalog": "GET /cards",
    "sets_catalog": "GET /sets",
    "card_history": "GET /cards/{card_id}/history",
    "card_forecast": "GET /cards/{card_id}/forecast",
    "card_condition": "POST /cards/{card_id}/condition",
    "upload_card_condition": "POST /upload/cards/{card_id}/condition",
    "dashboard_trending": "GET /dashboard",
    "currency_status": "GET /currency"
  }
}
```

#### 2. `GET /health`
Digunakan oleh sistem monitoring atau docker container healthcheck untuk memverifikasi kesiapan memori model AI dan koneksi dataset.
* **Response (200 OK):**
```json
{
  "status": "healthy",
  "app": "Regokemon Analytics API",
  "version": "3.1.0",
  "models": {
    "model_1_clip_faiss": true,
    "model_2_yolo_grader": true,
    "model_3_chronos_bolt": true
  },
  "dataset": {
    "master_cards_count": 20617,
    "total_sets_count": 172
  },
  "currency_rate_idr": 16500.0
}
```

---

### B. Layanan Computer Vision & Identifikasi Kartu

#### 3. `POST /identify`
Endpoint pemindaian kamera langsung (On-Cam). Menerima Base64 citra kartu, menjalankan Model 1 (OpenAI CLIP ViT-B-32 + FAISS + Top-8 ORB Re-Ranking) dengan latensi sub-detik (~120 ms).

* **Header:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "expected_card_id": null
}
```

* **Response (200 OK - Kasus Berhasil):**
```json
{
  "status": "success",
  "message": "Kartu berhasil diidentifikasi.",
  "card_id": "sv8-116",
  "name": "Koraidon",
  "number": "116/191",
  "set_name": "Surging Sparks",
  "set_id": "sv8",
  "set_series": "Scarlet & Violet",
  "release_year": 2024,
  "rarity": "Illustration Rare",
  "supertype": "Pokémon",
  "subtypes": "Basic",
  "types": "Dragon",
  "hp": 140.0,
  "confidence_percentage": 94.2,
  "confidence_label": "High",
  "raw_similarity_score": 0.8845,
  "orb_verification_score": 0.042,
  "margin_to_runner_up": 0.0812,
  "official_image_url": "https://images.pokemontcg.io/sv8/116_hires.png",
  "pricing": {
    "base_price_usd": 18.50,
    "base_price_idr": 305250,
    "condition_multiplier": 1.0,
    "condition_discount_pct": 0.0,
    "final_price_usd": 18.50,
    "final_price_idr": 305250,
    "currency_rate": 16500.0
  },
  "candidates": [
    {
      "rank": 2,
      "card_id": "sv8-117",
      "name": "Koraidon ex",
      "confidence_percentage": 78.4,
      "raw_similarity_score": 0.8033,
      "set_name": "Surging Sparks",
      "price_usd": 4.50,
      "price_idr": 74250
    }
  ],
  "execution_time_ms": 118.4
}
```

* **Response (200 OK - Kasus Ambigu / Confidence Gating < 45.0%):**
Jika skor keyakinan kartu di bawah ambang batas toleransi 45% (setelah *Conditional Lazy Orientation Fallback* diuji pada skor < 48%), API mengembalikan status `"ambiguous"` agar frontend dapat menginstruksikan pengguna untuk menyesuaikan posisi/pencahayaan:
```json
{
  "status": "ambiguous",
  "message": "Kartu belum teridentifikasi jelas. Posisikan kartu tegak lurus di tengah kotak panduan.",
  "card_id": null,
  "name": null,
  "confidence_percentage": 38.5,
  "confidence_label": "Rendah",
  "execution_time_ms": 124.2
}
```

#### 4. `POST /upload/identify`
Versi Multipart Form-Data untuk endpoint On-Cam / Identify. Berguna untuk klien HTTP atau formulir web yang mengirimkan berkas biner secara langsung.
* **Header:** `Content-Type: multipart/form-data`
* **Form Field:** `file` *(UploadFile, wajib, maks 15 MB)*
* **Response (200 OK):** Identik dengan skema `IdentifyResponse` pada endpoint `/identify`.

#### 5. `POST /analyze`
Endpoint evaluasi penuh untuk pemindaian foto statis. Menjalankan pipeline komprehensif: Model 1 (Identifikasi Kartu) + Model 2 (Deteksi Cacat Fisik Depan & Belakang via YOLO26s 800px) + Valuation Engine + Proyeksi Analitika.

* **Header:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "image": "data:image/jpeg;base64,...",
  "back_image": "data:image/jpeg;base64,...",
  "expected_card_id": null
}
```
* **Response (200 OK - AnalyzeResponse):**
Mengembalikan seluruh atribut `IdentifyResponse` ditambah objek kondisi fisik dan analitika valuasi:
```json
{
  "status": "success",
  "message": "Kartu berhasil diidentifikasi.",
  "card_id": "sv8-116",
  "name": "Koraidon",
  "condition_report": {
    "condition_tier": "Lightly Played (LP)",
    "has_defects": true,
    "defect_count": 2,
    "front_defects": [
      {
        "label": "Scratch",
        "confidence": 0.72,
        "bbox": {
          "x": 300.0,
          "y": 420.0,
          "width": 85.0,
          "height": 12.0,
          "x_pct": 35.71,
          "y_pct": 39.0,
          "width_pct": 10.12,
          "height_pct": 1.11,
          "img_width": 840,
          "img_height": 1077
        }
      }
    ],
    "back_defects": [
      {
        "label": "Corner Wear",
        "confidence": 0.64,
        "bbox": {
          "x": 580.0,
          "y": 145.0,
          "width": 24.0,
          "height": 20.0,
          "x_pct": 69.05,
          "y_pct": 13.46,
          "width_pct": 2.86,
          "height_pct": 1.86,
          "img_width": 840,
          "img_height": 1077
        }
      }
    ],
    "defects": [],
    "evaluation_status": "evaluated",
    "front_warped_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "back_warped_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  },
  "market_analytics": {
    "predicted_fair_value_usd": 15.72,
    "predicted_fair_value_idr": 259380,
    "mispricing_gap_pct": -15.0,
    "signal_reason": "Terdeteksi goresan fisik halus (-15% penyesuaian kondisi).",
    "forecast_7d": {
      "future_dates": ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"],
      "p10": [14.8, 14.5, 14.2, 14.0, 13.9, 13.8, 13.7],
      "p50": [15.7, 15.6, 15.5, 15.4, 15.3, 15.2, 15.1],
      "p90": [16.8, 17.0, 17.2, 17.3, 17.5, 17.6, 17.8]
    }
  },
  "recommendation_signal": "HOLD",
  "estimated_price": 259380,
  "execution_time_ms": 1150.2
}
```

#### 6. `POST /upload/analyze`
Versi Multipart Form-Data untuk endpoint Full Analysis. Mendukung unggahan foto tampak depan dan tampak belakang secara mandiri.
* **Header:** `Content-Type: multipart/form-data`
* **Form Fields:**
  * `front_file` *(UploadFile, wajib atau via fallback `file`, maks 15 MB)*: Citra tampak depan.
  * `back_file` *(UploadFile, opsional, maks 15 MB)*: Citra tampak belakang.
  * `card_id` *(str, opsional)*: Override ID kartu langsung jika user sudah memilih kartu dari katalog.
* **Response (200 OK):** Identik dengan skema `AnalyzeResponse` pada endpoint `/analyze`.

---

### C. Layanan Katalog & Eksplorasi Data

#### 7. `GET /cards`
Menampilkan daftar kartu resmi (20.617 entri) dengan fitur pencarian teks, filter kelangkaan, tipe kartu, set ekspansi, dan paginasi. Otomatis beralih ke CSV offline jika database Supabase tidak terjangkau.

* **Query Parameters:**
  * `limit` *(int, default=20, max=100)*: Jumlah kartu per halaman.
  * `page` *(int, default=1)*: Nomor halaman paginasi.
  * `search` *(str, opsional)*: Kata kunci pencarian nama kartu (disanitasi dengan URL-encoding).
  * `supertype` *(str, opsional)*: Filter tipe utama (`Pokémon`, `Trainer`, `Energy`).
  * `rarity` *(str, opsional)*: Filter tingkat kelangkaan (misal `Illustration Rare`, `Rare Holo`, `Common`).
  * `set_id` *(str, opsional)*: Filter berdasarkan kode set (misal `sv8`).
  * `sort_by` *(str, default="newest")*: Pengurutan (`newest`, `price_desc`, `price_asc`).
* **Response (200 OK):**
```json
{
  "total": 20617,
  "page": 1,
  "limit": 20,
  "total_pages": 1031,
  "currency_rate": 16500.0,
  "cards": [
    {
      "id": "sv8-116",
      "name": "Koraidon",
      "supertype": "Pokémon",
      "price": "$ 18.50",
      "price_usd": "$ 18.50",
      "price_idr": "Rp 305.250",
      "price_num": 18.50,
      "is_unlisted": false,
      "rarityText": "Illustration Rare",
      "rarityIcon": "IR",
      "set": "sv8",
      "image": "https://images.pokemontcg.io/sv8/116.png"
    }
  ]
}
```

#### 8. `GET /sets`
Mengambil seluruh daftar ekspansi set resmi Pokémon TCG terurut dari edisi rilis terbaru ke edisi klasik.
* **Query Parameters:** `limit` *(int, default=250)*: Mengakomodasi seluruh **172 set** resmi tanpa terpotong.
* **Response (200 OK):**
```json
[
  {
    "set_id": "sv8pt5",
    "name": "Prismatic Evolutions",
    "series": "Scarlet & Violet",
    "release_date": "2025-01-17",
    "release_year": 2025
  },
  {
    "set_id": "sv8",
    "name": "Surging Sparks",
    "series": "Scarlet & Violet",
    "release_date": "2024-11-08",
    "release_year": 2024
  }
]
```

---

### D. Layanan Analitika Deret Waktu & Peramalan

#### 9. `GET /cards/{card_id}/history`
Mengambil catatan deret waktu transaksi harga harian untuk kartu tertentu guna visualisasi grafik tren pasar.
* **Path Parameter:** `card_id` *(str, misal: `base1-4`)*
* **Response (200 OK):**
```json
[
  { "recorded_date": "2026-10-01", "effective_market_price": 285.50 },
  { "recorded_date": "2026-10-02", "effective_market_price": 288.00 },
  { "recorded_date": "2026-10-03", "effective_market_price": 292.00 }
]
```

#### 10. `GET /cards/{card_id}/forecast`
Endpoint peramalan harga probabilistik 7 hari ke depan menggunakan Amazon Chronos-Bolt Mini beserta rekomendasi sinyal trading preskriptif (`BUY`, `HOLD`, atau `SELL`).
* **Path Parameter:** `card_id` *(str, misal: `sv4-241`)*
* **Response (200 OK - ForecastResponse):**
```json
{
  "status": "success",
  "message": "Peramalan harga 7 hari berhasil diproses.",
  "card_id": "sv4-241",
  "card_name": "Rika",
  "current_price_usd": 2.81,
  "current_price_idr": 46365,
  "forecast": [
    {
      "day": 1,
      "date": "2026-11-16",
      "predicted_price_usd": 86.20,
      "p10_usd": 82.50,
      "p50_usd": 86.20,
      "p90_usd": 90.10
    },
    {
      "day": 7,
      "date": "2026-11-22",
      "predicted_price_usd": 91.50,
      "p10_usd": 84.00,
      "p50_usd": 91.50,
      "p90_usd": 99.20
    }
  ],
  "predicted_price_day7_usd": 91.50,
  "predicted_price_day7_idr": 1509750,
  "change_pct": 7.65,
  "signal": "BUY",
  "signal_reason": "Harga saat ini ($85.00) berada di bawah median wajar H+7 ($91.50) dengan tren akumulasi positif.",
  "mispricing_gap_pct": -7.1,
  "ai_confidence_pct": 91.4,
  "quantile_ribbon": {
    "future_dates": ["2026-11-16", "...", "2026-11-22"],
    "p10": [82.50, "...", 84.00],
    "p50": [86.20, "...", 91.50],
    "p90": [90.10, "...", 99.20]
  },
  "currency_rate": 16500.0
}
```
*(Catatan: `ai_confidence_pct` bernilai `null` apabila inferensi menggunakan fallback regresi tabular saat riwayat deret waktu < 5 hari).*

---

### E. Layanan Penilaian Kondisi Fisik Standalone

#### 11. `POST /cards/{card_id}/condition`
Mengevaluasi kondisi fisik kartu tertentu menggunakan Model 2 YOLO26s (800px) secara independen melalui representasi Base64.
* **Path Parameter:** `card_id` *(str)*
* **Request Body:**
```json
{
  "front_image": "data:image/jpeg;base64,...",
  "back_image": "data:image/jpeg;base64,..."
}
```
* **Response (200 OK - CardConditionResponse):**
```json
{
  "status": "success",
  "message": "Penilaian kondisi fisik selesai.",
  "card_id": "sv8-116",
  "card_name": "Koraidon",
  "condition_score_pct": 85.0,
  "condition_report": {
    "condition_tier": "Lightly Played (LP)",
    "has_defects": true,
    "defect_count": 1,
    "front_defects": [ { "label": "Scratch", "confidence": 0.78, "bbox": { "x": 300.0, "y": 420.0, "width": 85.0, "height": 12.0 } } ],
    "back_defects": []
  },
  "pricing": {
    "base_price_usd": 18.50,
    "base_price_idr": 305250,
    "condition_multiplier": 0.85,
    "condition_discount_pct": 15.0,
    "final_price_usd": 15.72,
    "final_price_idr": 259380,
    "currency_rate": 16500.0
  }
}
```

#### 12. `POST /upload/cards/{card_id}/condition`
Versi Multipart Form-Data untuk evaluasi kondisi fisik standalone.
* **Path Parameter:** `card_id` *(str)*
* **Header:** `Content-Type: multipart/form-data`
* **Form Fields:**
  * `front_file` *(UploadFile, opsional jika back_file ada, maks 15 MB)*
  * `back_file` *(UploadFile, opsional jika front_file ada, maks 15 MB)*
* **Response (200 OK):** Identik dengan skema `CardConditionResponse` pada endpoint `/cards/{card_id}/condition`.

---

### F. Layanan Dashboard & Valuta Asing

#### 13. `GET /dashboard`
Mengambil data kartu trending (Top Weekly Price Gainers) beserta agregasi analitika statistik katalog secara penuh untuk seluruh widget pada halaman Dashboard.
* **Response (200 OK):**
```json
{
  "trending": [
    {
      "id": 1,
      "card_id": "base1-4",
      "name": "Charizard",
      "rarity": "Rare Holo",
      "holo": "Holo Print",
      "price": "$ 285.50",
      "gain_pct": "+14.2%",
      "gain_numeric": 14.2,
      "image": "https://images.pokemontcg.io/base1/4_hires.png",
      "setIcon": "/base1-logo.png",
      "flagIcon": "US"
    }
  ],
  "total_cards": 20617,
  "total_sets": 172,
  "liquidity": {
    "active_cards": 19686,
    "total_cards": 20617,
    "liquidity_pct": 95.5,
    "status": "HIGH LIQUIDITY"
  },
  "character_leaderboard": [
    { "rank": 1, "pokemon": "Rayquaza", "medianUsd": 14.5, "medianIdr": "Rp 239.250", "sampleCount": 82, "tag": "Grail Tier" }
  ],
  "rarity_production": [
    { "name": "Common", "percent": 31.2, "count": "6.432 kartu", "color": "#4b5e94" }
  ],
  "chase_packs": [
    { "set_id": "sv3pt5", "title": "Pokemon 151", "theme": "tm-yellow", "layout": "tm-grid-2x2", "cards": [] }
  ],
  "era_trend_index": [
    { "year": "2026", "vintage": 51.9, "midEra": 32.74, "modern": 10.29 }
  ],
  "feature_impact": [
    { "feature": "Rarity Tier", "impact": 48.3, "label": "0.483 (Utama)" }
  ],
  "is_offline_fallback": false
}
```

#### 14. `GET /currency`
Mengambil informasi status kurs live USD ke IDR yang aktif digunakan dalam perhitungan sistem valuasi.
* **Response (200 OK):**
```json
{
  "currency": "USD_TO_IDR",
  "rate": 16500.0,
  "cached": true,
  "source": "live_api",
  "ttl_remaining_hours": 142.5
}
```

---

## 🧱 5. Skema Objek Data Bersama (Shared Schemas)

Berikut definisi tipe Pydantic utama di [`backend/app/schemas.py`](../backend/app/schemas.py):

* **`PricingDetails`:**
  * `base_price_usd` *(float)*: Harga pasar acuan awal kartu dalam kondisi mulus.
  * `base_price_idr` *(int)*: Estimasi harga dasar dalam Rupiah.
  * `condition_multiplier` *(float)*: Faktor diskon kondisi fisik ($F_{condition}$).
  * `condition_discount_pct` *(float)*: Persentase diskon terhitung.
  * `final_price_usd` *(float)*: Harga pasar wajar akhir ($P_{final}$).
  * `final_price_idr` *(int)*: Harga wajar akhir dalam Rupiah.
  * `currency_rate` *(float)*: Kurs acuan USD ke IDR.

* **`DefectItem`:**
  * `label` *(str)*: Jenis cacat fisik (`Card`, `Corner Wear`, `Edge Wear`, `Scratch`).
  * `confidence` *(float)*: Skor keyakinan model YOLO (0.0 s/d 1.0).
  * `bbox` *(dict)*: Koordinat spasial & persentase relatif citra warped `{ "x", "y", "width", "height", "x_pct", "y_pct", "width_pct", "height_pct", "img_width", "img_height" }`.

* **`ConditionReport`:**
  * `condition_tier` *(str)*: Kategori kondisi fisik (`Near Mint / Mint`, `Lightly Played (LP)`, `Moderately Played (MP)`, `Heavily Played (HP)`, `Damaged`).
  * `has_defects` *(bool)* & `defect_count` *(int)*.
  * `front_defects` / `back_defects` / `defects` *(List[DefectItem])*.
  * `evaluation_status` *(str)*: `evaluated`, `bypassed_oncam`, atau `error`.
  * `front_warped_image` / `back_warped_image` *(str, opsional)*: Data URL Base64 citra hasil *perspective alignment* untuk rendering overlay *bounding box* yang akurat di frontend.

---

## ⚠️ 6. Standar Penanganan Error (HTTP Status Codes)

API mengimplementasikan kode status HTTP standar:
* **`200 OK`:** Permintaan berhasil dieksekusi secara normal.
* **`400 Bad Request`:** Format data gambar tidak valid, berkas rusak, atau Base64 tidak dapat didekode.
* **`404 Not Found`:** `card_id` atau data kartu tidak ditemukan di database dan fallback master.
* **`413 Payload Too Large`:** Ukuran berkas unggahan atau string Base64 melebihi batas maksimum 15 MB.
* **`422 Unprocessable Entity`:** Struktur payload JSON tidak memenuhi spesifikasi skema Pydantic.
* **`429 Too Many Requests`:** Melebihi kuota pemanggilan (*rate limit*) inferensi AI (maksimum **300 req/menit** untuk `/identify` & `/upload/identify`; **60 req/menit** untuk endpoint AI berat per IP). Disertai header `Retry-After`.
* **`500 Internal Server Error`:** Terjadi kegagalan internal pada server backend atau pemrosesan model AI.
