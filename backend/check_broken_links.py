import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# 1. Menentukan path direktori file CSV
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "dataset", "pokemon_cards_dataset.csv")

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"File CSV tidak ditemukan di: {csv_path}")

df = pd.read_csv(csv_path)
total_data = len(df)
print(f"Total baris data dalam CSV: {total_data}")

# 2. Konfigurasi Session HTTP untuk pengecekan cepat
session = requests.Session()
retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)
session.mount("http://", adapter)

# 3. Fungsi untuk memeriksa status HTTP dari sebuah URL (menggunakan method HEAD agar lebih cepat)
def check_link(row):
    card_id = row.get('card_id')
    img_url = row.get('images.large')
    
    if pd.isna(img_url):
        return "empty"
    
    try:
        # Menggunakan method HEAD untuk mengecek header tanpa mendownload isi file fisiknya
        response = session.head(img_url, timeout=10)
        if response.status_code == 200:
            return "active"
        else:
            return "broken"
    except Exception:
        return "broken"

# 4. Menjalankan pengecekan paralel menggunakan ThreadPoolExecutor
active_count = 0
broken_count = 0
empty_count = 0

max_workers = 32  # Menggunakan worker lebih banyak karena pengecekan HEAD sangat ringan

print("Memulai pemeriksaan tautan gambar...")
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(check_link, row): row for _, row in df.iterrows()}
    
    with tqdm(total=total_data, desc="Checking Links", unit="link") as pbar:
        for future in as_completed(futures):
            result = future.result()
            if result == "active":
                active_count += 1
            elif result == "broken":
                broken_count += 1
            else:
                empty_count += 1
            pbar.update(1)

print("\n--- HASIL PEMERIKSAAN URL ---")
print(f"Total Baris di CSV   : {total_data}")
print(f"Tautan Aktif (Valid) : {active_count}")
print(f"Tautan Rusak (Broken): {broken_count}")
print(f"Tautan Kosong/NaN    : {empty_count}")
print(f"Jumlah Total Teruji  : {active_count + broken_count + empty_count}")