#!/usr/bin/env python3
"""
=============================================================================
Pokemon Card Value Analytic Tool — Ultra-Efficient Page-Based Ingestion Engine
=============================================================================
Skrip otomatisasi penarikan SELURUH data kartu Pokemon (20.479+ kartu)
dari pokemontcg.io API secara langsung via paginated endpoint:
  - Page size 250 (hanya butuh ~82 request HTTP untuk seluruh 20.479 kartu di dunia)
  - Automatic Retry & Exponential Backoff (kebal crash 502 Bad Gateway / Cloudflare)
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

# Load API Key dari file .env secara otomatis
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv tidak terinstall, tidak apa-apa

BASE_URL = "https://api.pokemontcg.io/v2"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "dataset", "pokemon_cards_dataset.json")
DEFAULT_API_KEY = os.getenv("POKEMONTCG_API_KEY", "")


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
    Membaca dataset lokal jika ada untuk fitur Resumable Download.
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

    # 1. Load data lokal untuk resume
    existing_cards = load_existing_dataset(output_file)
    cards_map = {c["card_id"]: c for c in existing_cards if "card_id" in c}
    tqdm.write(f"ℹ️ Dataset lokal memuat {len(cards_map)} kartu terdaftar.")

    # 2. Cek totalCount kartu langsung dari API
    tqdm.write("🔍 Mengambil total jumlah kartu dari API pokemontcg.io...")
    init_res = fetch_with_retry(f"{BASE_URL}/cards", headers=headers, params={"pageSize": 1})
    if not init_res or "totalCount" not in init_res:
        tqdm.write("❌ Gagal terhubung ke API pokemontcg.io.")
        return

    total_cards_count = init_res["totalCount"]
    page_size = 250
    total_pages = (total_cards_count + page_size - 1) // page_size

    tqdm.write(f"✅ Total kartu di database API: {total_cards_count} kartu.")
    tqdm.write(f"🚀 Memproses {total_pages} halaman (setiap halaman {page_size} kartu)...")

    # 3. Penarikan Paginated Page 1 s/d N
    for page in tqdm(range(1, total_pages + 1), desc="Memproses Halaman"):
        params = {
            "page": page,
            "pageSize": page_size
        }
        res = fetch_with_retry(f"{BASE_URL}/cards", headers=headers, params=params)
        if not res or "data" not in res:
            tqdm.write(f"⚠️ Gagal menarik halaman {page}, melewati...")
            continue

        cards = res.get("data", [])
        new_in_page = 0
        for card in cards:
            card_id = card.get("id")
            if card_id and card_id not in cards_map:
                extracted = extract_relevant_fields(card)
                cards_map[card_id] = extracted
                new_in_page += 1

        # Auto-save per halaman jika ada kartu baru
        if new_in_page > 0:
            save_dataset(list(cards_map.values()), output_file)

        time.sleep(0.15)  # Jeda ramah API

    final_dataset = list(cards_map.values())
    save_dataset(final_dataset, output_file)
    tqdm.write(f"\n✨ Penarikan Selesai! Total {len(final_dataset)} / {total_cards_count} kartu tersimpan di: {output_file}")

    # 4. Opsional: Download Gambar Kartu secara Multi-Threaded
    if download_images:
        download_images_parallel(final_dataset, save_dir="pokemon-cards", max_workers=max_workers)


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
    parser = argparse.ArgumentParser(description="Pokemon Card Page-Based Data Ingestion Engine")
    parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY, help="API Key dari pokemontcg.io (default: dibaca dari backend/.env)")
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
