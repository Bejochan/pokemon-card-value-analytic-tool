import os
import time
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

import sys
# Pastikan terminal Windows tidak crash saat print karakter/emoji
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Pastikan SUPABASE_URL dan SUPABASE_KEY sudah terisi di backend/.env!")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"  # UPSERT mode
}

CSV_PATH = os.path.join(BASE_DIR, "dataset", "pokemon_cards_dataset_cleaned.csv")

def check_tables_exist():
    """Memeriksa apakah tabel sets, cards, dan card_prices sudah dibuat di Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/"
    res = requests.get(url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    if res.status_code != 200:
        print(f"[error] Gagal mengakses REST API Supabase: {res.status_code} - {res.text}")
        return False
    
    definitions = res.json().get("definitions", {})
    required = ["sets", "cards", "card_prices"]
    missing = [t for t in required if t not in definitions]
    
    if missing:
        print(f"\n[PERINGATAN] Tabel berikut belum dibuat di Supabase: {missing}")
        print("Silakan jalankan file SQL 'backend/schema.sql' di SQL Editor dashboard Supabase terlebih dahulu!")
        return False
    return True

def upload_batch(endpoint, records, batch_size=500):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    total = len(records)
    
    for i in tqdm(range(0, total, batch_size), desc=f"Uploading {endpoint}"):
        batch = records[i:i + batch_size]
        res = requests.post(url, headers=HEADERS, json=batch)
        if res.status_code not in (200, 201):
            print(f"\n[error] Gagal upload batch {i}-{i+len(batch)} ke '{endpoint}': {res.status_code}")
            print(res.text[:300])
            return False
        time.sleep(0.05)  # slight delay to be gentle on connection
    return True

def main():
    print("=" * 60)
    print("🚀 SEEDING DATASET KE SUPABASE (SETS, CARDS, CARD_PRICES)")
    print(f"URL Supabase: {SUPABASE_URL}")
    print("=" * 60)

    if not check_tables_exist():
        return

    print("\n1. Membaca dataset CSV...")
    df = pd.read_csv(CSV_PATH)
    print(f"   Total baris data: {len(df):,}")

    # -------------------------------------------------------------
    # A. Ekstrak & Upload Tabel SETS
    # -------------------------------------------------------------
    print("\n2. Mempersiapkan data SETS...")
    df_sets = df[["set.id", "set.name", "set.series", "set.release_date", "release_year"]].drop_duplicates(subset=["set.id"]).copy()
    df_sets.rename(columns={
        "set.id": "set_id",
        "set.name": "name",
        "set.series": "series",
        "set.release_date": "release_date",
        "release_year": "release_year"
    }, inplace=True)
    
    # Format release_date ke YYYY-MM-DD
    df_sets["release_date"] = pd.to_datetime(df_sets["release_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df_sets = df_sets.replace({np.nan: None})
    records_sets = df_sets.to_dict(orient="records")
    print(f"   Total set unik: {len(records_sets)}")
    
    if not upload_batch("sets", records_sets, batch_size=200):
        print("Gagal seeding tabel sets. Proses dihentikan.")
        return
    print("   ✅ Tabel 'sets' berhasil di-upload!")

    # -------------------------------------------------------------
    # B. Ekstrak & Upload Tabel CARDS
    # -------------------------------------------------------------
    print("\n3. Mempersiapkan data CARDS...")
    df_cards = df[[
        "card_id", "name", "supertype", "subtypes", "types",
        "hp", "number", "rarity", "artist", "set.id",
        "images.small", "images.large"
    ]].copy()
    
    df_cards.rename(columns={
        "set.id": "set_id",
        "images.small": "image_small",
        "images.large": "image_large"
    }, inplace=True)
    
    df_cards = df_cards.replace({np.nan: None})
    records_cards = df_cards.to_dict(orient="records")
    print(f"   Total kartu: {len(records_cards):,}")

    if not upload_batch("cards", records_cards, batch_size=500):
        print("Gagal seeding tabel cards. Proses dihentikan.")
        return
    print("   ✅ Tabel 'cards' berhasil di-upload!")

    # -------------------------------------------------------------
    # C. Ekstrak & Upload Tabel CARD_PRICES
    # -------------------------------------------------------------
    print("\n4. Mempersiapkan data CARD_PRICES...")
    df_prices = df[[
        "card_id",
        "prices.tcgplayer_variants.normal.market",
        "prices.tcgplayer_variants.holofoil.market",
        "prices.tcgplayer_variants.reverseHolofoil.market",
        "prices.cardmarket_trend",
        "prices.cardmarket_avg_sell",
        "effective_market_price"
    ]].copy()

    df_prices.rename(columns={
        "prices.tcgplayer_variants.normal.market": "tcg_normal_market",
        "prices.tcgplayer_variants.holofoil.market": "tcg_holo_market",
        "prices.tcgplayer_variants.reverseHolofoil.market": "tcg_reverse_market",
        "prices.cardmarket_trend": "cardmarket_trend",
        "prices.cardmarket_avg_sell": "cardmarket_avg_sell",
        "effective_market_price": "effective_market_price"
    }, inplace=True)

    df_prices = df_prices.replace({np.nan: None})
    records_prices = df_prices.to_dict(orient="records")
    print(f"   Total data harga kartu: {len(records_prices):,}")

    if not upload_batch("card_prices", records_prices, batch_size=500):
        print("Gagal seeding tabel card_prices. Proses dihentikan.")
        return
    print("   ✅ Tabel 'card_prices' berhasil di-upload!")

    print("\n" + "=" * 60)
    print("🎉 SEMUA DATA BERHASIL DI-SEED KE SUPABASE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
