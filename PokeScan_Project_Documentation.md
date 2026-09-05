# PokeScan — Dokumentasi Proyek Anjay

**Dashboard analitik dan tools cek grade PSA untuk kolektor Pokemon card**

---

## 1. Ringkasan Proyek

PokeScan adalah aplikasi web berbasis Computer Vision yang membantu kolektor Pokemon card mengambil keputusan beli/jual yang lebih baik. Aplikasi ini menggabungkan tiga kemampuan dalam satu alur kerja:

1. **Search & Browse** — cari kartu secara manual dari database lengkap
2. **Scan & Grade** — foto kartu fisik, sistem otomatis identifikasi kartu dan estimasi kondisi (grade PSA)
3. **Trend & Signal** — lihat grafik harga historis dan dapatkan rekomendasi beli/tahan/jual

### Masalah yang diselesaikan

Kolektor sering menghadapi dua masalah nyata:
- **Beli kemahalan** — tidak tahu apakah harga yang ditawarkan penjual sesuai harga wajar pasar
- **Tidak tahu waktu jual yang tepat** — tidak ada alat bantu untuk melihat tren harga sebelum memutuskan

### Skenario penggunaan utama

Bayangkan sedang di event trading kartu. Seseorang menawarkan Charizard Base Set fisik dengan harga tertentu. Alih-alih menebak, pengguna membuka PokeScan, memfoto kartu tersebut, dan dalam hitungan detik mendapat:
- Identitas kartu (nama, set, rarity)
- Estimasi grade PSA dari kondisi fisik
- Harga pasar wajar untuk grade tersebut
- Sinyal apakah harga yang ditawarkan wajar, kemahalan, atau justru murah

---

## 2. Target Pengguna

| Segmen | Kebutuhan |
|---|---|
| Kolektor kasual | Cek harga wajar sebelum membeli kartu untuk koleksi pribadi |
| Kolektor yang mencari untung | Analisis tren harga untuk keputusan jual-beli yang menguntungkan |

Aplikasi dirancang seperti **Investing.com/RTI versi Pokemon card** — tempat riset dan pantau harga, bukan marketplace transaksi.

---

## 3. Arsitektur Sistem

```
Frontend (React + TypeScript)
        ↓ HTTP POST (gambar)
Backend (FastAPI, Python)
        ↓
CV Layer:
  - YOLOv8         → deteksi kartu + crop + perspective correction
  - EfficientNet-B4 → ekstraksi embedding 512-dimensi
        ↓
Search Layer:
  - FAISS index    → nearest neighbor search dari 15.000+ referensi kartu
        ↓
Data Layer:
  - PostgreSQL     → metadata kartu, histori harga, log scan
  - pokemontcg.io  → sync harga harian (TCGPlayer + Cardmarket)
        ↓
Response: identitas kartu + estimasi grade + harga + sinyal beli/jual
```

### Tech stack

| Layer | Tools |
|---|---|
| Frontend | React, TypeScript, Vite, TailwindCSS |
| Backend | FastAPI, Python, SQLAlchemy |
| CV — Detection | YOLOv8 (Ultralytics), fine-tuned dari COCO pretrained |
| CV — Embedding | EfficientNet-B4 (PyTorch/timm) |
| Similarity search | FAISS (Facebook AI), cosine similarity |
| Database | PostgreSQL |
| Data source | pokemontcg.io API |

---

## 4. Pipeline Computer Vision

### Stage 1 — Card Detection
- **Input:** foto kartu dengan background apapun
- **Proses:** YOLOv8 deteksi bounding box, lalu perspective warp untuk normalisasi orientasi
- **Output:** crop kartu yang sudah lurus dan siap diproses

### Stage 2 — Feature Extraction & Identification
- **Input:** crop kartu 300×420px
- **Proses:** EfficientNet-B4 menghasilkan vector embedding 512 dimensi sebagai "fingerprint visual" kartu
- **Output:** embedding vector

### Stage 3 — Similarity Search
- **Input:** embedding hasil Stage 2
- **Proses:** FAISS mencari nearest neighbor dari index 15.000+ kartu referensi
- **Output:** top-5 kandidat kartu beserta confidence score

### Stage 4 — Condition Grading (PSA Estimate)
- **Input:** foto resolusi tinggi kartu yang sudah teridentifikasi
- **Proses:** analisis 4 kriteria PSA — centering, corners, edges, surface
- **Output:** estimasi grade 1–10 dengan confidence interval

### Stage 5 — Price Lookup & Signal
- **Input:** card ID + estimasi grade
- **Proses:** query harga pasar khusus untuk grade tersebut, bandingkan dengan harga yang diinput/ditawarkan
- **Output:** grafik tren harga + sinyal buy/hold/sell

---

## 5. Dataset

### Sumber data (semua legal dan gratis untuk riset)

| Sumber | Kegunaan | Catatan |
|---|---|---|
| pokemontcg.io API | Gambar referensi 15.000+ kartu, metadata, harga TCGPlayer & Cardmarket | 20.000 request/hari dengan API key gratis |
| eBay Finding API | Foto kartu bergrade PSA untuk training model grading | Grade bisa di-parse dari judul listing |
| PriceCharting.com | Harga per grade PSA (7, 8, 9, 10) | Perlu scraping sopan dengan Playwright |
| Foto fisik mandiri | Data kondisi nyata untuk fine-tuning model grading | Beli kartu bekas dari marketplace lokal |

### Catatan penting
Cardmarket.com **tidak bisa** di-scrape langsung (diblokir, robots.txt melarang). Tapi tidak masalah — data harga Cardmarket sudah tersedia lewat pokemontcg.io API secara legal.

### Strategi pengumpulan data grading
1. Ambil listing eBay dengan kata kunci `"PSA [grade] [nama kartu]"` — foto dan grade sudah menempel di judul
2. Beli 20–50 kartu bekas kondisi bervariasi dari marketplace lokal untuk foto manual
3. Pretrain dari dataset foto berkualitas, fine-tune dengan data kondisi nyata

---

## 6. Logika Sinyal Beli/Tahan/Jual

### Versi awal (target 2 minggu)
Membandingkan harga yang ditawarkan dengan harga pasar wajar sesuai grade:

```
selisih = (harga_ditawarkan - harga_pasar_wajar) / harga_pasar_wajar

selisih > +15%  → SELL sinyal (kartu kemahalan, jangan beli)
selisih < -15%  → BUY sinyal (kartu di bawah harga wajar)
antara itu      → HOLD / harga wajar
```

### Versi lanjutan (kalau waktu memungkinkan)
Menambahkan komponen arah tren harga 30 hari terakhir, bukan cuma perbandingan harga sesaat — kartu yang murah tapi tren terus turun beda sinyal dengan kartu murah yang tren naik.

### Kenapa grade penting dalam perhitungan
Harga pasar wajar diambil dari histori harga **khusus grade yang terdeteksi**, bukan rata-rata semua kondisi. Ini membuat fitur grading benar-benar dipakai dalam keputusan bisnis, bukan sekadar fitur tempelan.

---

## 7. Novelty & Kontribusi Akademik

- **Fine-grained multi-variant recognition** — membedakan varian kartu yang tampilannya mirip tapi harganya jauh berbeda (contoh: Charizard Base Set Holo vs Shadowless)
- **PSA grade estimation dari foto** — belum ada publikasi akademik yang benchmark ini secara proper
- **Kontribusi dataset** — dataset referensi dan embedding yang dibangun sendiri, bisa dipublikasikan sebagai open-source
- **Integrasi grading ke keputusan bisnis** — bukan cuma model CV berdiri sendiri, tapi terhubung langsung ke sistem rekomendasi

---

## 8. Analisis SWOT

### Strengths
- Tiga komponen (search, scan, prediksi) saling menguatkan dalam satu alur logis
- Positioning jelas lewat analogi RTI/Investing.com
- Dataset harga tersedia legal dan gratis
- Grading PSA jadi diferensiator nyata

### Weaknesses
- Data foto kartu fisik untuk training grading belum ada, harus dikumpulkan dari nol
- Ground truth PSA grade rawan noise karena grading manusia sendiri subjektif
- Histori harga harian masih pendek di awal proyek
- Holographic card menyulitkan deteksi visual karena reflektif tergantung sudut foto

### Opportunities
- Belum ada kompetitor yang gabungkan identifikasi, grading, dan sinyal beli/jual dalam satu tools
- Komunitas Pokemon TCG Indonesia cukup besar untuk validasi user nyata
- Dataset dan model bisa dipublikasikan sebagai kontribusi open-source
- Bisa diperluas ke TCG lain (Yu-Gi-Oh, Magic) kalau modelnya generalizable

### Threats
- Rate limit API bisa jadi hambatan kalau volume sync harga makin besar
- Timeline 2 bulan ketat kalau komponen grading molor
- Ekspektasi akurasi grading tinggi dari penguji, padahal PSA sendiri kadang tidak konsisten
- Produk serupa bisa muncul dari kompetitor besar (TCGPlayer, PSA) kapan saja

---

## 9. Timeline Pengembangan (8 Minggu, Tim 4 Orang)

### Minggu 1–2 — Fondasi Data & Card Index
- Setup pokemontcg.io API, download semua data kartu, bangun database
- Mulai jalankan cron job harian untuk snapshot harga (mulai sedini mungkin)
- Bangun fitur search & browse dasar di frontend

*Rekomendasi pembagian: 2 orang backend/data pipeline, 2 orang frontend search UI*

### Minggu 3–4 — CV Pipeline (Deteksi & Identifikasi)
- Bangun YOLOv8 untuk deteksi kartu
- Bangun EfficientNet + FAISS untuk identifikasi
- Paralel: mulai kumpulkan foto kartu fisik untuk data grading

*Rekomendasi pembagian: 2 orang CV model, 2 orang kumpul data foto + labeling*

### Minggu 5–6 — PSA Grading & Logika Signal
- Bangun model estimasi grade dari foto (mulai versi sederhana)
- Implementasi logika buy/hold/sell versi awal
- Mulai integrasi semua komponen jadi satu alur

*Rekomendasi pembagian: 2 orang grading model, 2 orang signal logic + dashboard*

### Minggu 7–8 — Polish, Testing, Demo Prep
- Integrasi penuh, testing end-to-end, perbaikan bug
- Siapkan skenario demo trading event
- Upgrade signal logic ke versi lanjutan kalau sempat
- Latihan presentasi

*Semua anggota: testing + demo prep*

---

## 10. Risiko Utama & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Data foto kartu fisik terbatas | Model grading kurang akurat | Mulai kumpulkan sejak minggu 1, gunakan transfer learning dari model foundation |
| Data historis harga pendek | Prediksi tren kurang solid | Mulai cron job harian sedini mungkin, pakai avg7/avg30 dari API sebagai titik awal |
| Holographic card sulit dideteksi | Akurasi identifikasi turun | Kumpulkan foto dari berbagai sudut, atau fokus non-holo dulu untuk MVP |
| Timeline ketat | Fitur tidak selesai tepat waktu | Prioritaskan versi sederhana dulu (Level 1) di tiap komponen, baru upgrade jika waktu memungkinkan |

---

## 11. Metrik Evaluasi

| Komponen | Metrik |
|---|---|
| Card detection | mAP@50, precision, recall |
| Card identification | Top-1 dan Top-5 accuracy |
| Grading model | Mean absolute error terhadap grade asli, per-rarity breakdown |
| Price signal | Directional accuracy (persentase sinyal beli/jual yang benar arahnya) |

---

*Dokumen ini dibuat sebagai rangkuman diskusi perancangan proyek PokeScan. Silakan didiskusikan dan disesuaikan bersama tim sebelum eksekusi.*
