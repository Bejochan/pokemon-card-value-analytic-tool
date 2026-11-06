# 📡 Spesifikasi Teknis REST API Regokemon
## Dokumentasi Lengkap Endpoint, Kontrak Payload, dan Skema Data

> **Pokemon Card Value Analytic Tool (REGOKEMON) : API Reference**  
> **Server Engine:** FastAPI (Python 3.10 - 3.12, Uvicorn ASGI)  
> **Base URL Lokal:** `http://127.0.0.1:8000`  
> **Dokumentasi Interaktif:** `/docs` (Swagger UI) & `/redoc` (ReDoc)  
> **CORS Policy:** Mengizinkan komunikasi lintas-asal (`*`) untuk integrasi Frontend React  

---

## 📌 Daftar Isi
1. [Ikhtisar Arsitektur API](#1-ikhtisar-arsitektur-api)
2. [Konfigurasi Base URL & Environment](#2-konfigurasi-base-url--environment)
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

REST API Regokemon dirancang menggunakan framework **FastAPI** dengan arsitektur asinkron berbasis ASGI (*Asynchronous Server Gateway Interface*). API ini bertindak sebagai jembatan terpadu antara antarmuka pengguna (React Single Page Application) dengan tiga engine komputasi:
1. **Model 1 Engine:** Ekstraksi embedding visual OpenAI CLIP (ViT-B/32) dan pencarian vektor FAISS IndexFlatIP (20.617 kartu).
2. **Model 2 Engine:** Deteksi cacat fisik lokal YOLO26s (800px) untuk tampak depan dan tampak belakang.
3. **Model 3 Engine:** Peramalan deret waktu probabilistik Amazon Chronos-Bolt Mini (Pita Kuantil P10, P50, P90).
4. **Analytics Engine:** Formula valuasi harga wajar pasar dan konversi kurs mata uang real-time.

---

## ⚙️ 2. Konfigurasi Base URL & Environment

Pada lingkungan pengembangan lokal, backend berjalan di:
```text
http://127.0.0.1:8000
```
Frontend React mengakses endpoint melalui modul konfigurasi [`frontend/src/config/api.js`](../frontend/src/config/api.js):
```javascript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
```
Untuk deployment cloud (seperti Render, Railway, atau VPS), tetapkan variabel `VITE_API_BASE_URL` pada pengaturan lingkungan build.

---

## 📋 3. Daftar Lengkap Endpoint REST API

| No | Metode | Endpoint | Deskripsi Ringkas | Tipe Payload |
| :---: | :---: | :--- | :--- | :---: |
| 1 | `GET` | `/` | Informasi status layanan, versi API, dan deskripsi engine | Tidak Ada |
| 2 | `GET` | `/health` | Healthcheck server untuk monitoring load balancer / Docker | Tidak Ada |
| 3 | `POST` | `/identify` | Identifikasi cepat Model 1 On-Cam (khusus kamera live) | JSON (Base64) |
| 4 | `POST` | `/upload/identify` | Identifikasi cepat Model 1 On-Cam versi unggah file multipart | Multipart Form |
| 5 | `POST` | `/analyze` | Analisis komprehensif (Model 1 + Model 2 YOLO depan & belakang) | JSON (Base64) |
| 6 | `POST` | `/upload/analyze` | Analisis komprehensif versi unggah file multipart dua sisi | Multipart Form |
| 7 | `GET` | `/cards` | Eksplorasi katalog kartu (search, filter, pagination, sorting) | Query Params |
| 8 | `GET` | `/sets` | Daftar seluruh ekspansi set rilis kartu Pokémon | Query Params |
| 9 | `GET` | `/cards/{card_id}/history` | Riwayat transaksi harga harian untuk visualisasi grafik | Path Param |
| 10 | `GET` | `/cards/{card_id}/forecast` | Peramalan harga 7 hari Amazon Chronos-Bolt (P10, P50, P90) | Path Param |
| 11 | `POST` | `/cards/{card_id}/condition` | Penilaian cacat fisik kartu standalone via Base64 | JSON (Base64) |
| 12 | `POST` | `/upload/cards/{card_id}/condition` | Penilaian cacat fisik kartu standalone via Multipart | Multipart Form |
| 13 | `GET` | `/dashboard` | Agregasi data trending, total kartu (20.617), dan total set (172) | Tidak Ada |
| 14 | `GET` | `/currency` | Informasi kurs live USD ke IDR dan status cache RAM | Tidak Ada |

---

## 🔬 4. Spesifikasi Rinci per Endpoint

### A. Layanan Status & Healthcheck

#### 1. `GET /`
Mengembalikan informasi dasar mengenai server API.
* **Request:** Tanpa parameter.
* **Response (200 OK):**
```json
{
  "message": "Regokemon Analytics & Valuation API is running!",
  "version": "3.1.0",
  "docs": "/docs",
  "redoc": "/redoc",
  "models": {
    "model_1": "CLIP ViT-B-32 + FAISS IndexFlatIP (20.617 Kartu)",
    "model_2": "Local YOLO26s (800px) Dual-Side Condition Grader",
    "model_3": "Amazon Chronos-Bolt Mini Time-Series Forecaster"
  }
}
```

#### 2. `GET /health`
Digunakan oleh orkestrator sistem untuk memverifikasi kesiapan server.
* **Response (200 OK):**
```json
{
  "status": "healthy"
}
```

---

### B. Layanan Computer Vision & Identifikasi Kartu

#### 3. `POST /identify`
Endpoint pemindaian cepat yang digunakan oleh antarmuka *Real-Time Scanner HUD*. Endpoint ini hanya menjalankan Model 1 (CLIP + FAISS + Top-8 ORB Re-Ranking) tanpa menjalankan Model 2 untuk menjaga latensi tetap sub-detik (~120 ms).

* **Header:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "expected_card_id": null
}
```
* **Response (200 OK - IdentifyResponse):**
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

#### 4. `POST /analyze`
Endpoint evaluasi penuh untuk pemindaian foto statis. Menjalankan pipeline lengkap: Model 1 (Identifikasi Kartu) + Model 2 (Deteksi Cacat Fisik Depan & Belakang via YOLO26s) + Valuation Engine + Proyeksi Analitika.

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
Mengembalikan seluruh atribut `IdentifyResponse` ditambah:
```json
{
  "condition_report": {
    "condition_tier": "Lightly Played (LP)",
    "has_defects": true,
    "defect_count": 2,
    "front_defects": [
      {
        "label": "Scratch",
        "confidence": 0.72,
        "bbox": { "x": 300.0, "y": 420.0, "width": 85.0, "height": 12.0 }
      }
    ],
    "back_defects": [
      {
        "label": "Corner Wear",
        "confidence": 0.64,
        "bbox": { "x": 580.0, "y": 35.0, "width": 24.0, "height": 20.0 }
      }
    ],
    "defects": [ ... ],
    "evaluation_status": "evaluated"
  },
  "market_analytics": {
    "predicted_fair_value_usd": 15.72,
    "predicted_fair_value_idr": 259380,
    "mispricing_gap_pct": -15.0,
    "signal_reason": "Terdeteksi goresan fisik halus (-15% penyesuaian kondisi).",
    "forecast_7d": {
      "future_dates": ["2026-11-07", "2026-11-08", "..."],
      "p10": [14.8, 14.5, 14.2, 14.0, 13.9, 13.8, 13.7],
      "p50": [15.7, 15.6, 15.5, 15.4, 15.3, 15.2, 15.1],
      "p90": [16.8, 17.0, 17.2, 17.3, 17.5, 17.6, 17.8]
    }
  },
  "recommendation_signal": "HOLD",
  "execution_time_ms": 1150.2
}
```

---

### C. Layanan Katalog & Eksplorasi Data

#### 5. `GET /cards`
Menampilkan daftar kartu dari database katalog resmi (20.617 kartu) dengan fitur pencarian dan filter bertingkat.

* **Query Parameters:**
  * `limit` *(int, default=20, max=100)*: Jumlah kartu per halaman.
  * `page` *(int, default=1)*: Nomor halaman paginasi.
  * `search` *(str, opsional)*: Kata kunci pencarian nama kartu.
  * `supertype` *(str, opsional)*: Filter tipe utama (`Pokémon`, `Trainer`, `Energy`).
  * `rarity` *(str, opsional)*: Filter tingkat kelangkaan (misal `Illustration Rare`).
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

#### 6. `GET /sets`
Mengambil seluruh daftar ekspansi set resmi Pokémon TCG terurut dari edisi terbaru ke edisi klasik.
* **Query Parameters:** `limit` *(int, default=150)*
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

#### 7. `GET /cards/{card_id}/history`
Mengambil catatan deret waktu transaksi harga harian untuk kartu tertentu.
* **Path Parameter:** `card_id` *(str, misal: `base1-4`)*
* **Response (200 OK):**
```json
[
  { "recorded_date": "2026-10-01", "effective_market_price": 285.50 },
  { "recorded_date": "2026-10-02", "effective_market_price": 288.00 },
  { "recorded_date": "2026-10-03", "effective_market_price": 292.00 }
]
```

#### 8. `GET /cards/{card_id}/forecast`
Endpoint peramalan harga probabilistik 7 hari ke depan menggunakan Amazon Chronos-Bolt Mini.
* **Path Parameter:** `card_id` *(str, misal: `sv4-241`)*
* **Response (200 OK - ForecastResponse):**
```json
{
  "status": "success",
  "message": "Peramalan harga 7 hari berhasil diproses.",
  "card_id": "sv4-241",
  "card_name": "Roaring Moon ex",
  "current_price_usd": 85.00,
  "current_price_idr": 1402500,
  "forecast": [
    {
      "day": 1,
      "date": "2026-11-07",
      "predicted_price_usd": 86.20,
      "p10_usd": 82.50,
      "p50_usd": 86.20,
      "p90_usd": 90.10
    },
    {
      "day": 7,
      "date": "2026-11-13",
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
  "currency_rate": 16500.0
}
```

---

### E. Layanan Penilaian Kondisi Fisik Standalone

#### 9. `POST /cards/{card_id}/condition`
Mengevaluasi kondisi fisik kartu tertentu menggunakan Model 2 YOLO26s secara independen (tanpa menjalankan Model 1).
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
    "front_defects": [ { "label": "Scratch", "confidence": 0.78, "bbox": { ... } } ],
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

---

### F. Layanan Dashboard & Valuta Asing

#### 10. `GET /dashboard`
Mengambil data ringkasan pasar untuk kartu trending dan total statistik katalog.
* **Response (200 OK):**
```json
{
  "trending": [
    {
      "id": 1,
      "card_id": "base1-4",
      "name": "Charizard",
      "rarity": "Rare Holo",
      "holo": "Normal Print",
      "price": "$ 285.50",
      "image": "https://images.pokemontcg.io/base1/4_hires.png",
      "setIcon": "/base1-logo.png",
      "flagIcon": "🇺🇸"
    }
  ],
  "total_cards": 20617,
  "total_sets": 172
}
```

#### 11. `GET /currency`
Mengambil status kurs live valuta asing USD ke IDR dari layanan in-memory cache.
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
  * `base_price_usd` *(float)*: Harga acuan pasar awal.
  * `base_price_idr` *(int)*: Estimasi harga dasar dalam Rupiah.
  * `condition_multiplier` *(float)*: Faktor diskon kondisi fisik ($F_{condition}$).
  * `condition_discount_pct` *(float)*: Persentase diskon terhitung.
  * `final_price_usd` *(float)*: Harga pasar wajar akhir ($P_{final}$).
  * `final_price_idr` *(int)*: Harga wajar akhir dalam Rupiah.
  * `currency_rate` *(float)*: Kurs acuan USD ke IDR.

* **`DefectItem`:**
  * `label` *(str)*: Jenis cacat (`Scratch`, `Corner Wear`, `Edge Wear`).
  * `confidence` *(float)*: Skor keyakinan model YOLO (0.0 s/d 1.0).
  * `bbox` *(dict)*: Koordinat spasial `{ "x", "y", "width", "height" }`.

---

## ⚠️ 6. Standar Penanganan Error (HTTP Status Codes)

API mengimplementasikan kode status HTTP standar:
* **`200 OK`:** Permintaan berhasil dieksekusi secara normal.
* **`400 Bad Request`:** Format data gambar tidak valid atau Base64 tidak dapat didekode.
* **`404 Not Found`:** `card_id` atau data yang dicari tidak ditemukan di database.
* **`422 Unprocessable Entity`:** Struktur payload JSON tidak memenuhi spesifikasi skema Pydantic.
* **`500 Internal Server Error`:** Terjadi kegagalan internal pada server backend (koneksi database atau engine AI).

