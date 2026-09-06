import pandas as pd
import json
import os

# Mendapatkan jalur absolut dari direktori tempat script ini berada (yaitu folder 'backend')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Menentukan jalur folder dan nama file
dataset_dir = os.path.join(BASE_DIR, 'dataset')
input_file = os.path.join(dataset_dir, 'pokemon_cards_dataset.json')
output_file = os.path.join(dataset_dir, 'pokemon_cards_dataset.csv')

# 1. Memuat data JSON dari folder dataset
with open(input_file, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 2. Meratakan (Flattening) JSON bersarang secara otomatis
df = pd.json_normalize(raw_data)

# 3. Menangani kolom berformat List (seperti types dan subtypes)
if 'types' in df.columns:
    df['types'] = df['types'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
if 'subtypes' in df.columns:
    df['subtypes'] = df['subtypes'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

# 4. Membersihkan tipe data harga (Memastikan semuanya Float/Numerik)
price_columns = [
    'prices.cardmarket_trend',
    'prices.cardmarket_avg_sell',
    'prices.tcgplayer_variants.normal.market',
    'prices.tcgplayer_variants.holofoil.market',
    'prices.tcgplayer_variants.reverseHolofoil.market'
]

for col in price_columns:
    if col in df.columns:
        # Menggunakan errors='coerce' agar karakter non-numerik otomatis menjadi NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')

# 5. Memilih kolom esensial untuk diekspor
kolom_pilihan = [
    'card_id', 'name', 'number', 'rarity', 'types', 
    'set.name', 'set.release_date', 'images.large',
    'prices.cardmarket_trend', 'prices.tcgplayer_variants.holofoil.market'
]

kolom_akhir = [col for col in kolom_pilihan if col in df.columns]
df_final = df[kolom_akhir]

# 6. Ekspor ke CSV ke dalam folder dataset
df_final.to_csv(output_file, index=False)
print(f"Data berhasil dibersihkan dan diekspor ke: {output_file}")