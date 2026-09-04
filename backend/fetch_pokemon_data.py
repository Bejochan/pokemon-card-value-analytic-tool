#!/usr/bin/env python3
"""
=============================================================================
Pokemon Card Value Analytic Tool — Efficient Data Ingestion Engine
=============================================================================
Skrip otomatisasi penarikan seluruh data kartu Pokemon (18.000+ kartu, 160+ set)
dari pokemontcg.io API dengan efisiensi maksimal:
  - Page size 250 (meminimalkan HTTP round-trip ke ~70 request)
  - Automatic Retry & Exponential Backoff (bebas crash dari 502 Bad Gateway)
  - Resumable Checkpoint (bisa dilanjutkan jika terputus di tengah jalan)
  - Multi-threaded Image Downloader (opsional)
=============================================================================
"""

import os
import sys
import json
import time
import argparse
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://api.pokemontcg.io/v2"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "dataset", "pokemon_cards_dataset.json")


def fetch_with_retry(url, headers=None, params=None, max_retries=5, backoff_factor=1.5):
    """
    Melakukan request HTTP dengan retry otomatis jika mengalami rate limit (429)
    atau server error (500, 502, 503, 504).
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [429, 500, 502, 503, 504]:
                wait_time = backoff_factor ** attempt
                tqdm.write(f"⚠️ [HTTP {response.status_code}] Retry {attempt}/{max_retries} dalam {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                tqdm.write(f"❌ [HTTP {response.status_code}] Gagal: {response.text[:100]}")
                break
        except Exception as e:
            wait_time = backoff_factor ** attempt
            tqdm.write(f"⚠️ [Network Error] {e}. Retry {attempt}/{max_retries} dalam {wait_time:.1f}s...")
            time.sleep(wait_time)
    return None


def fetch_all_sets(headers=None):
    """
    Mengambil daftar seluruh set kartu Pokemon yang tersedia di API.
    """
    tqdm.write("🔍 Mengambil daftar seluruh set kartu dari API...")
    data = fetch_with_retry(f"{BASE_URL}/sets", headers=headers, params={"pageSize": 250})
    if not data or "data" not in data:
        tqdm.write("❌ Gagal mendapatkan daftar set.")
        return []
    
    sets = data["data"]
    tqdm.write(f"✅ Ditemukan total {len(sets)} set kartu.")
    return sets


def extract_relevant_fields(card):
    """
    Mengekstrak hanya field relevan untuk efisiensi penyimpanan & analitika data.
    """
    tcgplayer = card.get("tcgplayer") or {}
    tcg_prices = tcgplayer.get("prices") or {}

    cardmarket = card.get("cardmarket") or {}
    cm_prices = cardmarket.get("prices") or {}

    tcg_variant = {}
    for variant_name, variant_data in tcg_prices.items():
        if isinstance(variant_data, dict):
            tcg_variant[variant_name] = {
                "low": variant_data.get("low"),
                "mid": variant_data.get("mid"),
                "high": variant_data.get("high"),
                "market": variant_data.get("market"),
            }

    return {
        "card_id": card.get("id"),
        "name": card.get("name"),
        "number": card.get("number"),
        "rarity": card.get("rarity"),
        "supertype": card.get("supertype"),
        "subtypes": card.get("subtypes") or [],
        "types": card.get("types") or [],
        "hp": card.get("hp"),
        "artist": card.get("artist"),
        "set": {
            "id": (card.get("set") or {}).get("id"),
            "name": (card.get("set") or {}).get("name"),
            "series": (card.get("set") or {}).get("series"),
            "release_date": (card.get("set") or {}).get("releaseDate"),
            "total_cards": (card.get("set") or {}).get("printedTotal"),
        },
        "images": {
            "small": (card.get("images") or {}).get("small"),
            "large": (card.get("images") or {}).get("large"),
        },
        "prices": {
            "tcgplayer_url": tcgplayer.get("url"),
            "tcgplayer_updated": tcgplayer.get("updatedAt"),
            "tcgplayer_variants": tcg_variant,
            "cardmarket_url": cardmarket.get("url"),
            "cardmarket_updated": cardmarket.get("updatedAt"),
            "cardmarket_avg_sell": cm_prices.get("averageSellPrice"),
            "cardmarket_trend": cm_prices.get("trendPrice"),
            "cardmarket_avg1": cm_prices.get("avg1"),
            "cardmarket_avg7": cm_prices.get("avg7"),
            "cardmarket_avg30": cm_prices.get("avg30"),
        }
    }


def load_existing_dataset(output_file):
    """
    Membaca dataset lokal jika ada untuk fitur Resumable Download (Skip set/kartu yang sudah ditarik).
    """
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_dataset(data, output_file):
    """
    Menyimpan dataset secara aman ke file JSON (Checkpointing).
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    temp_file = output_file + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, output_file)


def run_pipeline(api_key=None, output_file=DEFAULT_OUTPUT, download_images=False, max_workers=8):
    headers = {"X-Api-Key": api_key} if api_key else {}

    # 1. Load data yang sudah ada untuk resume
    existing_cards = load_existing_dataset(output_file)
    existing_ids = {c["card_id"] for c in existing_cards if "card_id" in c}
    tqdm.write(f"ℹ️ Dataset lokal memuat {len(existing_cards)} kartu terdaftar.")

    # 2. Ambil seluruh set
    all_sets = fetch_all_sets(headers=headers)
    if not all_sets:
        tqdm.write("❌ Proses dibatalkan karena gagal mengambil set.")
        return

    # 3. Penarikan kartu per set dengan efisiensi maksimal
    extracted_cards = list(existing_cards)
    cards_map = {c["card_id"]: c for c in extracted_cards}

    total_new_added = 0
    tqdm.write(f"\n🚀 Memulai penarikan kartu dari {len(all_sets)} set...")

    for set_obj in tqdm(all_sets, desc="Memproses Set"):
        set_id = set_obj["id"]
        set_name = set_obj["name"]
        printed_total = set_obj.get("printedTotal", 0)

        # Cek apakah kartu dari set ini sudah lengkap ter-cache di lokal
        page = 1
        set_new_count = 0

        while True:
            params = {
                "q": f"set.id:{set_id}",
                "page": page,
                "pageSize": 250  # Ukuran maksimal per request
            }
            res = fetch_with_retry(f"{BASE_URL}/cards", headers=headers, params=params)
            if not res or "data" not in res:
                break

            cards = res.get("data", [])
            if not cards:
                break

            for card in cards:
                card_id = card.get("id")
                if card_id not in cards_map:
                    extracted = extract_relevant_fields(card)
                    cards_map[card_id] = extracted
                    existing_ids.add(card_id)
                    set_new_count += 1

            page += 1
            time.sleep(0.15)  # Jeda ramah API

        if set_new_count > 0:
            total_new_added += set_new_count
            # Auto-save / checkpoint per set
            save_dataset(list(cards_map.values()), output_file)

    final_dataset = list(cards_map.values())
    save_dataset(final_dataset, output_file)
    tqdm.write(f"\n✨ Penarikan Selesai! Total {len(final_dataset)} kartu tersimpan di: {output_file}")

    # 4. Opsional: Download Gambar Kartu secara Multi-Threaded
    if download_images:
        download_images_parallel(final_dataset, max_workers=max_workers)


def download_single_image(card, save_dir):
    img_url = (card.get("images") or {}).get("large")
    if not img_url:
        return
    card_id = card["card_id"]
    save_path = os.path.join(save_dir, f"{card_id}.png")
    
    if os.path.exists(save_path):
        return

    try:
        resp = requests.get(img_url, timeout=12)
        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(resp.content)
    except Exception:
        pass


def download_images_parallel(cards, save_dir="pokemon-cards", max_workers=8):
    os.makedirs(save_dir, exist_ok=True)
    tqdm.write(f"\n🖼️ Memulai download {len(cards)} gambar kartu ({max_workers} threads)...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(
            executor.map(lambda c: download_single_image(c, save_dir), cards),
            total=len(cards),
            desc="Downloading Gambar"
        ))
    tqdm.write(f"✅ Download gambar selesai di folder: {save_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pokemon Card Data Ingestion Engine")
    parser.add_argument("--api-key", type=str, default="", help="API Key dari pokemontcg.io")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Path berkas output JSON")
    parser.add_argument("--download-images", action="store_true", help="Download seluruh gambar kartu secara paralel")
    parser.add_argument("--workers", type=int, default=8, help="Jumlah thread paralel download gambar")

    args = parser.parse_args()
    run_pipeline(
        api_key=args.api_key,
        output_file=args.output,
        download_images=args.download_images,
        max_workers=args.workers
    )
