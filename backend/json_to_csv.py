import os
import json
import pandas as pd

# 1. Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(BASE_DIR, 'dataset')
input_json = os.path.join(dataset_dir, 'pokemon_cards_dataset.json')
output_csv = os.path.join(dataset_dir, 'pokemon_cards_dataset.csv')
cleaned_csv = os.path.join(dataset_dir, 'pokemon_cards_dataset_cleaned.csv')
cleaned_json = os.path.join(dataset_dir, 'pokemon_cards_dataset_cleaned.json')
compressed_img_dir = os.path.join(dataset_dir, 'compressed_images')

if not os.path.exists(input_json):
    raise FileNotFoundError(f"File JSON tidak ditemukan di: {input_json}")

print("1. Memuat data JSON mentah...")
with open(input_json, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

print(f"   Total kartu di JSON mentah: {len(raw_data)}")

# 2. Flatten JSON bersarang
print("2. Melakukan ekstraksi & flattening fitur...")
df = pd.json_normalize(raw_data)

# Meratakan list menjadi string yang dipisahkan koma
for list_col in ['types', 'subtypes']:
    if list_col in df.columns:
        df[list_col] = df[list_col].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

# Konversi HP ke angka (NaN untuk Trainer/Energy/Non-monster)
if 'hp' in df.columns:
    df['hp'] = pd.to_numeric(df['hp'], errors='coerce')

# Ekstraksi release_year dari release_date
if 'set.release_date' in df.columns:
    df['release_year'] = pd.to_datetime(df['set.release_date'], errors='coerce').dt.year

# Konversi kolom-kolom harga ke numerik
price_cols = [
    'prices.tcgplayer_variants.normal.market',
    'prices.tcgplayer_variants.holofoil.market',
    'prices.tcgplayer_variants.reverseHolofoil.market',
    'prices.cardmarket_trend',
    'prices.cardmarket_avg_sell'
]
for col in price_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        df[col] = None

# Kalkulasi effective_market_price (Hierarki: normal -> holofoil -> reverseHolofoil -> trend -> avg_sell)
df['effective_market_price'] = (
    df['prices.tcgplayer_variants.normal.market']
    .fillna(df['prices.tcgplayer_variants.holofoil.market'])
    .fillna(df['prices.tcgplayer_variants.reverseHolofoil.market'])
    .fillna(df['prices.cardmarket_trend'])
    .fillna(df['prices.cardmarket_avg_sell'])
)

# 3. Pilih dan susun kolom-kolom penting
kolom_pilihan = [
    'card_id', 'name', 'supertype', 'subtypes', 'types', 'hp', 'number', 'rarity', 'artist',
    'set.id', 'set.name', 'set.series', 'set.release_date', 'release_year',
    'images.small', 'images.large',
    'prices.tcgplayer_variants.normal.market',
    'prices.tcgplayer_variants.holofoil.market',
    'prices.tcgplayer_variants.reverseHolofoil.market',
    'prices.cardmarket_trend',
    'prices.cardmarket_avg_sell',
    'effective_market_price'
]

kolom_tersedia = [c for c in kolom_pilihan if c in df.columns]
df_final = df[kolom_tersedia]

# Ekspor CSV mentah lengkap
df_final.to_csv(output_csv, index=False)
print(f"   CSV mentah berhasil diperbarui ({len(df_final)} baris): {output_csv}")

# 4. Sinkronisasi Data Bersih (Filtering Link Mati / Gambar Terunduh)
print("3. Menyinkronkan dataset bersih (link aktif & gambar fisik ada)...")

valid_card_ids = set()
if os.path.exists(compressed_img_dir):
    # Mengambil ID dari gambar yang berhasil dikompres ke JPG
    valid_card_ids = {os.path.splitext(f)[0] for f in os.listdir(compressed_img_dir) if f.endswith('.jpg')}
    print(f"   Ditemukan {len(valid_card_ids)} gambar valid di folder compressed_images.")

if valid_card_ids:
    df_cleaned = df_final[df_final['card_id'].isin(valid_card_ids)].reset_index(drop=True)
    raw_data_cleaned = [item for item in raw_data if item.get('card_id') in valid_card_ids]
else:
    # Fallback ke dataset yang sudah ada jika folder gambar tidak ditemukan
    df_cleaned = df_final
    raw_data_cleaned = raw_data

# Ekspor CSV Bersih
df_cleaned.to_csv(cleaned_csv, index=False)
print(f"   CSV Bersih (Cleaned) berhasil disimpan ({len(df_cleaned)} baris): {cleaned_csv}")

# Ekspor JSON Bersih
with open(cleaned_json, 'w', encoding='utf-8') as f:
    json.dump(raw_data_cleaned, f, ensure_ascii=False, indent=2)
print(f"   JSON Bersih (Cleaned) berhasil disimpan ({len(raw_data_cleaned)} item): {cleaned_json}")

print("\n✨ PROSES KONVERSI & SINKRONISASI SELESAI!")
print(f"   • Total Fitur di CSV  : {len(kolom_tersedia)} kolom")
print(f"   • Coverage Harga      : {df_cleaned['effective_market_price'].notna().sum()} / {len(df_cleaned)} ({df_cleaned['effective_market_price'].notna().mean()*100:.2f}%)")