"""
export_broken_links.py
======================
Memeriksa semua tautan gambar di pokemon_cards_dataset.csv secara paralel
dan mengekspor HANYA baris yang link-nya rusak ke:

    backend/dataset/broken_links_report.csv

Kolom output: card_id, name, number, rarity, set.name, set.series,
              set.release_date, images.large, status
"""

import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# ---------- Paths ----------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_IN      = os.path.join(CURRENT_DIR, "dataset", "pokemon_cards_dataset.csv")
CSV_OUT     = os.path.join(CURRENT_DIR, "dataset", "broken_links_report.csv")

if not os.path.exists(CSV_IN):
    raise FileNotFoundError(f"File CSV tidak ditemukan di: {CSV_IN}")

df = pd.read_csv(CSV_IN)
print(f"Total baris data dalam CSV : {len(df)}")

# ---------- HTTP Session ----------
session  = requests.Session()
retries  = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter  = HTTPAdapter(max_retries=retries, pool_connections=64, pool_maxsize=64)
session.mount("https://", adapter)
session.mount("http://",  adapter)


def check_link(row_tuple):
    idx, row = row_tuple
    img_url  = row.get("images.large")
    if pd.isna(img_url):
        return idx, "empty"
    try:
        resp = session.head(img_url, timeout=10, allow_redirects=True)
        return idx, ("active" if resp.status_code == 200 else "broken")
    except Exception:
        return idx, "broken"


# ---------- Parallel check ----------
print("Memulai pemeriksaan tautan gambar secara paralel...")
results = {}

rows_iter = list(df.iterrows())
with ThreadPoolExecutor(max_workers=64) as executor:
    futures = {executor.submit(check_link, item): item[0] for item in rows_iter}
    with tqdm(total=len(rows_iter), desc="Checking Links", unit="link") as pbar:
        for future in as_completed(futures):
            idx, status = future.result()
            results[idx] = status
            pbar.update(1)

# ---------- Summary ----------
active_count = sum(1 for s in results.values() if s == "active")
broken_count = sum(1 for s in results.values() if s == "broken")
empty_count  = sum(1 for s in results.values() if s == "empty")

print("\n--- HASIL PEMERIKSAAN URL ---")
print(f"Total Baris di CSV   : {len(df)}")
print(f"Tautan Aktif (Valid) : {active_count}")
print(f"Tautan Rusak (Broken): {broken_count}")
print(f"Tautan Kosong/NaN    : {empty_count}")

# ---------- Export broken rows ----------
broken_indices = [idx for idx, status in results.items() if status in ("broken", "empty")]

EXPORT_COLS = ["card_id", "name", "number", "rarity",
               "set.name", "set.series", "set.release_date", "images.large"]
export_cols_present = [c for c in EXPORT_COLS if c in df.columns]

df_broken = df.loc[broken_indices, export_cols_present].copy()
df_broken["status"] = [results[i] for i in broken_indices]

df_broken.to_csv(CSV_OUT, index=False, encoding="utf-8")

print(f"\nBerkas laporan link rusak tersimpan di:")
print(f"  {CSV_OUT}")
print(f"  ({len(df_broken)} baris)")
