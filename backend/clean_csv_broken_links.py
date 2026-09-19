import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# 1. Menentukan path direktori file CSV secara dinamis
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "dataset", "pokemon_cards_dataset.csv")
cleaned_csv_path = os.path.join(current_dir, "dataset", "pokemon_cards_dataset_cleaned.csv")

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"File CSV tidak ditemukan di: {csv_path}")

df = pd.read_csv(csv_path)
print(f"Total baris awal dalam CSV: {len(df)}")

# 2. Konfigurasi Session HTTP untuk pengecekan cepat
session = requests.Session()
retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)
session.mount("http://", adapter)

# 3. Fungsi untuk mengecek validitas link baris data
def check_link_status(row):
    idx = row.name
    img_url = row.get('images.large')
    
    if pd.isna(img_url):
        return idx, False
    
    try:
        response = session.head(img_url, timeout=10)
        if response.status_code == 200:
            return idx, True
        else:
            return idx, False
    except Exception:
        return idx, False

# 4. Menjalankan pemeriksaan paralel menggunakan ThreadPoolExecutor
valid_indices = []
max_workers = 32

print("Memeriksa tautan dan memfilter baris yang rusak...")
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(check_link_status, row) for _, row in df.iterrows()]
    
    with tqdm(total=len(df), desc="Cleaning CSV", unit="row") as pbar:
        for future in as_completed(futures):
            idx, is_valid = future.result()
            if is_valid:
                valid_indices.append(idx)
            pbar.update(1)

# Menyaring dataframe hanya untuk baris yang link-nya aktif/valid
df_cleaned = df.loc[sorted(valid_indices)].reset_index(drop=True)

# Menyimpan file CSV baru yang sudah bersih
df_cleaned.to_csv(cleaned_csv_path, index=False)

print("\n--- RINGKASAN PEMBERSIHAN CSV ---")
print(f"Baris awal di CSV                : {len(df)}")
print(f"Baris valid tersisa (aktif)      : {len(df_cleaned)}")
print(f"Baris dihapus (link rusak/mati)  : {len(df) - len(df_cleaned)}")
print(f"File bersih tersimpan di         : {cleaned_csv_path}")