import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# 1. Menentukan path direktori secara dinamis berdasarkan lokasi file script ini
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "dataset", "pokemon_cards_dataset.csv")

# Folder penyimpanan target (sejajar dengan card-condition-dataset)
output_dir = os.path.join(current_dir, "dataset", "raw_images")
os.makedirs(output_dir, exist_ok=True)

# 2. Cek keberadaan file CSV
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"File CSV tidak ditemukan di: {csv_path}")

df = pd.read_csv(csv_path)
print(f"Total baris data ditemukan di CSV: {len(df)}")

# 3. Konfigurasi Session dengan Retry Strategy agar tahan banting jika ada gangguan jaringan sesaat
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)
session.mount("http://", adapter)

# 4. Fungsi untuk mendownload satu gambar secara efisien
def download_single_image(row):
    card_id = row.get('card_id')
    img_url = row.get('images.large')
    
    # Validasi jika card_id atau url kosong/NaN
    if pd.isna(card_id) or pd.isna(img_url):
        return "skipped"
    
    file_path = os.path.join(output_dir, f"{card_id}.png")
    
    # Jika file sudah pernah terdownload sebelumnya, lewati (mencegah duplikasi & hemat waktu)
    if os.path.exists(file_path):
        return "skipped"
    
    try:
        response = session.get(img_url, timeout=15, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return "success"
        else:
            return "failed"
    except Exception:
        return "failed"

# 5. Menjalankan proses multithreading berkecepatan tinggi dengan Progress Bar (tqdm)
print(f"Memulai unduhan gambar ke folder: {output_dir}")
success_count = 0
skipped_count = 0
failed_count = 0

# Menggunakan 16 worker threads (optimal untuk kecepatan tanpa membebani router/koneksi)
max_workers = 16

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    # Memetakan tugas ke setiap baris dataframe
    futures = {executor.submit(download_single_image, row): row for _, row in df.iterrows()}
    
    # Menampilkan progress bar interaktif di terminal
    with tqdm(total=len(df), desc="Downloading Images", unit="img") as pbar:
        for future in as_completed(futures):
            result = future.result()
            if result == "success":
                success_count += 1
            elif result == "skipped":
                skipped_count += 1
            else:
                failed_count += 1
            pbar.update(1)

print("\n--- RINGKASAN UNDUHAN ---")
print(isi := f"Berhasil diunduh : {success_count} gambar")
print(f"Sudah ada (Lewat) : {skipped_count} gambar")
print(f"Gagal diunduh    : {failed_count} gambar")
print(f"Direktori simpan : {output_dir}")