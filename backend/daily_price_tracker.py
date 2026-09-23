#!/usr/bin/env python3
"""
Regokemon Daily Price Tracker & Ingestion Engine
================================================
Menarik snapshot harga harian secara otomatis dari pokemontcg.io API (TCGPlayer & Cardmarket),
mengekstrak metrik harga likuiditas (low, mid, high, market) dan time-series (avg1, avg7, avg30),
kemudian menyimpannya ke Supabase:
  1. Tabel `card_prices` (Update snapshot harga terkini untuk live search & valuasi)
  2. Tabel `card_price_history` (Upsert histori harga harian per tanggal YYYY-MM-DD)

Dapat dijalankan secara mandiri lokal maupun otomatis via GitHub Actions cron harian.
"""

import os
import sys
import time
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm

# Encoding UTF-8 untuk stdout terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables (.env jika ada)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass

POKEMONTCG_API_KEY = os.getenv("POKEMONTCG_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

POKEMONTCG_BASE_URL = "https://api.pokemontcg.io/v2"


def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }


def fetch_valid_card_ids():
    """
    Mengambil daftar seluruh `card_id` yang terdaftar di tabel `cards` Supabase.
    Hal ini penting guna memastikan integritas foreign-key (FK) tidak bentrok jika
    ada kartu baru rilis di pokemontcg.io yang belum di-seed ke tabel `cards`.
    """
    print("🔍 Mengambil daftar card_id terdaftar dari Supabase...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    
    valid_ids = set()
    offset = 0
    limit = 1000
    
    while True:
        url = f"{SUPABASE_URL}/rest/v1/cards?select=card_id&order=card_id.asc&offset={offset}&limit={limit}"
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                batch = r.json()
                if not batch:
                    break
                for row in batch:
                    valid_ids.add(row["card_id"])
                offset += len(batch)
                if len(batch) < limit:
                    break
            else:
                print(f"⚠️ Peringatan: Gagal mengambil batch card_id (HTTP {r.status_code}): {r.text[:100]}")
                break
        except Exception as e:
            print(f"⚠️ Error koneksi ke Supabase: {e}")
            break
            
    print(f"   ✅ Ditemukan {len(valid_ids):,} kartu master terdaftar di database Supabase.")
    return valid_ids


def fetch_page_with_retry(page_num, page_size=250, max_retries=5, backoff_factor=2.0):
    """
    Menarik 1 halaman data kartu (hanya id, tcgplayer, cardmarket) dengan retry otomatis.
    """
    url = f"{POKEMONTCG_BASE_URL}/cards"
    params = {
        "page": page_num,
        "pageSize": page_size,
        "select": "id,tcgplayer,cardmarket"
    }
    headers = {}
    if POKEMONTCG_API_KEY:
        headers["X-Api-Key"] = POKEMONTCG_API_KEY

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=25)
            if r.status_code == 200:
                data = r.json()
                return page_num, data.get("data", []), data.get("totalCount", 0)
            elif r.status_code in [429, 500, 502, 503, 504]:
                wait_time = backoff_factor ** attempt
                time.sleep(wait_time)
            else:
                tqdm.write(f"❌ [HTTP {r.status_code}] Gagal di halaman {page_num}")
                break
        except Exception as e:
            wait_time = backoff_factor ** attempt
            time.sleep(wait_time)

    return page_num, [], 0


def calculate_effective_price(prices):
    """
    Menentukan harga pasar efektif dengan prioritas:
    normal.market -> holofoil.market -> reverse.market -> cardmarket.trend -> avg_sell -> avg1 -> mid.
    """
    candidates = [
        prices.get("tcg_normal_market"),
        prices.get("tcg_holo_market"),
        prices.get("tcg_reverse_market"),
        prices.get("cardmarket_trend"),
        prices.get("cardmarket_avg_sell"),
        prices.get("cardmarket_avg1"),
        prices.get("tcg_normal_mid"),
        prices.get("tcg_holo_mid"),
    ]
    for val in candidates:
        if val is not None and val > 0:
            return round(float(val), 2)
    return None


def extract_card_price_record(card):
    """
    Mengekstrak seluruh metrik likuiditas dan time-series dari data TCGPlayer & Cardmarket.
    """
    card_id = card.get("id")
    if not card_id:
        return None

    tcg = card.get("tcgplayer") or {}
    tcg_prices = tcg.get("prices") or {}

    normal = tcg_prices.get("normal") or {}
    holo = tcg_prices.get("holofoil") or {}
    reverse = tcg_prices.get("reverseHolofoil") or {}

    cm = card.get("cardmarket") or {}
    cm_prices = cm.get("prices") or {}

    def _safe_float(val):
        if val is not None:
            try:
                f = float(val)
                return round(f, 2) if f > 0 else 0.0
            except (ValueError, TypeError):
                pass
        return None

    record = {
        "card_id": card_id,
        "tcg_normal_market": _safe_float(normal.get("market")),
        "tcg_normal_low": _safe_float(normal.get("low")),
        "tcg_normal_mid": _safe_float(normal.get("mid")),
        "tcg_normal_high": _safe_float(normal.get("high")),
        "tcg_holo_market": _safe_float(holo.get("market")),
        "tcg_holo_low": _safe_float(holo.get("low")),
        "tcg_holo_mid": _safe_float(holo.get("mid")),
        "tcg_holo_high": _safe_float(holo.get("high")),
        "tcg_reverse_market": _safe_float(reverse.get("market")),
        "cardmarket_trend": _safe_float(cm_prices.get("trendPrice")),
        "cardmarket_avg_sell": _safe_float(cm_prices.get("averageSellPrice")),
        "cardmarket_low": _safe_float(cm_prices.get("lowPrice")),
        "cardmarket_avg1": _safe_float(cm_prices.get("avg1")),
        "cardmarket_avg7": _safe_float(cm_prices.get("avg7")),
        "cardmarket_avg30": _safe_float(cm_prices.get("avg30")),
    }

    record["effective_market_price"] = calculate_effective_price(record)
    return record


def upload_batch_to_supabase(table_name, records, conflict_cols=None, batch_size=500):
    """
    Mengunggah sekumpulan baris ke tabel Supabase dengan mode upsert / merge-duplicates.
    """
    if not records:
        return True

    headers = get_supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    if conflict_cols:
        url += f"?on_conflict={conflict_cols}"

    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        success = False
        for attempt in range(1, 4):
            try:
                r = requests.post(url, headers=headers, json=chunk, timeout=30)
                if r.status_code in [200, 201, 204]:
                    success = True
                    break
                else:
                    tqdm.write(f"⚠️ [HTTP {r.status_code}] Gagal upload batch {i}-{i+len(chunk)} ke '{table_name}': {r.text[:120]}")
                    time.sleep(2)
            except Exception as e:
                tqdm.write(f"⚠️ Error upload batch {i}: {e}")
                time.sleep(2)

        if not success:
            print(f"❌ Gagal permanen mengunggah chunk {i} ke tabel {table_name}")
            return False

    return True


def run_daily_tracker(max_pages=None, workers=4, dry_run=False):
    start_time = time.time()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 65)
    print(f"🚀 REGOKEMON DAILY PRICE TRACKER ({today_str})")
    print("=" * 65)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL dan SUPABASE_KEY wajib diset!")
        sys.exit(1)

    # 1. Ambil daftar kartu valid dari Supabase
    valid_card_ids = fetch_valid_card_ids()
    if not valid_card_ids and not dry_run:
        print("❌ Tidak dapat memvalidasi card_id Supabase. Operasi dibatalkan demi keamanan.")
        sys.exit(1)

    # 2. Cek jumlah kartu & total halaman di pokemontcg.io
    print("📡 Menghubungi API pokemontcg.io untuk menentukan jumlah halaman...")
    _, initial_cards, total_count = fetch_page_with_retry(1, page_size=250)
    
    if total_count == 0:
        print("❌ Gagal mendapatkan total kartu dari pokemontcg.io.")
        sys.exit(1)

    page_size = 250
    total_pages = (total_count + page_size - 1) // page_size
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    print(f"   Total kartu di API: {total_count:,} kartu ({total_pages} halaman @ 250 kartu)")
    print(f"   Menggunakan {workers} concurrent workers...")

    # 3. Tarik seluruh halaman secara paralel
    all_raw_cards = list(initial_cards)
    pages_to_fetch = list(range(2, total_pages + 1))

    if pages_to_fetch:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_page = {
                executor.submit(fetch_page_with_retry, p, page_size): p 
                for p in pages_to_fetch
            }
            with tqdm(total=len(pages_to_fetch), desc="⚡ Mengambil Data Harga", unit="hlm") as pbar:
                for future in as_completed(future_to_page):
                    page_num, cards, _ = future.result()
                    if cards:
                        all_raw_cards.extend(cards)
                    pbar.update(1)

    print(f"\n📦 Berhasil menarik total {len(all_raw_cards):,} data kartu dari pokemontcg.io.")

    # 4. Ekstrak & pisahkan kartu terdaftar vs kartu baru
    prices_latest = []
    prices_history = []
    unregistered_cards = []

    for card in all_raw_cards:
        rec = extract_card_price_record(card)
        if not rec:
            continue

        card_id = rec["card_id"]
        # Validasi apakah kartu sudah ada di tabel master `cards`
        if valid_card_ids and card_id not in valid_card_ids:
            unregistered_cards.append(card_id)
            continue

        # Record untuk `card_prices` (Snapshot terkini)
        rec_latest = dict(rec)
        rec_latest["updated_at"] = now_iso
        prices_latest.append(rec_latest)

        # Record untuk `card_price_history` (Histori harian)
        rec_hist = dict(rec)
        rec_hist["recorded_date"] = today_str
        rec_hist["created_at"] = now_iso
        prices_history.append(rec_hist)

    print(f"   📊 Kartu valid siap sinkronisasi : {len(prices_latest):,} kartu")
    if unregistered_cards:
        print(f"   ✨ Ditemukan kartu rilis terbaru  : {len(unregistered_cards)} kartu baru (belum ada di tabel master 'cards')")

    if dry_run:
        print("\n[DRY RUN] Mode uji coba aktif - Data TIDAK diunggah ke Supabase.")
        if prices_latest:
            sample = prices_latest[0]
            print(f"Sample data ({sample['card_id']}):")
            print(f"  TCG Market: ${sample['tcg_normal_market'] or sample['tcg_holo_market']}")
            print(f"  CM Trend  : €{sample['cardmarket_trend']} | Avg 1D/7D/30D: {sample['cardmarket_avg1']} / {sample['cardmarket_avg7']} / {sample['cardmarket_avg30']}")
            print(f"  Effective : ${sample['effective_market_price']}")
        return

    # 5. Upload ke Supabase
    print("\n💾 1/2 Memperbarui snapshot harga terkini ke tabel 'card_prices'...")
    with tqdm(total=len(prices_latest), desc="Tabel card_prices", unit="kartu") as pbar:
        # Upload per batch 500
        batch_size = 500
        for i in range(0, len(prices_latest), batch_size):
            chunk = prices_latest[i:i + batch_size]
            upload_batch_to_supabase("card_prices", chunk, conflict_cols="card_id", batch_size=batch_size)
            pbar.update(len(chunk))

    print("\n📈 2/2 Mencatat entri histori harian ke tabel 'card_price_history'...")
    with tqdm(total=len(prices_history), desc="Tabel card_price_history", unit="kartu") as pbar:
        batch_size = 500
        for i in range(0, len(prices_history), batch_size):
            chunk = prices_history[i:i + batch_size]
            upload_batch_to_supabase("card_price_history", chunk, conflict_cols="card_id,recorded_date", batch_size=batch_size)
            pbar.update(len(chunk))

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"🎉 SUKSES! Sinkronisasi harga harian selesai dalam {elapsed:.1f} detik.")
    print(f"   - Kartu ter-update: {len(prices_latest):,}")
    print(f"   - Tanggal histori : {today_str}")
    if unregistered_cards:
        print(f"   - Info tambahan   : Ada {len(unregistered_cards)} kartu baru di pokemontcg.io.")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regokemon Daily Price Ingestion Engine")
    parser.add_argument("--max-pages", type=int, default=None, help="Batasi jumlah halaman (untuk testing cepat)")
    parser.add_argument("--workers", type=int, default=4, help="Jumlah concurrent worker threads (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Uji proses ekstraksi tanpa menulis ke Supabase")

    args = parser.parse_args()
    run_daily_tracker(max_pages=args.max_pages, workers=args.workers, dry_run=args.dry_run)
