# 📊 Ringkasan Eksekutif & Metrik Dataset (Dataset Summary & Metrics)

> **Pokemon Card Value Analytic Tool (REGOKEMON)**  
> **Terakhir Diperbarui:** 23 September 2026  
> **Status Sinkronisasi:** 100% Valid & Terverifikasi (Database Supabase, File Fisik, dan Dataset CSV/JSON)

Dokumen ini menyajikan rincian statistik kuantitatif, cakupan harga pasar, segmentasi kartu yang dapat dianalisis (*actionable dataset*), serta status integrasi seluruh komponen data di dalam sistem **Regokemon**.

---

## 🎯 1. Ringkasan Angka Kunci (High-Level Metrics)

| Parameter Metrik | Jumlah / Nilai | Persentase | Keterangan |
| :--- | :---: | :---: | :--- |
| **Total Kartu Mentah (API pokemontcg.io)** | **20.670** | 100,00% | Seluruh kartu Pokémon TCG resmi dari era Base Set (1999) hingga Mega Evolution (September 2026). |
| **Kartu Broken Links (Tautan Rusak/404)** | **53** | 0,26% | Kartu promosi McDonald's / Black Star Promo lama yang gambarnya dihapus oleh CDN pokemontcg.io (tercatat di `broken_links_report.csv`). |
| **Total Kartu Bersih Siap Pakai (Bisa Diotak-Atik)** | **20.617** | **99,74%** | **Dataset master aktif** (`pokemon_cards_dataset_cleaned.csv` & `.json`). Memiliki gambar fisik dan metadata lengkap. |
| **Total Edisi Set (Expansions)** | **172 Set** | - | Dari generasi pertama *Base Set* hingga edisi terbaru *30th Celebration* (`me55` & `me55c`). |
| **Aset Master Gambar Mentah (`raw_images/*.png`)** | **20.617 file** | 100,00% | File gambar resolusi tinggi (PNG) tersimpan lokal. |
| **Aset Gambar Terkompresi (`compressed_images/*.jpg`)** | **20.617 file** | 100,00% | Gambar resolusi 640×640 (JPG 85% Quality) untuk visual AI FAISS. |
| **Total Baris Master Terdaftar di Supabase** | **20.617 baris** | 100,00% | Terunggah secara utuh di tabel `cards` dan `card_prices`. |

---

## 💰 2. Metrik Cakupan Harga Pasar (Price Coverage)

Regokemon menggabungkan dua sumber harga internasional: **TCGPlayer** (fokus pasar Amerika Serikat / Dolar) dan **Cardmarket** (fokus pasar Eropa / Euro).

```
                             ┌─── TCGPlayer Market (18.688 kartu / 90,64%)
                             │
[ effective_market_price ] ──┼─── Cardmarket Trend/Avg (19.081 kartu / 92,55%)
 (19.686 kartu / 95,48%)     │
                             └─── Tanpa Harga / Rare Collector Only (931 kartu / 4,52%)
```

### Tabel Rincian Cakupan Harga:
| Kategori Harga | Jumlah Kartu | Persentase | Status & Implikasi Analitika |
| :--- | :---: | :---: | :--- |
| **Memiliki `effective_market_price`** | **19.686** | **95,48%** | **Sangat Tinggi**. Kartu memiliki harga pasar acuan aktif ($P_{base}$) untuk model valuasi. |
| **Memiliki Harga TCGPlayer** | 18.688 | 90,64% | Data mencakup varian *Normal*, *Holofoil*, dan *Reverse Holofoil*. |
| **Memiliki Harga Cardmarket** | 19.081 | 92,55% | Data mencakup *trend price*, serta riwayat rata-rata jual (*avg1, avg7, avg30*). |
| **Tanpa Data Harga (*Missing Price*)** | **931** | **4,52%** | Sebagian besar berupa kartu *Trophy Promo*, edisi turnamen eksklusif, atau kartu edisi awal yang sangat langka sehingga tidak ada transaksi retail harian. |

> [!TIP]
> **Strategi Penanganan Nilai Kosong (Fallback Policy):**  
> Untuk 931 kartu yang tidak memiliki harga pasar aktif, sistem Regokemon menggunakan nilai *median price* yang dihitung secara dinamis berdasarkan kombinasi `rarity` dan `release_year` yang sekelas, atau mengklasifikasikannya sebagai *Collector Appraisal Item*.

---

## 📈 3. Distribusi Statistik Harga Pasar ($ USD)

Berdasarkan 19.686 kartu yang memiliki data harga:

| Statistik Metrik | Nilai Valuasi ($ USD) | Nilai Setara (IDR @ Rp15.500) | Keterangan Distribusi |
| :--- | :---: | :---: | :--- |
| **Minimum** | **$0,01** | Rp155 | Kartu Energy dasar dan Common cetakan massal. |
| **Kuartil 1 ($Q_1$ - 25%)** | **$0,25** | Rp3.875 | 25% kartu berharga di bawah 25 sen USD. |
| **Median ($Q_2$ - 50%)** | **$0,96** | Rp14.880 | **Nilai tengah riil pasar**: 50% kartu berada di bawah $1 USD. |
| **Mean (Rata-Rata)** | **$22,56** | Rp349.680 | Rata-rata tertarik tinggi karena *outliers* kartu legendaris bernilai ribuan dolar. |
| **Kuartil 3 ($Q_3$ - 75%)** | **$7,48** | Rp115.940 | Kartu *Holo Rare*, *Ultra Rare*, dan kartu kompetitif reguler. |
| **Persentil 90 ($P_{90}$)** | **$38,25** | Rp592.875 | 10% kartu teratas memiliki nilai di atas $38 USD. |
| **Persentil 99 ($P_{99}$)** | **$388,82** | Rp6.026.710 | 1% kartu paling langka (Secret Rare, Alternate Art, Vintage). |
| **Maksimum** | **$4.500,00** | Rp69.750.000 | *Lugia - Aquapolis (Rare Secret)*. |

---

## 🏆 4. Top 10 Kartu Paling Bernilai di Dataset Regokemon

Berikut adalah 10 kartu dengan harga pasar acuan (*effective market price*) tertinggi yang ada di dalam database:

| No | Card ID | Nama Kartu | Seri / Set | Tingkat Kelangkaan (*Rarity*) | Harga Pasar ($ USD) |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | `ecard2-149` | **Lugia** | Aquapolis (E-Card, 2003) | Rare Secret | **$4.500,00** |
| 2 | `sm9-170` | **Latias & Latios-GX** (Alt Art) | Team Up (Sun & Moon, 2019) | Rare Ultra | **$3.910,42** |
| 3 | `ex15-101` | **Mew ★ (Gold Star)** | Dragon Frontiers (EX, 2006) | Rare Holo Star | **$3.500,00** |
| 4 | `ex7-107` | **Mudkip ★ (Gold Star)** | Team Rocket Returns (EX, 2004) | Rare Holo Star | **$3.101,79** |
| 5 | `ecard3-146` | **Charizard** | Skyridge (E-Card, 2003) | Rare Secret | **$2.999,99** |
| 6 | `np-28` | **Championship Arena** | Nintendo Black Star Promos (2005) | Promo | **$2.999,00** |
| 7 | `ex8-106` | **Latios ★ (Gold Star)** | Deoxys (EX, 2005) | Rare Holo Star | **$2.600,00** |
| 8 | `ex8-107` | **Rayquaza ★ (Gold Star)** | Deoxys (EX, 2005) | Rare Holo Star | **$2.500,99** |
| 9 | `ex10-105` | **Lugia ex** | Unseen Forces (EX, 2005) | Rare Holo EX | **$2.500,00** |
| 10 | `bp-8` | **Rocket's Mewtwo** | Best of Game (2002) | Promo | **$2.400,00** |

---

## 🧩 5. Segmentasi Kartu yang Bisa Diotak-Atik

### A. Berdasarkan Kategori Supertype
Setiap kategori memiliki karakteristik pemodelan analitika yang berbeda:
* **Pokémon (17.412 kartu / 84,45%)**: Memiliki atribut lengkap (`types`, `hp`, `subtypes`, `rarity`). Ini adalah target utama identifikasi gambar visual dan valuasi AI.
* **Trainer (2.811 kartu / 13,63%)**: Item, Supporter, Stadium, dan Pokémon Tool. Tidak memiliki HP/Type, namun memiliki volatilitas harga tinggi berdasarkan *metagame* turnamen.
* **Energy (394 kartu / 1,91%)**: Kartu energi dasar dan spesial.

### B. Berdasarkan Era Rilis (Vintage vs Modern)
Sistem analitika membagi kartu ke dalam dua era pasar dengan dinamika perilaku yang berbeda:
* **Era Modern (Tahun $\ge$ 2005): 18.016 kartu (87,38%)**  
  * Karakteristik: Likuiditas transaksi tinggi, perputaran harga harian dipengaruhi turnamen resmi dan tren unboxing YouTube/TikTok.
* **Era Vintage (Tahun $<$ 2005): 2.601 kartu (12,62%)**  
  * Karakteristik: Pasokan terbatas (*finite supply*), sangat sensitif terhadap kondisi fisik (*condition grading*), dan bertindak sebagai aset investasi jangka panjang (*blue-chip collectibles*).

### C. Sebaran Kartu per Seri Generasi (Series Breakdown)

```
Sword & Shield        [██████████████████████████████] 3.667 kartu
Scarlet & Violet      [█████████████████████████████ ] 3.629 kartu
Sun & Moon            [████████████████████████      ] 2.973 kartu
XY                    [███████████████               ] 1.923 kartu
EX Series             [██████████████                ] 1.766 kartu
Black & White         [████████████                  ] 1.437 kartu
Mega Evolution (2026) [█████████                     ] 1.170 kartu (Update Terbaru)
Diamond & Pearl       [███████                       ]   900 kartu
HeartGold SoulSilver  [████                          ]   544 kartu
E-Card                [████                          ]   529 kartu
Platinum              [████                          ]   517 kartu
Base Set (WotC)       [████                          ]   494 kartu
Neo                   [███                           ]   365 kartu
Gym                   [██                            ]   264 kartu
Seri Lainnya (Promo)  [███                           ]   439 kartu
```

---

## 🛠️ 6. Arsitektur File & Script Pengelola Data

Berikut adalah panduan file script yang mengoperasikan dataset ini di folder `backend/`:

| Nama File Script | Fungsi & Tanggung Jawab Utama | File Input $\rightarrow$ Output |
| :--- | :--- | :--- |
| [`clean_csv_broken_links.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/clean_csv_broken_links.py) | Memeriksa ketersediaan HTTP URL CDN dan menyaring tautan yang mati (53 link). | `pokemon_cards_dataset.csv` $\rightarrow$ `pokemon_cards_dataset_cleaned.csv` |
| [`export_broken_links.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/export_broken_links.py) | Melakukan audit jaringan dan mengekspor laporan 53 kartu rusak secara terurut deterministik. | `pokemon_cards_dataset.csv` $\rightarrow$ `broken_links_report.csv` |
| [`pokemon_cards_dataset_download.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/pokemon_cards_dataset_download.py) | Mengunduh file fisik resolusi tinggi master PNG secara paralel (multi-threading). | URL CDN $\rightarrow$ `dataset/raw_images/*.png` (20.617 file) |
| [`compress_images.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/compress_images.py) | Melakukan optimasi ukuran gambar ke format JPG 640×640 Lanczos untuk AI inference cepat. | `raw_images/*.png` $\rightarrow$ `compressed_images/*.jpg` (20.617 file) |
| [`json_to_csv.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/json_to_csv.py) | Menghubungkan JSON mentah dengan aset gambar lokal dan menyinkronkan dataset bersih. | `pokemon_cards_dataset.json` $\rightarrow$ `_cleaned.csv` & `_cleaned.json` |
| [`seed_supabase.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/seed_supabase.py) | Mengunggah dataset bersih ke cloud database Supabase dengan mode UPSERT. | `_cleaned.csv` $\rightarrow$ Supabase (`sets`, `cards`, `card_prices`) |
| [`daily_price_tracker.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/daily_price_tracker.py) | Bot otomatis harian yang menarik update fluktuasi harga dari API ke Supabase. | API pokemontcg.io $\rightarrow$ `card_prices` & `card_price_history` |
| [`models/build_card_index.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/models/build_card_index.py) | Mengekstrak vektor representasi CLIP ViT-B-32 (512-D) untuk pencarian sub-milidetik FAISS. | `compressed_images/` $\rightarrow$ `card_embeddings.index` & `card_id_map.json` |

---

## 📋 7. Panduan Penggunaan untuk Riset & Model (Cheat Sheet)

* **Jika ingin melakukan eksplorasi data analisis (EDA):**
  Gunakan berkas CSV utama:
  ```python
  import pandas as pd
  df = pd.read_csv("backend/dataset/pokemon_cards_dataset_cleaned.csv")
  print(f"Total kartu siap dianalisis: {len(df):,}")  # 20.617 baris
  ```

* **Jika ingin memuat data terstruktur bersarang (JSON):**
  Gunakan berkas JSON bersih:
  ```python
  import json
  with open("backend/dataset/pokemon_cards_dataset_cleaned.json", "r", encoding="utf-8") as f:
      cards = json.load(f)
  print(f"Total kartu di JSON: {len(cards):,}")  # 20.617 item
  ```

* **Jika ingin query langsung dari Database Cloud (PostgreSQL / Supabase):**
  ```python
  from supabase import create_client
  # Mengambil seluruh kartu dengan harga di atas $100
  res = supabase.table("cards").select("card_id, name, rarity, card_prices(effective_market_price)").gt("card_prices.effective_market_price", 100).execute()
  ```
