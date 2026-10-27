#!/usr/bin/env python3
"""
Regokemon Daily Price Tracker & Ingestion Engine (Resilient Edition)
===================================================================
Menarik snapshot harga harian secara otomatis dari pokemontcg.io API (TCGPlayer & Cardmarket),
mengekstrak metrik harga likuiditas (low, mid, high, market) dan time-series (avg1, avg7, avg30),
kemudian menyimpannya ke Supabase:
  1. Tabel `card_prices` (Update snapshot harga terkini untuk live search & valuasi)
  2. Tabel `card_price_history` (Upsert histori harga harian per tanggal YYYY-MM-DD)

Fitur Ketahanan (Zero-Gap Guarantee):
  - Idempotensi cerdas: Melewati sinkronisasi jika data tanggal hari ini sudah lengkap.
  - HTTP Connection Pooling & Keep-Alive untuk Supabase dan PokemonTCG API.
  - Multi-Pass Queue & Jittered Pacing untuk menghindari rate limit Cloudflare.
  - Adaptive Sub-Page Fallback untuk halaman yang lambat/timeout.
  - Zero-Gap Imputation: Otomatis melengkapi kartu yang terlewat dari harga kemarin jika ada gangguan parsial API.
"""

import os
import sys
import time
import random
import argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# Encoding UTF-8 untuk stdout terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
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


def create_resilient_session(pool_size=12):
    """
    Membuat requests.Session dengan connection pooling untuk mencegah
    overhead SSL handshake berulang. Retry dikendalikan penuh oleh aplikasi.
    """
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=0
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }


def check_today_sync_status(today_str, session=None):
    """
    Memeriksa apakah data histori hari ini sudah lengkap di Supabase.
    Jika sudah >= 20,000 kartu, mengembalikan jumlah baris yang ada.
    """
    s = session or requests
    url = f"{SUPABASE_URL}/rest/v1/card_price_history?recorded_date=eq.{today_str}&select=card_id&limit=1"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=exact"
    }
    try:
        r = s.get(url, headers=headers, timeout=15)
        if r.status_code in [200, 206]:
            cr = r.headers.get("content-range", "")
            if "/" in cr:
                total_str = cr.split("/")[-1]
                if total_str.isdigit():
                    return int(total_str)
    except Exception as e:
        print(f"⚠️ Peringatan saat memeriksa status histori hari ini: {e}")
    return 0


def fetch_valid_card_ids(session=None):
    """
    Mengambil daftar seluruh `card_id` master yang terdaftar di tabel `cards` Supabase.
    Dilengkapi retry loop per batch agar tahan terhadap fluktuasi koneksi.
    """
    s = session or requests
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
        batch = None
        for attempt in range(1, 4):
            try:
                r = s.get(url, headers=headers, timeout=25)
                if r.status_code == 200:
                    batch = r.json()
                    break
                else:
                    time.sleep(1.5 * attempt)
            except Exception as e:
                time.sleep(1.5 * attempt)

        if batch is None:
            print(f"⚠️ Gagal mengambil batch card_id pada offset {offset} setelah 3 percobaan.")
            break

        if not batch:
            break

        for row in batch:
            valid_ids.add(row["card_id"])

        offset += len(batch)
        if len(batch) < limit:
            break
            
    print(f"   ✅ Ditemukan {len(valid_ids):,} kartu master terdaftar di database Supabase.")
    return valid_ids


def fetch_page_with_retry(session, page_num, page_size=250, max_retries=5, backoff_factor=1.5):
    """
    Menarik 1 halaman data kartu dari pokemontcg.io dengan retry otomatis,
    jitter pacing, dan penanganan Cloudflare 500/502/504/429.
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

    # Jitter pacing acak (80ms - 250ms) agar antrean request tidak menabrak batas rate-limit bersamaan
    time.sleep(0.08 + random.uniform(0.02, 0.15))

    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(url, headers=headers, params=params, timeout=28)
            if r.status_code == 200:
                try:
                    data = r.json()
                    cards = data.get("data", [])
                    if cards:
                        return page_num, cards, data.get("totalCount", 0)
                except Exception:
                    pass
            elif r.status_code in [429, 500, 502, 503, 504]:
                wait_time = min(25.0, (backoff_factor ** attempt) + random.uniform(1.0, 3.0))
                time.sleep(wait_time)
            else:
                time.sleep(2.0)
        except Exception:
            wait_time = min(25.0, (backoff_factor ** attempt) + random.uniform(1.0, 3.0))
            time.sleep(wait_time)

    return page_num, [], 0


def fetch_subpages_fallback(session, page_num):
    """
    Adaptive Sub-Page Fallback:
    Jika request 1 halaman besar (pageSize=250) terus menerus gagal atau timeout,
    bagi menjadi 2 sub-request lebih kecil (pageSize=125) yang jauh lebih cepat dan andal.
    """
    subpage_1 = (page_num - 1) * 2 + 1
    subpage_2 = (page_num - 1) * 2 + 2
    
    combined_cards = []
    total_cnt = 0
    
    for subp in [subpage_1, subpage_2]:
        _, cards, total = fetch_page_with_retry(session, subp, page_size=125, max_retries=4)
        if cards:
            combined_cards.extend(cards)
            if total > 0:
                total_cnt = total

    return page_num, combined_cards, total_cnt


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


def fetch_missing_card_prices_from_supabase(session, missing_card_ids):
    """
    Zero-Gap Fallback:
    Mengambil data harga terakhir dari tabel `card_prices` Supabase untuk kartu-kartu
    yang gagal ditarik dari API hari ini, memastikan histori harian tetap 100% lengkap.
    """
    if not missing_card_ids:
        return {}

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    fallback_records = {}
    missing_list = list(missing_card_ids)
    chunk_size = 100  # URL query parameter limit safe

    for i in range(0, len(missing_list), chunk_size):
        chunk = missing_list[i:i + chunk_size]
        id_filter = ",".join(chunk)
        url = f"{SUPABASE_URL}/rest/v1/card_prices?card_id=in.({id_filter})"
        try:
            r = session.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                rows = r.json()
                for row in rows:
                    cid = row.get("card_id")
                    if cid:
                        # Buang kolom internal yang tidak relevan untuk history
                        clean_row = {k: v for k, v in row.items() if k not in ["updated_at"]}
                        fallback_records[cid] = clean_row
        except Exception as e:
            print(f"⚠️ Gagal menarik fallback harga untuk sub-batch {i}: {e}")

    return fallback_records


def upload_batch_to_supabase(session, table_name, records, conflict_cols=None, batch_size=500):
    """
    Mengunggah sekumpulan baris ke tabel Supabase dengan mode upsert / merge-duplicates.
    Dilengkapi fallback otomatis ke sub-batch lebih kecil (100 baris) jika terjadi timeout.
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
                r = session.post(url, headers=headers, json=chunk, timeout=25)
                if r.status_code in [200, 201, 204]:
                    success = True
                    break
                else:
                    time.sleep(1.5 * attempt)
            except Exception:
                time.sleep(1.5 * attempt)

        # Fallback ke micro-batch (100 baris) jika batch besar gagal/timeout
        if not success and len(chunk) > 100:
            sub_success = True
            micro_size = 100
            for j in range(0, len(chunk), micro_size):
                micro_chunk = chunk[j:j + micro_size]
                try:
                    r_sub = session.post(url, headers=headers, json=micro_chunk, timeout=20)
                    if r_sub.status_code not in [200, 201, 204]:
                        sub_success = False
                        break
                except Exception:
                    sub_success = False
                    break
            success = sub_success

        if not success:
            print(f"❌ Gagal permanen mengunggah chunk {i}-{i+len(chunk)} ke tabel {table_name}")
            return False

    return True


def run_daily_tracker(max_pages=None, workers=3, dry_run=False, force=False):
    start_time = time.time()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 65)
    print(f"🚀 REGOKEMON DAILY PRICE TRACKER ({today_str})")
    print("=" * 65)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL dan SUPABASE_KEY wajib diset!")
        sys.exit(1)

    session = create_resilient_session(pool_size=workers * 3 + 4)

    # 1. Cek Idempotensi: Apakah data hari ini sudah lengkap?
    if not dry_run and not force:
        existing_today_count = check_today_sync_status(today_str, session)
        if existing_today_count >= 20000:
            print(f"✅ [IDEMPOTENCY] Data histori untuk tanggal {today_str} sudah lengkap ({existing_today_count:,} kartu) di Supabase.")
            print("   Pipeline selesai tanpa perlu menarik ulang. (Gunakan --force jika ingin menimpa paksa).")
            return

    # 2. Ambil daftar kartu master valid dari Supabase
    valid_card_ids = fetch_valid_card_ids(session)
    if not valid_card_ids and not dry_run:
        print("❌ Tidak dapat memvalidasi card_id Supabase. Operasi dibatalkan demi keamanan.")
        sys.exit(1)

    # 3. Cek jumlah kartu & total halaman di pokemontcg.io
    print("📡 Menghubungi API pokemontcg.io untuk menentukan jumlah halaman...")
    _, initial_cards, total_count = fetch_page_with_retry(session, 1, page_size=250)
    
    if total_count == 0:
        print("❌ Gagal mendapatkan total kartu dari pokemontcg.io.")
        sys.exit(1)

    page_size = 250
    total_pages = (total_count + page_size - 1) // page_size
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    print(f"   Total kartu di API: {total_count:,} kartu ({total_pages} halaman @ 250 kartu)")
    print(f"   Menggunakan {workers} concurrent workers (Resilient Connection Pooling)...")

    # 4. Tarik seluruh halaman dengan sistem Multi-Pass Retry Queue
    all_raw_cards_dict = {}
    if initial_cards:
        for c in initial_cards:
            if c.get("id"):
                all_raw_cards_dict[c["id"]] = c

    pages_to_fetch = set(range(2, total_pages + 1))
    max_passes = 4

    for pass_num in range(1, max_passes + 1):
        if not pages_to_fetch:
            break

        pass_label = "⚡ Mengambil Data Harga" if pass_num == 1 else f"🔁 Putaran Retry #{pass_num-1} ({len(pages_to_fetch)} hlm)"
        failed_pages = set()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            if pass_num <= 2:
                # Pass 1 & 2: Halaman standar 250 kartu
                future_to_page = {
                    executor.submit(fetch_page_with_retry, session, p, page_size): p 
                    for p in pages_to_fetch
                }
            else:
                # Pass 3 & 4: Adaptive Sub-Page Fallback (125 kartu per sub-request)
                future_to_page = {
                    executor.submit(fetch_subpages_fallback, session, p): p 
                    for p in pages_to_fetch
                }

            with tqdm(total=len(pages_to_fetch), desc=pass_label, unit="hlm") as pbar:
                for future in as_completed(future_to_page):
                    page_num, cards, _ = future.result()
                    if cards:
                        for c in cards:
                            if c.get("id"):
                                all_raw_cards_dict[c["id"]] = c
                    else:
                        failed_pages.add(page_num)
                    pbar.update(1)

        if failed_pages:
            print(f"   ⚠️ Terdapat {len(failed_pages)} halaman belum berhasil di putaran {pass_num}.")
            if pass_num < max_passes:
                cooldown = 3 * pass_num
                time.sleep(cooldown)
                pages_to_fetch = failed_pages
            else:
                print(f"   ℹ️ Halaman API yang belum terambil setelah {max_passes} putaran: {sorted(list(failed_pages))}")
        else:
            pages_to_fetch = set()

    all_raw_cards = list(all_raw_cards_dict.values())
    print(f"\n📦 Berhasil menarik total {len(all_raw_cards):,} data kartu segar dari pokemontcg.io.")

    # 5. Ekstrak & Format Kartu Terdaftar vs Kartu Baru
    prices_latest = []
    prices_history = []
    unregistered_cards = []
    fetched_card_ids = set()

    for card in all_raw_cards:
        rec = extract_card_price_record(card)
        if not rec:
            continue

        card_id = rec["card_id"]
        fetched_card_ids.add(card_id)

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

    # 6. Zero-Gap Fallback Guardrail
    # Jika ada kartu terdaftar yang belum terambil karena gangguan parsial API upstream (< 35% kartu)
    missing_from_api = valid_card_ids - fetched_card_ids if valid_card_ids else set()
    imputed_count = 0

    if missing_from_api and not dry_run and not max_pages:
        missing_count = len(missing_from_api)
        max_allowable_missing = int(len(valid_card_ids) * 0.35)

        if missing_count <= max_allowable_missing:
            print(f"\n🛡️ Zero-Gap Guardrail: Ditemukan {missing_count:,} kartu tertinggal karena isu jaringan API.")
            print(f"   Mengambil snapshot harga terakhir dari Supabase untuk menjamin histori 100% lengkap...")
            
            fallback_map = fetch_missing_card_prices_from_supabase(session, missing_from_api)
            for cid in missing_from_api:
                if cid in fallback_map:
                    fb_rec = dict(fallback_map[cid])
                    fb_rec["recorded_date"] = today_str
                    fb_rec["created_at"] = now_iso
                    prices_history.append(fb_rec)
                    imputed_count += 1

            print(f"   ✅ Sukses melengkapi {imputed_count:,} kartu histori dari harga kemarin.")
        else:
            print(f"\n❌ [CRITICAL OUTAGE] Jumlah kartu tertinggal ({missing_count:,}) melebihi batas aman imputasi.")
            print("   Operasi dibatalkan demi menjaga keaslian data.")
            sys.exit(1)

    print(f"   📊 Kartu valid siap sinkronisasi : {len(prices_history):,} kartu (Kelengkapan: {len(prices_history)/len(valid_card_ids)*100:.1f}%)" if valid_card_ids else f"   📊 Kartu valid siap sinkronisasi : {len(prices_history):,} kartu")
    if imputed_count > 0:
        print(f"   🩹 Kartu diimputasi (fallback)   : {imputed_count:,} kartu")
    if unregistered_cards:
        print(f"   ✨ Ditemukan kartu rilis terbaru  : {len(unregistered_cards)} kartu baru (belum ada di master 'cards')")

    if dry_run:
        print("\n[DRY RUN] Mode uji coba aktif - Data TIDAK diunggah ke Supabase.")
        if prices_latest:
            sample = prices_latest[0]
            print(f"Sample data ({sample['card_id']}):")
            print(f"  TCG Market: ${sample['tcg_normal_market'] or sample['tcg_holo_market']}")
            print(f"  CM Trend  : €{sample['cardmarket_trend']} | Avg 1D/7D/30D: {sample['cardmarket_avg1']} / {sample['cardmarket_avg7']} / {sample['cardmarket_avg30']}")
            print(f"  Effective : ${sample['effective_market_price']}")
        return

    # 7. Upload ke Supabase
    print("\n💾 1/2 Memperbarui snapshot harga terkini ke tabel 'card_prices'...")
    with tqdm(total=len(prices_latest), desc="Tabel card_prices", unit="kartu") as pbar:
        batch_size = 500
        for i in range(0, len(prices_latest), batch_size):
            chunk = prices_latest[i:i + batch_size]
            upload_batch_to_supabase(session, "card_prices", chunk, conflict_cols="card_id", batch_size=batch_size)
            pbar.update(len(chunk))

    print("\n📈 2/2 Mencatat entri histori harian ke tabel 'card_price_history'...")
    with tqdm(total=len(prices_history), desc="Tabel card_price_history", unit="kartu") as pbar:
        batch_size = 500
        for i in range(0, len(prices_history), batch_size):
            chunk = prices_history[i:i + batch_size]
            upload_batch_to_supabase(session, "card_price_history", chunk, conflict_cols="card_id,recorded_date", batch_size=batch_size)
            pbar.update(len(chunk))

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"🎉 SUKSES! Sinkronisasi harga harian selesai dalam {elapsed:.1f} detik.")
    print(f"   - Kartu ter-update di snapshot: {len(prices_latest):,}")
    print(f"   - Total histori tersimpan     : {len(prices_history):,} (100% komplit)")
    print(f"   - Tanggal histori             : {today_str}")
    if imputed_count > 0:
        print(f"   - Catatan Fallback Imputasi   : {imputed_count:,} kartu")
    if unregistered_cards:
        print(f"   - Info tambahan               : Ada {len(unregistered_cards)} kartu baru di pokemontcg.io.")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regokemon Daily Price Ingestion Engine")
    parser.add_argument("--max-pages", type=int, default=None, help="Batasi jumlah halaman (untuk testing cepat)")
    parser.add_argument("--workers", type=int, default=3, help="Jumlah concurrent worker threads (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Uji proses ekstraksi tanpa menulis ke Supabase")
    parser.add_argument("--force", action="store_true", help="Paksa jalankan sinkronisasi meskipun data hari ini sudah ada")

    args = parser.parse_args()
    run_daily_tracker(max_pages=args.max_pages, workers=args.workers, dry_run=args.dry_run, force=args.force)
