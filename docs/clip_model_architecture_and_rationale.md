# 🧠 Arsitektur Model CLIP & Rasional Pemilihan pada Sistem Regokemon

> **Pokemon Card Value Analytic Tool (REGOKEMON)**  
> **Modul Terkait:** `backend/models/card_identifier.py`, `card_identifier_realtime.py`, `card_identifier_oncam.py`  
> **Model Backbone:** `openai/clip-vit-base-patch32` (`ViT-B/32`)  
> **Status Integrasi:** Master Production Pipeline (Vector Search FAISS + Two-Stage ORB Reranking)

---

## 📌 Daftar Isi
1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Apa Itu CLIP?](#2-apa-itu-clip)
3. [Apakah Backbone CLIP Berbasis Vision Transformer (ViT)?](#3-apakah-backbone-clip-berbasis-vision-transformer-vit)
4. [Mengapa CLIP Sangat Cocok untuk Proyek Kartu Pokémon?](#4-mengapa-clip-sangat-cocok-untuk-proyek-kartu-pokémon)
5. [Arsitektur Two-Stage Hybrid: CLIP + FAISS + Fast ORB](#5-arsitektur-two-stage-hybrid-clip--faiss--fast-orb)
6. [Tabel Komparasi: CLIP ViT vs Model Alternatif](#6-tabel-komparasi-clip-vit-vs-model-alternatif)
7. [Panduan Menjawab Pertanyaan Dosen (Q&A Defense Guide)](#7-panduan-menjawab-pertanyaan-dosen-qa-defense-guide)

---

## 🎯 1. Ringkasan Eksekutif

Dalam pengenalan citra kartu Pokémon fisik secara *real-time*, pendekatan klasifikasi konvensional (seperti CNN ResNet/MobileNet dengan layer *Softmax*) memiliki keterbatasan mendasar: **ketidakmampuan menangani penambahan kelas baru tanpa pelatihan ulang (*closed-set limitation*)** serta **sensitivitas tinggi terhadap pantulan cahaya (*glare*) dan variasi sudut kamera**.

Sistem **Regokemon** mengadopsi model **CLIP (*Contrastive Language-Image Pre-training*)** dengan *backbone* **Vision Transformer (`ViT-B/32`)** sebagai ekstraktor fitur visual global (*embedding extractor*) yang dipadukan dengan mesin pencari vektor **FAISS** dan verifikasi fitur lokal **ORB**. Kombinasi ini menghasilkan sistem identifikasi kartu yang:
* Mampu mengenali **20.617+ kartu** secara instan tanpa batasan kelas kaku.
* Memiliki latensi rendah (**~120–150 ms** per inferensi), memungkinkan *live preview* **30+ FPS**.
* Tangguh terhadap gangguan fisik kamera HP (pantulan pelindung kartu/sleeve, bayangan, dan kemiringan perspektif).

---

## 🔍 2. Apa Itu CLIP?

**CLIP (*Contrastive Language-Image Pre-training*)** adalah model fondasi multimodal yang diperkenalkan oleh OpenAI (Radford et al., 2021). CLIP dilatih menggunakan paradigma **Contrastive Learning** pada skala masif (400 juta pasangan gambar dan teks dari internet).

```
          ┌─────────────────────────────────────────────────────────┐
          │                    ARSITEKTUR CLIP                      │
          └─────────────────────────────────────────────────────────┘

        Citra Input (Gambar Kartu)          Teks / Label / Deskripsi
                     │                                 │
                     ▼                                 ▼
         ┌───────────────────────┐         ┌───────────────────────┐
         │ Vision Encoder (ViT)  │         │     Text Encoder      │
         └───────────────────────┘         └───────────────────────┘
                     │                                 │
                     ▼                                 ▼
           Vektor Embedding Citra            Vektor Embedding Teks
               (512 Dimensi)                     (512 Dimensi)
                     │                                 │
                     └───────────────┬─────────────────┘
                                     ▼
                     Cosine Similarity (Dot Product)
                       [ Ruang Bersama / Joint Space ]
```

### Karakteristik Utama CLIP:
1. **Dual-Encoder Architecture:** Terdiri dari *Vision Encoder* (memproses gambar) dan *Text Encoder* (memproses teks). Pada sistem identifikasi kartu fisik Regokemon, komponen yang aktif digunakan saat inferensi *real-time* adalah **Vision Encoder**.
2. **Contrastive Objective:** Selama masa pelatihan, model memaksimalkan nilai *cosine similarity* untuk pasangan gambar-teks yang cocok, dan meminimalkan nilai untuk pasangan yang tidak cocok.
3. **Semantic Metric Space:** Output dari Vision Encoder adalah vektor berdimensi 512 yang terdistribusi secara seragam pada *unit hypersphere* ($L_2\text{-normalized}$), sehingga jarak sudut antar-vektor merepresentasikan kemiripan semantik dan visual.

---

## ⚡ 3. Apakah Backbone CLIP Berbasis Vision Transformer (ViT)?

**Ya, betul sekali.** Model CLIP yang digunakan di sistem ini adalah varian **`openai/clip-vit-base-patch32`** (dikenal sebagai **ViT-B/32**). 

Vision Encoder di dalam model ini sepenuhnya mengimplementasikan arsitektur **Vision Transformer (ViT)** (Dosovitskiy et al., ICLR 2021), bukan Convolutional Neural Network (CNN).

### Mekanisme Kerja Vision Transformer (ViT-B/32) pada Citra Kartu:

```
Gambar Kartu (224×224) 
   │
   ├─► Dipecah menjadi 49 Patch (7×7 grid, masing-masing patch berukuran 32×32 piksel)
   │
   ├─► Linear Projection: Tiap patch diubah menjadi vektor berdimensi 768
   │
   ├─► Ditambahkan [CLS] Token (token representasi global di awal urutan)
   │
   ├─► Ditambahkan Positional Embedding (informasi koordinat posisi patch)
   │
   ├─► Diproses melalui 12 Lapisan Transformer Encoder:
   │     • Multi-Head Self-Attention (12 heads)
   │     • Layer Normalization & MLP Blocks
   │     • Residual Connections
   │
   └─► Linear Projection Head ──► Vektor Embedding 512-Dimensi (L2-Normalized)
```

### Mengapa ViT Berbeda dari CNN Konvensional?
* **CNN (Convolutional Neural Network):** Menggunakan *local receptive field* (filter berukuran kecil, misal $3 \times 3$). Informasi spasial global baru terbangun secara bertahap setelah melalui banyak lapisan konvolusi dan pooling.
* **ViT (Vision Transformer):** Mekanisme **Self-Attention** memungkinkan setiap *patch* pada gambar untuk berinteraksi dan mengukur korelasi langsung dengan seluruh *patch* lainnya sejak lapisan pertama. Hal ini memberikan kemampuan **Global Context Awareness** yang jauh lebih unggul.

---

## 💡 4. Mengapa CLIP Sangat Cocok untuk Proyek Kartu Pokémon?

### Alasan 1: Zero-Shot Scalability (Pendekatan Metric Learning vs Klasifikasi Tertutup)

Dalam sistem TCG (*Trading Card Game*), jumlah kartu terus bertambah setiap ada ekspansi baru (hingga saat ini terdapat **20.617+ kartu unik** di database Regokemon).

| Aspek | Klasifikasi Konvensional (CNN + Softmax) | CLIP + Vector Retrieval (Regokemon) |
| :--- | :--- | :--- |
| **Output Layer** | Vektor probabilitas berdimensi tetap ($N$ kelas). | Vektor embedding kontinu 512 dimensi. |
| **Penambahan Kartu Baru** | **Harus melatih ulang model (*re-training*)** dari awal setiap ada rilis set kartu baru. | **Tanpa re-training.** Cukup ekstrak embedding kartu baru dan masukkan ke FAISS Index dalam 5 milidetik. |
| **Efisiensi Database** | Memerlukan ratusan sampel gambar training per kartu. | Memerlukan 1 gambar referensi master per kartu (*one-shot reference*). |

---

### Alasan 2: Pemahaman Tata Letak Global Kartu (*Global Spatial Layout Awareness*)

Kartu Pokémon memiliki struktur hierarkis terstandarisasi yang tersebar di berbagai sudut:
* **Pojok Kiri Atas:** Nama Pokémon dan Stage Evolusi (*Basic, Stage 1, Stage 2*).
* **Pojok Kanan Atas:** HP (*Hit Points*) dan Tipe Energi (*Fire, Water, Grass, dll.*).
* **Bagian Tengah:** Kotak ilustrasi utama (*Artwork Box*).
* **Bagian Bawah:** Daftar serangan (*Attacks*), teks deskripsi aturan (*Rules/Ability*), kelemahan (*Weakness*), dan biaya mundur (*Retreat*).
* **Pojok Kanan/Kiri Bawah:** Simbol Set, Nomor Koleksi (misal `129/167`), dan Simbol Kelangkaan (*Rarity*).

CNN konvensional sering kali terkecoh oleh kemiripan warna latar belakang atau pose Pokémon. Berkat mekanisme **Self-Attention ViT**, CLIP mampu menghubungkan korelasi antara artwork tengah dengan teks dan tata letak frame di sekelilingnya secara simultan.

---

### Alasan 3: Ketahanan terhadap Gangguan Kamera Fisik (*Robustness to Distribution Shift*)

Pengambilan gambar langsung melalui kamera HP (*on-cam / real-time*) memiliki tantangan optik yang nyata:
1. **Pantulan Cahaya (*Glare / Reflection*):** Lapisan plastik pelindung (*sleeve*) atau kartu *holographic/foil* memantulkan cahaya lampu ruangan.
2. **Perubahan Pencahayaan:** Suhu warna lampu (putih vs kuning) dan intensitas lux ruangan yang tidak seragam.
3. **Kemiringan Perspektif (*Perspective Distortion*):** Tangan pengguna yang sedikit bergetar atau memegang kartu dengan sudut miring.

Karena CLIP dilatih pada 400 juta citra internet yang bervariasi secara ekstrem, representasi fiturnya bersifat **invarian terhadap gangguan fotometrik minor**. Model tetap mampu mengenali identitas kartu meskipun sebagian area kartu tertutup kilau pantulan lampu.

---

### Alasan 4: Efisiensi Komputasi dan Kecepatan Inferensi Real-Time

Varian **`ViT-B/32`** dipilih secara spesifik karena menghadirkan *sweet spot* terbaik antara akurasi representasi dan kecepatan eksekusi:
* Ukuran vektor sangat ringkas: **512 elemen float32** (~2 KB per kartu).
* Indeks FAISS untuk **20.617 kartu** hanya memakan memori RAM sebesar **~42 MB**.
* Waktu ekstraksi fitur hanya **~120–150 ms** pada CPU standar atau GPU laptop.
* Melalui arsitektur *Multithreaded Asynchronous Worker* yang diterapkan pada `card_identifier_realtime.py`, *frame rate* kamera tetap berjalan mulus di **30+ FPS** tanpa *lag* atau *freeze*.

---

## 🏗️ 5. Arsitektur Two-Stage Hybrid: CLIP + FAISS + Fast ORB

Meskipun CLIP sangat kuat dalam representasi visual makro, kartu Pokémon memiliki tantangan unik: **Varian Cetak Ulang (*Reprints*)**. Kartu reprint memiliki artwork Pokémon yang identik, tetapi berasal dari set berbeda dengan nomor koleksi, simbol set, dan border yang berbeda tipis.

Untuk mengatasi hal ini, Regokemon menerapkan **Two-Stage Identification Pipeline**:

```
[ Kamera HP (720x1280) ] 
          │
          ▼
[ Kotak Target Rasio 63:88 ] ──► [ Deteksi Ketajaman (Laplacian Var) ]
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 1: Global Semantic Retrieval (CLIP ViT-B/32 + FAISS)       │
│ • Mengekstrak vektor 512-D dari crop kartu                      │
│ • Melakukan Inner Product Search di FAISS (20.617 kartu)        │
│ • Mengembalikan Top-K Kandidat Terdekat (~120 ms)               │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼ (Top-K Pool, e.g. K=15 untuk Real-Time)
┌─────────────────────────────────────────────────────────────────┐
│ TAHAP 2: Local Fine-Grained Verification (Fast ORB Reranking)   │
│ • Ekstraksi keypoint geometris lokal (sudut set, teks halus)     │
│ • Homography & RANSAC geometric consensus matching              │
│ • Memberikan bobot tambahan pada kandidat yang terverifikasi    │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
[ Output Terkalibrasi: Nama Kartu, Set, ID, Harga Pasar, & Metrik CV ]
```

---

## 📊 6. Tabel Komparasi: CLIP ViT vs Model Alternatif

| Kriteria Evaluasi | MobileNetV3 (Legacy) | ResNet-50 (Klasifikasi) | SIFT / ORB Murni | **CLIP ViT-B/32 (Regokemon)** |
| :--- | :---: | :---: | :---: | :---: |
| **Arsitektur Dasar** | CNN Ringan | Deep CNN (Residual) | Detektor Titik Sudut | **Vision Transformer (ViT)** |
| **Mekanisme Fitur** | Konvolusi Lokal | Konvolusi Lokal | Gradien Lokal | **Multi-Head Self-Attention** |
| **Skalabilitas Kelas** | Terbatas (Closed-Set) | Terbatas (Closed-Set) | Terbuka (Database Fitur) | **Sangat Fleksibel (Open-Set Metric Space)** |
| **Kemudahan Tambah Kartu** | Retraining Ulang | Retraining Ulang | Tambah Deskriptor | **Tinggal Append Vektor ke FAISS** |
| **Ketahanan terhadap Glare** | Rendah | Sedang | Sangat Rendah | **Tinggi (Trained on 400M Web Images)** |
| **Ukuran Embedding** | 1024 Dimensi | 2048 Dimensi | Ribuan Titik per Gambar | **512 Dimensi (Efisien)** |
| **Latensi Inferensi** | ~50 ms | ~180 ms | ~400–800 ms (Lambat) | **~120–150 ms (Optimal)** |

---

## 🎓 7. Panduan Menjawab Pertanyaan Dosen (Q&A Defense Guide)

Berikut adalah panduan antisipasi pertanyaan dari dosen penguji/pembimbing Computer Vision beserta jawaban yang tepat dan berbobot:

### Q1: *"Kenapa memilih CLIP, bukan fine-tuning ResNet atau model klasifikasi biasa?"*
> **Jawaban:**  
> *"Jika menggunakan klasifikasi konvensional dengan output layer Softmax, model akan terkunci pada jumlah kelas tertentu. Kartu Pokémon memiliki lebih dari 20.000 varian dan terus bertambah setiap beberapa bulan saat ekspansi baru dirilis. Jika memakai klasifikasi biasa, setiap rilis kartu baru kita harus melakukan retraining seluruh model.*  
> *Dengan CLIP, kami menggunakan pendekatan **Metric Learning / Vector Retrieval**. CLIP berperan sebagai feature extractor serbaguna yang menghasilkan representasi 512 dimensi, lalu pencarian dilakukan menggunakan FAISS. Ketika ada kartu baru, kami cukup mengekstrak embedding-nya satu kali dan memasukkannya ke indeks FAISS tanpa perlu melatih ulang model."*

---

### Q2: *"Apakah Vision Transformer (ViT) di CLIP tidak terlalu berat untuk dijalankan real-time di laptop?"*
> **Jawaban:**  
> *"Kami menggunakan varian **ViT-B/32** (Base dengan patch size 32). Patch berukuran 32×32 menghasilkan sequence length yang relatif ringkas (hanya 49 patch tokens untuk input 224×224), sehingga komputasi Self-Attention-nya jauh lebih ringan dibandingkan ViT-B/16. Waktu inferensinya berkisar antara 120 hingga 150 ms.*  
> *Selain itu, kami memisahkan proses inferensi ke dalam **Background Worker Thread Asinkron**, sehingga rendering kamera dan animasi UI tetap berjalan stabil dan mulus di atas 30 FPS tanpa terjadi freeze pada layar."*

---

### Q3: *"Mengapa masih membutuhkan ORB jika CLIP sudah akurat?"*
> **Jawaban:**  
> *"CLIP sangat unggul dalam menangkap kemiripan semantik dan visual global, tetapi kartu Pokémon memiliki kasus khusus yaitu **kartu reprint**. Kartu reprint menampilkan ilustrasi Pokémon yang sama persis, tetapi berasal dari set dan nomor kartu yang berbeda.*  
> *Untuk membedakan varian tersebut secara presisi, kami menerapkan **Two-Stage Pipeline**: CLIP dan FAISS bertindak sebagai pencari cepat untuk menyaring 20.617 kartu menjadi pool kandidat kecil (Top-15), kemudian algoritma **ORB Feature Matching** melakukan verifikasi geometris lokal tingkat piksel untuk memvalidasi nomor set dan logo spesifik di bagian bawah kartu."*
