# 📚 Kamus Data & Dokumentasi Dataset (Dataset Dictionary)

> **Pokemon Card Value Analytic Tool (PokeScan)**  
> **Berkas Dataset:** `backend/dataset/pokemon_cards_dataset_cleaned.csv`  
> **Versi Dataset:** 2.0 (Cleaned & Synchronized)  
> **Jumlah Baris:** 19.926 Kartu (100% Konsisten dengan Gambar Fisik `compressed_images/*.jpg`)  
> **Jumlah Fitur:** 22 Kolom Fitur  

---

## 📌 1. Skema & Kamus Variabel Fitur (Data Dictionary)

Berikut adalah rincian 22 variabel fitur yang ada di dalam berkas `pokemon_cards_dataset_cleaned.csv`:

| No | Nama Kolom Fitur | Tipe Data | Deskripsi & Contoh | Keterangan & Aturan Nilai Kosong (*NaN*) |
|---|---|:---:|---|---|
| 1 | `card_id` | `String` | ID unik kartu Pokémon.<br>*(Contoh: `base1-4`, `ex10-?`)* | **Primary Key**. Format: `{set_id}-{number}`. Tidak boleh kosong (0% NaN). |
| 2 | `name` | `String` | Nama resmi kartu.<br>*(Contoh: `Charizard`, `Aggron`)* | Nama karakter/item/energi. Tidak boleh kosong (0% NaN). |
| 3 | `supertype` | `String` | Kategori utama tipe kartu.<br>*(Nilai: `Pokémon`, `Trainer`, `Energy`)* | Mengikuti aturan resmi game TCG. Tidak boleh kosong (0% NaN). |
| 4 | `subtypes` | `String` | Sub-kategori klasifikasi kartu.<br>*(Contoh: `Basic`, `Stage 1`, `VMAX`, `Supporter`)* | Menggambarkan tahap evolusi atau jenis spesifik kartu. |
| 5 | `types` | `String` | Tipe elemen energi Pokémon.<br>*(Contoh: `Fire`, `Water`, `Grass, Metal`)* | **Domain Knowledge Rule:** Kosong (*NaN*) untuk kartu `Trainer` dan `Energy`. |
| 6 | `hp` | `Float` | Hit Points (Poin Nyawa/Darah) Pokémon.<br>*(Contoh: `60.0`, `120.0`, `330.0`)* | **Domain Knowledge Rule:** Kosong (*NaN*) untuk kartu `Trainer` dan `Energy`. |
| 7 | `number` | `String` | Nomor urut koleksi dalam set edisi.<br>*(Contoh: `4`, `102/165`, `?`)* | Nomor kartu. Kartu edisi spesial **Unown ?** memiliki nomor `?`. |
| 8 | `rarity` | `String` | Tingkat kelangkaan kartu.<br>*(Contoh: `Common`, `Rare Holo`, `Ultra Rare`)* | Penentu utama pengali harga pasar wajar ($M_{variant}$). |
| 9 | `artist` | `String` | Nama ilustrator/seniman pembuat gambar.<br>*(Contoh: `Mitsuhiro Arita`, `Kyoko Koizumi`)* | Nama pelukis kartu. Sebagian kartu lama tidak mencantumkan artist. |
| 10 | `set.id` | `String` | ID unik edisi ekspansi set.<br>*(Contoh: `base1`, `ex10`, `sv3pt5`)* | Kode singkatan set edisi resmi. |
| 11 | `set.name` | `String` | Nama lengkap edisi ekspansi set.<br>*(Contoh: `Base`, `Unseen Forces`, `151`)* | Nama resmi seri peluncuran kartu. |
| 12 | `set.series` | `String` | Edisi era generasi Pokémon.<br>*(Contoh: `Base`, `EX`, `Diamond & Pearl`, `Scarlet & Violet`)* | Pengelompokan generasi rilis TCG. |
| 13 | `set.release_date` | `Date/Str` | Tanggal rilis resmi set edisi.<br>*(Format: `YYYY/MM/DD`, Contoh: `1999/01/09`)* | Digunakan untuk mengidentifikasi era rilis kartu. |
| 14 | `release_year` | `Integer` | Tahun rilis resmi edisi ekspansi.<br>*(Contoh: `1999`, `2005`, `2024`)* | **Vintage Factor Rule:** Tahun $< 2005$ dikategorikan sebagai kartu Vintage. |
| 15 | `images.small` | `String` | URL tautan gambar sampel kecil (thumbnail). | Diambil langsung dari pokemontcg.io API. |
| 16 | `images.large` | `String` | URL tautan gambar master resolusi tinggi. | Tautan acuan unduhan berkas master gambar. |
| 17 | `prices.tcgplayer_variants.normal.market` | `Float` | Harga pasar harian varian biasa (non-holo) di TCGPlayer ($ USD). | *NaN* jika kartu tersebut tidak memiliki varian biasa. |
| 18 | `prices.tcgplayer_variants.holofoil.market` | `Float` | Harga pasar harian varian Holofoil di TCGPlayer ($ USD). | *NaN* jika kartu tersebut tidak memiliki varian Holofoil. |
| 19 | `prices.tcgplayer_variants.reverseHolofoil.market` | `Float` | Harga pasar harian varian Reverse Holofoil di TCGPlayer ($ USD). | *NaN* jika kartu tersebut tidak memiliki varian Reverse Holo. |
| 20 | `prices.cardmarket_trend` | `Float` | Tren harga pasar Eropa di Cardmarket (€ EUR / USD). | Indikator tren pergerakan harga dari pasar Cardmarket. |
| 21 | `prices.cardmarket_avg_sell` | `Float` | Rata-rata harga penjualan 30 hari terakhir di Cardmarket. | Indikator riwayat transaksi fisik kartu. |
| 22 | `effective_market_price` | `Float` | **Harga Dasar Pasar Utama ($P_{base}$)**.<br>*(Satuan: $ USD)* | **Target Variabel Valuasi**. Kombinasi TCGPlayer & Cardmarket (96.29% coverage). |

---

## 💡 2. Aturan Domain Knowledge & Data Integrity

### A. Alasan Terjadinya *Missing Values* (Data Kosong)
Berdasarkan hasil Data Quality Audit pada 19.926 kartu:
1. **`types` (Kosong pada 3.078 baris) & `hp` (Kosong pada 3.047 baris):**
   * **Bukan Error/Typo:** Kartu ber-supertype `Trainer` (2.718 kartu) dan `Energy` (373 kartu) secara resmi di dalam aturan Pokémon TCG **tidak memiliki poin HP maupun tipe elemen**.
   * Kartu `Pokémon` (16.835 kartu) memiliki data `types` dan `hp` **100% lengkap**.
2. **`effective_market_price` (Kosong pada 740 baris / 3.71%):**
   * Kartu yang tidak memiliki harga umumnya merupakan kartu edisi khusus promo lawas atau kartu yang tidak pernah diperjualbelikan secara umum di marketplace.
   * **Strategi Fallback Backend:** Saat kalkulasi $P_{final}$, jika `effective_market_price` bernilai *NaN*, engine akan menggunakan *median price* dari kelompok `rarity` dan `release_year` yang sejenis.

### B. Penanganan Kasus Khusus File System (Windows Reserved Character)
* **Kasus Kartu Unown ? (`ex10-?`):**
  Kartu edisi *Unseen Forces (2005)* ini memiliki nomor resmi `?`. Karena karakter `?` dilarang oleh Windows File System (`< > : " / \ | ? *`), gambar kartu diunduh dan disimpan dengan nama **`question_hires.jpg`**.
* **Solusi Pemetaan:** Skrip `json_to_csv.py` secara otomatis memetakan `question_hires.jpg` $\leftrightarrow$ `ex10-?` sehingga seluruh 19.926 kartu sinkron 1-to-1 secara sempurna.

---

## ⚙️ 3. Integrasi Fitur Terhadap AI Engine & Valuasi

```text
[ Fitur CSV / JSON ] ───► [ Variabel Perhitungan ] ───► [ Formula Valuation ]
1. effective_market_price ──► P_base (Harga Pasar)  ──┐
2. release_year (< 2005)  ──► M_vintage (+20-50%)   ├──► P_final = P_base * M_variant * F_condition * F_market
3. rarity (Secret/Holo)   ──► M_rarity (+15-35%)    ──┘
```

1. **Model 1: Card Identifier (FAISS Vector Search):**
   - Menghubungkan hasil pencarian visual FAISS (berdasarkan `compressed_images/*.jpg`) kembali ke `card_id` pada CSV ini untuk menarik seluruh informasi metadata kartu.
2. **Model 2: Condition Grader (YOLOv8):**
   - Menghasilkan pengali kondisi fisik ($F_{condition}$) yang memotong nilai dari $P_{base}$ di CSV.
3. **Analytics Valuation Engine:**
   - Menggunakan `effective_market_price`, `release_year`, dan `rarity` untuk menghitung deviasi penawaran penjual di marketplace dan menghasilkan sinyal **BUY**, **HOLD**, atau **SELL**.
