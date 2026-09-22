# 🗄️ Kamus Data & Dokumentasi Skema Database Supabase

> **Pokemon Card Value Analytic Tool (REGOKEMON)**  
> **Database Engine:** Supabase Cloud (PostgreSQL 15+)  
> **Skema:** `public`  
> **Total Entitas Master:** 161 Sets, 20.426 Kartu (`cards`), dan 20.426 Data Harga (`card_prices`)  
> **File DDL / Skema Asli:** [`docs/schema.sql`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/docs/schema.sql)  
> **Skrip Seeding:** [`backend/seed_supabase.py`](file:///d:/Career/Semester%205/Project%20Analitika%20Data/Proyek%20Pokemon/backend/seed_supabase.py)

---

## 📌 1. Diagram Relasi Entitas (Entity-Relationship Diagram / ERD)

Database dirancang dalam bentuk relasional yang ternormalisasi (3NF) guna memisahkan metadata ekspansi set, profil kartu, dan data valuasi harga yang dinamis:

```mermaid
erDiagram
    SETS ||--o{ CARDS : "memiliki (1:N)"
    CARDS ||--|| CARD_PRICES : "memiliki harga (1:1)"

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
        NUMERIC tcg_normal_market "Harga pasar varian reguler TCGPlayer (USD)"
        NUMERIC tcg_holo_market "Harga pasar varian holofoil TCGPlayer (USD)"
        NUMERIC tcg_reverse_market "Harga pasar varian reverse holo TCGPlayer (USD)"
        NUMERIC cardmarket_trend "Tren harga pasar Eropa di Cardmarket (EUR/USD)"
        NUMERIC cardmarket_avg_sell "Rata-rata harga jual 30 hari di Cardmarket"
        NUMERIC effective_market_price "Harga acuan pasar utama hasil kalkulasi (P_base)"
        TIMESTAMPTZ updated_at "Waktu pencatatan/pembaruan harga terakhir"
    }
```

---

## 📋 2. Rincian Kolom Tabel Database

### A. Tabel `public.sets` (Ekspansi Seri / Set Kartu)
Menyimpan daftar edisi resmi peluncuran kartu Pokémon TCG sejak edisi *Base Set (1999)* hingga era modern.

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `set_id` | `TEXT` | `PRIMARY KEY` | `'sv8pt5'`, `'base1'` | Kode pengenal unik edisi ekspansi. Menjadi *Foreign Key* rujukan bagi tabel `cards`. |
| `name` | `TEXT` | `NOT NULL` | `'Prismatic Evolutions'`, `'Base'` | Nama lengkap resmi ekspansi rilis. Digunakan untuk pencarian dan penyaringan di UI. |
| `series` | `TEXT` | `NULLABLE` | `'Scarlet & Violet'`, `'Base'` | Era/generasi game Pokémon yang menaungi ekspansi ini. |
| `release_date` | `DATE` | `NULLABLE` | `'2025-01-17'`, `'1999-01-09'` | Tanggal rilis resmi ke pasar global. |
| `release_year` | `INT` | `NULLABLE` | `2025`, `1999` | Tahun rilis resmi. Digunakan dalam formula valuasi: tahun `< 2005` mendapat pengali kartu vintage ($M_{vintage}$). |

---

### B. Tabel `public.cards` (Katalog Utama Kartu Pokémon)
Menyimpan profil lengkap identitas kartu dari 20.426 entri yang telah disinkronkan secara 1-to-1 dengan dataset citra.

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `card_id` | `TEXT` | `PRIMARY KEY` | `'sv8pt5-77'`, `'base1-4'` | ID unik kartu (kombinasi `{set_id}-{number}`). Dipakai sebagai acuan inferensi Model 1 (CLIP). |
| `name` | `TEXT` | `NOT NULL` | `'Hoothoot'`, `'Charizard'` | Nama resmi kartu/karakter Pokémon. |
| `supertype` | `TEXT` | `NULLABLE` | `'Pokémon'`, `'Trainer'`, `'Energy'` | Kategori fundamental kartu. Mengatur aturan apakah kartu memiliki HP/elemen atau tidak. |
| `subtypes` | `TEXT` | `NULLABLE` | `'Basic'`, `'Stage 2'`, `'Supporter'` | Sub-kategori gameplay/evolusi kartu. Kartu edisi spesial (VMAX, Tera, Radiant) mendapat pengali valuasi ($M_{variant}$). |
| `types` | `TEXT` | `NULLABLE` | `'Colorless'`, `'Fire'`, `'Water, Metal'` | Tipe elemen energi. Bernilai `NULL` untuk kartu `Trainer` dan `Energy` (aturan resmi permainan TCG). |
| `hp` | `FLOAT` | `NULLABLE` | `80.0`, `120.0`, `330.0` | Poin nyawa kartu karakter. Bernilai `NULL` untuk kartu `Trainer` dan `Energy`. |
| `number` | `TEXT` | `NULLABLE` | `'77'`, `'4'`, `'?'` | Nomor urut koleksi di dalam set. Kartu unik Unown edisi Unseen Forces bernilai `'?'`. |
| `rarity` | `TEXT` | `NULLABLE` | `'Illustration Rare'`, `'Common'` | Tingkat kelangkaan kartu. Merupakan faktor utama penentu pengali harga dasar pasar kartu. |
| `artist` | `TEXT` | `NULLABLE` | `'REND'`, `'Mitsuhiro Arita'` | Nama seniman/ilustrator gambar kartu. Kolektor sering memburu kartu dari ilustrator legendaris tertentu. |
| `set_id` | `TEXT` | `FOREIGN KEY` | `'sv8pt5'` | Mengacu ke `sets.set_id` dengan aturan `ON DELETE CASCADE`. |
| `image_small` | `TEXT` | `NULLABLE` | `'https://images.pokemontcg.io/...'` | URL gambar resolusi rendah resmi (thumbnail) untuk ditampilkan pada list katalog UI. |
| `image_large` | `TEXT` | `NULLABLE` | `'https://images.pokemontcg.io/...'` | URL gambar resolusi tinggi master resmi untuk inspeksi visual detail. |

---

### C. Tabel `public.card_prices` (Valuasi & Histori Harga Pasar)
Menyimpan harga pasar aktif dari marketplace internasional (TCGPlayer & Cardmarket) serta harga acuan pasar terhitung.

| Nama Kolom | Tipe Data SQL | Constraints | Contoh Data | Deskripsi & Peran Analitika |
| :--- | :---: | :---: | :--- | :--- |
| `card_id` | `TEXT` | `PRIMARY KEY, FK` | `'sv8pt5-77'` | Mengacu langsung ke `cards.card_id` dengan aturan relasi 1-to-1 dan `ON DELETE CASCADE`. |
| `tcg_normal_market` | `NUMERIC(10,2)` | `NULLABLE` | `NULL`, `1.25` | Harga pasar harian varian Non-Holo (kertas biasa) dari TCGPlayer dalam mata uang USD ($). |
| `tcg_holo_market` | `NUMERIC(10,2)` | `NULLABLE` | `18.50`, `0.80` | Harga pasar harian varian Holofoil mengilap dari TCGPlayer dalam mata uang USD ($). |
| `tcg_reverse_market` | `NUMERIC(10,2)` | `NULLABLE` | `NULL`, `2.10` | Harga pasar harian varian Reverse Holofoil (latar mengilap) dari TCGPlayer dalam mata uang USD ($). |
| `cardmarket_trend` | `NUMERIC(10,2)` | `NULLABLE` | `14.20` | Indikator tren harga transaksi terkini pada bursa Cardmarket Eropa. |
| `cardmarket_avg_sell` | `NUMERIC(10,2)` | `NULLABLE` | `13.85` | Rata-rata harga penjualan nyata 30 hari terakhir pada platform Cardmarket. |
| `effective_market_price` | `NUMERIC(10,2)` | `NULLABLE` | `18.50` | **Harga Acuan Pasar Utama ($P_{base}$)** dalam USD. Digunakan sebagai dasar kalkulasi valuasi akhir $P_{final}$ sistem Regokemon. |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` | `'2026-09-20 12:00:00+00'` | Waktu stempel saat harga terakhir disinkronkan ke Supabase. |

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
