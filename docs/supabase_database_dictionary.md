# 🗄️ Kamus Data & Dokumentasi Skema Database Supabase

> **Pokemon Card Value Analytic Tool (REGOKEMON)**  
> **Database Engine:** Supabase Cloud (PostgreSQL 15+)  
> **Skema:** `public`  
> **Total Entitas Master:** 161 Sets, 20.426 Kartu (`cards`), Snapshot Harga (`card_prices`), dan Riwayat Harga Harian (`card_price_history`)  
> **File DDL / Skema Asli:** [`docs/schema.sql`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/docs/schema.sql)  
> **Skrip Seeding & Tracker:** [`backend/seed_supabase.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/seed_supabase.py) & [`backend/daily_price_tracker.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/daily_price_tracker.py)

---

## 📌 1. Diagram Relasi Entitas (Entity-Relationship Diagram / ERD)

Database dirancang dalam bentuk relasional yang ternormalisasi (3NF) guna memisahkan metadata ekspansi set, profil kartu, snapshot harga pasar aktif, dan tren pergerakan harga historis:

```mermaid
erDiagram
    SETS ||--o{ CARDS : "memiliki (1:N)"
    CARDS ||--|| CARD_PRICES : "memiliki snapshot harga (1:1)"
    CARDS ||--o{ CARD_PRICE_HISTORY : "mencatat tren harian (1:N)"

    SETS {
        TEXT set_id PK "Kode unik set, mis: base1, sv8pt5"
        TEXT name "Nama resmi ekspansi set"
        TEXT series "Era seri generasi, mis: Scarlet & Violet"
        DATE release_date "Tanggal rilis resmi set"
        INT release_year "Tahun rilis resmi set"
    }

    CARDS {
        TEXT card_id PK "Kode unik kartu, mis: sv8pt5-77"
        TEXT name "Nama karakter/item kartu"
        TEXT supertype "Pokémon / Trainer / Energy"
        TEXT subtypes "Kategori evolusi, mis: Basic, Stage 1"
        TEXT types "Elemen energi, mis: Colorless, Fire"
        FLOAT hp "Hit Points karakter Pokémon"
        TEXT number "Nomor urut koleksi di dalam set"
        TEXT rarity "Tingkat kelangkaan, mis: Illustration Rare"
        TEXT artist "Nama seniman pembuat ilustrasi"
        TEXT set_id FK "Relasi ke tabel sets(set_id)"
        TEXT image_small "URL thumbnail kartu resmi"
        TEXT image_large "URL gambar resolusi tinggi master"
    }

    CARD_PRICES {
        TEXT card_id PK_FK "Relasi ke cards(card_id) ON DELETE CASCADE"
        NUMERIC tcg_normal_market "Harga transaksi varian reguler TCGPlayer (USD)"
        NUMERIC tcg_normal_low "Harga penawaran terendah varian reguler (USD)"
        NUMERIC tcg_normal_mid "Median penawaran varian reguler (USD)"
        NUMERIC tcg_normal_high "Harga penawaran tertinggi varian reguler (USD)"
        NUMERIC tcg_holo_market "Harga transaksi varian holofoil (USD)"
        NUMERIC tcg_holo_low "Harga penawaran terendah varian holofoil (USD)"
        NUMERIC tcg_holo_mid "Median penawaran varian holofoil (USD)"
        NUMERIC tcg_holo_high "Harga penawaran tertinggi varian holofoil (USD)"
        NUMERIC tcg_reverse_market "Harga pasar varian reverse holo (USD)"
        NUMERIC cardmarket_trend "Tren harga pasar Eropa di Cardmarket (EUR)"
        NUMERIC cardmarket_avg_sell "Rata-rata harga jual di Cardmarket (EUR)"
        NUMERIC cardmarket_low "Harga terendah di Cardmarket (EUR)"
        NUMERIC cardmarket_avg1 "Rata-rata harga 1 hari terakhir (EUR)"
        NUMERIC cardmarket_avg7 "Rata-rata harga 7 hari terakhir (EUR)"
        NUMERIC cardmarket_avg30 "Rata-rata harga 30 hari terakhir (EUR)"
        NUMERIC effective_market_price "Harga acuan pasar utama (Base Price) (USD)"
        TIMESTAMPTZ updated_at "Waktu update terakhir"
    }

    CARD_PRICE_HISTORY {
        TEXT card_id PK_FK "Relasi ke cards(card_id) ON DELETE CASCADE"
        DATE recorded_date PK "Tanggal pencatatan kalender harian"
        NUMERIC tcg_normal_market "Harga pasar reguler pada tanggal tersebut"
        NUMERIC tcg_holo_market "Harga pasar holofoil pada tanggal tersebut"
        NUMERIC cardmarket_trend "Tren Cardmarket pada tanggal tersebut"
        NUMERIC cardmarket_avg1 "Rata-rata harga 1 hari pada tanggal tersebut"
        NUMERIC cardmarket_avg7 "Rata-rata harga 7 hari pada tanggal tersebut"
        NUMERIC cardmarket_avg30 "Rata-rata harga 30 hari pada tanggal tersebut"
        NUMERIC effective_market_price "Harga acuan efektif pada tanggal tersebut"
        TIMESTAMPTZ created_at "Waktu pencatatan"
    }
```

---

## 📋 2. Kamus Data Atribut per Tabel

### A. Tabel `public.sets` (Ekspansi Seri Rilis)
Menyimpan referensi katalog ekspansi rilis Pokémon TCG sejak generasi Base Set (1999) hingga era Scarlet & Violet terbaru.

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `set_id` | `TEXT` | `PRIMARY KEY` | `'sv8pt5'`, `'base1'` | Kode unik resmi ekspansi set dari Pokémon TCG API. |
| `name` | `TEXT` | `NOT NULL` | `'Prismatic Evolutions'` | Nama resmi peluncuran set. Digunakan untuk pencarian dan filter antarmuka. |
| `series` | `TEXT` | `NOT NULL` | `'Scarlet & Violet'` | Era konsol / generasi rilis. Bermanfaat untuk segmentasi dan komparasi pasar antar-era. |
| `release_date` | `DATE` | `NULLABLE` | `'2025-01-17'` | Tanggal rilis komersial resmi ke publik. Digunakan untuk perhitungan usia kartu. |
| `release_year` | `INT` | `NULLABLE` | `2025` | Tahun rilis (integer) untuk fitur filter cepat, grouping, dan regresi tren tahunan. |

---

### B. Tabel `public.cards` (Master Profil Kartu)
Menyimpan identitas spesifik dari 20.426 varian kartu individual yang terdaftar.

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `card_id` | `TEXT` | `PRIMARY KEY` | `'sv8pt5-77'` | Identifier global unik per kartu (kombinasi `set_id` dan nomor seri kartu). |
| `name` | `TEXT` | `NOT NULL` | `'Eevee'` | Nama karakter Pokémon, nama Trainer, atau jenis kartu Energy. |
| `supertype` | `TEXT` | `NOT NULL` | `'Pokémon'` | Klasifikasi hierarki utama: `'Pokémon'`, `'Trainer'`, atau `'Energy'`. |
| `subtypes` | `TEXT` | `NULLABLE` | `'Basic'`, `'Stage 2'` | Kategori evolusi atau status kartu (misal: *EX*, *VMAX*, *Item*, *Supporter*). |
| `types` | `TEXT` | `NULLABLE` | `'Colorless'`, `'Fire'` | Tipe energi/elemen Pokémon. Membantu filter koleksi deck turnamen. |
| `hp` | `FLOAT` | `NULLABLE` | `70.0`, `310.0` | Nilai Hit Points kartu. Fitur numerik penting untuk korelasi kekuatan vs nilai kelangkaan. |
| `number` | `TEXT` | `NOT NULL` | `'77'`, `'001/165'` | Nomor urut fisik yang tercetak pada kartu pojok kiri/kanan bawah. |
| `rarity` | `TEXT` | `NULLABLE` | `'Illustration Rare'` | Tingkat kelangkaan kartu resmi. Menjadi salah satu prediktor harga terkuat. |
| `artist` | `TEXT` | `NULLABLE` | `'Mitsuhiro Arita'` | Nama ilustrator kartu. Berperan penting dalam memprediksi premi harga kartu *special art*. |
| `set_id` | `TEXT` | `FK` | `'sv8pt5'` | Mengacu ke `sets.set_id` dengan aturan `ON DELETE CASCADE`. |
| `image_small` | `TEXT` | `NULLABLE` | `'https://images.pokemontcg.io/...'` | URL gambar resolusi rendah resmi (thumbnail) untuk ditampilkan pada list katalog UI. |
| `image_large` | `TEXT` | `NULLABLE` | `'https://images.pokemontcg.io/...'` | URL gambar resolusi tinggi master resmi untuk inspeksi visual detail. |

---

### C. Tabel `public.card_prices` (Snapshot Valuasi & Harga Pasar Terkini)
Menyimpan harga pasar aktif dari marketplace internasional (TCGPlayer & Cardmarket) serta harga acuan pasar terhitung. Diperbarui setiap hari oleh cron tracker.

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `card_id` | `TEXT` | `PRIMARY KEY, FK` | `'sv8pt5-77'` | Mengacu langsung ke `cards.card_id` dengan aturan relasi 1-to-1 dan `ON DELETE CASCADE`. |
| `tcg_normal_market` | `NUMERIC(10,2)` | `NULLABLE` | `1.25` | Harga pasar riil varian Non-Holo dari TCGPlayer (USD). |
| `tcg_normal_low` | `NUMERIC(10,2)` | `NULLABLE` | `0.50` | Penawaran harga terendah varian Non-Holo (USD). |
| `tcg_normal_mid` | `NUMERIC(10,2)` | `NULLABLE` | `1.40` | Median harga penawaran varian Non-Holo (USD). |
| `tcg_normal_high` | `NUMERIC(10,2)` | `NULLABLE` | `5.00` | Penawaran harga tertinggi varian Non-Holo (USD). |
| `tcg_holo_market` | `NUMERIC(10,2)` | `NULLABLE` | `18.50` | Harga pasar riil varian Holofoil dari TCGPlayer (USD). |
| `tcg_holo_low` | `NUMERIC(10,2)` | `NULLABLE` | `12.00` | Penawaran harga terendah varian Holofoil (USD). |
| `tcg_holo_mid` | `NUMERIC(10,2)` | `NULLABLE` | `19.00` | Median harga penawaran varian Holofoil (USD). |
| `tcg_holo_high` | `NUMERIC(10,2)` | `NULLABLE` | `45.00` | Penawaran harga tertinggi varian Holofoil (USD). |
| `tcg_reverse_market` | `NUMERIC(10,2)` | `NULLABLE` | `2.10` | Harga pasar riil varian Reverse Holo dari TCGPlayer (USD). |
| `cardmarket_trend` | `NUMERIC(10,2)` | `NULLABLE` | `14.20` | Indikator tren harga transaksi terkini pada Cardmarket Eropa (EUR). |
| `cardmarket_avg_sell` | `NUMERIC(10,2)` | `NULLABLE` | `13.85` | Rata-rata harga penjualan nyata 30 hari di Cardmarket (EUR). |
| `cardmarket_low` | `NUMERIC(10,2)` | `NULLABLE` | `8.00` | Harga terendah di Cardmarket (EUR). |
| `cardmarket_avg1` | `NUMERIC(10,2)` | `NULLABLE` | `14.50` | Rata-rata harga 1 hari terakhir (kemarin) di Cardmarket (EUR). |
| `cardmarket_avg7` | `NUMERIC(10,2)` | `NULLABLE` | `14.10` | Rata-rata harga 7 hari terakhir (minggu ini) di Cardmarket (EUR). |
| `cardmarket_avg30` | `NUMERIC(10,2)` | `NULLABLE` | `13.90` | Rata-rata harga 30 hari terakhir (bulan ini) di Cardmarket (EUR). |
| `effective_market_price` | `NUMERIC(10,2)` | `NULLABLE` | `18.50` | **Harga Acuan Pasar Utama ($P_{base}$)** dalam USD. Dasar valuasi $P_{final}$ sistem Regokemon. |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` | `'2026-09-22 15:00:00+00'` | Waktu stempel saat harga terakhir disinkronkan ke Supabase. |

---

### D. Tabel `public.card_price_history` (Riwayat Tren Time-Series Harian)
Menyimpan snapshot historis harga harian per tanggal kalender untuk keperluan pembuatan grafik tren harga panjang dan model peramalan (*forecasting*).

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `card_id` | `TEXT` | `PK, FK` | `'sv8pt5-77'` | Mengacu ke `cards.card_id`. Bagian dari Composite Primary Key. |
| `recorded_date` | `DATE` | `PK` | `'2026-09-22'` | Tanggal pencatatan harga harian. Mengizinkan 1 rekaman per kartu per hari. |
| `tcg_normal_market` | `NUMERIC(10,2)` | `NULLABLE` | `1.25` | Snapshot harga pasar varian reguler pada tanggal tersebut. |
| `tcg_holo_market` | `NUMERIC(10,2)` | `NULLABLE` | `18.50` | Snapshot harga pasar varian holofoil pada tanggal tersebut. |
| `cardmarket_trend` | `NUMERIC(10,2)` | `NULLABLE` | `14.20` | Snapshot tren harga Cardmarket pada tanggal tersebut. |
| `cardmarket_avg1` | `NUMERIC(10,2)` | `NULLABLE` | `14.50` | Rata-rata harga 1 hari pada tanggal pencatatan. |
| `cardmarket_avg7` | `NUMERIC(10,2)` | `NULLABLE` | `14.10` | Rata-rata harga 7 hari pada tanggal pencatatan. |
| `cardmarket_avg30` | `NUMERIC(10,2)` | `NULLABLE` | `13.90` | Rata-rata harga 30 hari pada tanggal pencatatan. |
| `effective_market_price` | `NUMERIC(10,2)` | `NULLABLE` | `18.50` | Snapshot harga acuan efektif pada tanggal pencatatan. |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` | `'2026-09-22 00:00:00+00'` | Waktu stempel penulisan baris rekaman. |

---

## ⚡ 3. Optimasi Indeks Database (Performance Indexing)

Untuk memastikan respons pencarian REST API FastAPI tetap di bawah **15 milidetik** saat melayani ribuan request, dibuat indeks B-Tree khusus:

```sql
-- Mempercepat pencarian kartu berdasarkan nama (autocomplete & text search)
CREATE INDEX IF NOT EXISTS idx_cards_name ON public.cards(name);

-- Mempercepat filter daftar kartu berdasarkan seri rilis / set
CREATE INDEX IF NOT EXISTS idx_cards_set_id ON public.cards(set_id);

-- Mempercepat filter kartu berdasarkan elemen (Water, Fire, Grass, dll)
CREATE INDEX IF NOT EXISTS idx_cards_types ON public.cards(types);

-- Mempercepat filter berdasarkan kelangkaan (Secret Rare, Illustration Rare, dll)
CREATE INDEX IF NOT EXISTS idx_cards_rarity ON public.cards(rarity);

-- Mempercepat sorting kartu termahal / termurah (ORDER BY effective_market_price)
CREATE INDEX IF NOT EXISTS idx_card_prices_effective ON public.card_prices(effective_market_price);
```

---

## 🔗 4. Integrasi dengan Backend & Computer Vision

```text
[ Foto Kamera / Scanner ]
           │
           ▼
[ Model 1: CLIP Engine ] ──(card_id: "sv8pt5-77")──► [ Query Supabase Cloud ]
                                                              │
                                                              ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ SELECT c.name, c.rarity, s.name as set_name, p.effective_market_price  │
 │ FROM cards c                                                           │
 │ JOIN sets s ON c.set_id = s.set_id                                     │
 │ JOIN card_prices p ON c.card_id = p.card_id                            │
 │ WHERE c.card_id = 'sv8pt5-77';                                         │
 └────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
 [ Model 2: YOLOv8 Grader ] ──(F_condition: 0.85)──► [ Analytics Valuation ]
                                                              │
                                                              ▼
                                               [ Rekomendasi BUY / HOLD / SELL ]
```

1. **Inferensi Model 1 (CLIP):** Mengembalikan `card_id` kartu dengan skor kemiripan tertinggi.
2. **Pencarian Cepat Supabase:** Backend FastAPI menarik data `effective_market_price` ($P_{base}$), `release_year`, dan `rarity` dari Supabase.
3. **Kombinasi Kondisi Fisik Model 2 (YOLOv8):** Kerusakan fisik (Scratched, Bent, Edge Wear) dikalikan ke harga acuan pasar untuk menghasilkan estimasi harga wajar kartu bekas yang realistis.

---

## 🛠️ 5. Contoh Kueri SQL Analitika yang Sering Digunakan

### A. Mengambil Detail Kartu Lengkap Beserta Harga Pasar
```sql
SELECT 
    c.card_id,
    c.name,
    c.rarity,
    c.types,
    c.hp,
    s.name AS set_name,
    s.release_year,
    p.effective_market_price,
    p.tcg_normal_market,
    p.tcg_holo_market
FROM public.cards c
LEFT JOIN public.sets s ON c.set_id = s.set_id
LEFT JOIN public.card_prices p ON c.card_id = p.card_id
WHERE c.card_id = 'sv8pt5-77';
```

### B. Menampilkan 10 Kartu Termahal di Seluruh Database
```sql
SELECT 
    c.card_id,
    c.name,
    s.name AS set_name,
    s.release_year,
    c.rarity,
    p.effective_market_price
FROM public.cards c
JOIN public.sets s ON c.set_id = s.set_id
JOIN public.card_prices p ON c.card_id = p.card_id
WHERE p.effective_market_price IS NOT NULL
ORDER BY p.effective_market_price DESC
LIMIT 10;
```

### C. Statistik Rata-rata Harga per Tingkat Kelangkaan (Rarity)
```sql
SELECT 
    c.rarity,
    COUNT(c.card_id) AS total_kartu,
    ROUND(AVG(p.effective_market_price), 2) AS rata_rata_harga_usd,
    MAX(p.effective_market_price) AS harga_tertinggi_usd
FROM public.cards c
JOIN public.card_prices p ON c.card_id = p.card_id
WHERE p.effective_market_price IS NOT NULL AND c.rarity IS NOT NULL
GROUP BY c.rarity
ORDER BY rata_rata_harga_usd DESC;
```
