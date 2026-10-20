"""
backend/app/currency_service.py
================================
Layanan Konversi Mata Uang Otomatis (USD -> IDR) Real-Time untuk Regokemon:
1. Menarik data kurs valuta asing live dari API publik gratis (open.er-api.com).
2. Menerapkan In-Memory Cache (TTL 6 jam) agar performa API tetap sub-milidetik (0 ms)
   dan tidak melakukan request berulang-ulang ke internet setiap kali ada user membuka web.
3. Dilengkapi sistem Fallback aman jika koneksi internet terputus atau API pihak ketiga lambat.
"""

import os
import time
import requests
from typing import Dict, Any, Optional

# Kurs fallback jika internet mati total atau API kurs luar down
FALLBACK_USD_TO_IDR: float = float(os.getenv("DEFAULT_USD_TO_IDR", "16500.0"))

# Waktu kedaluwarsa cache (6 jam = 21.600 detik)
CACHE_TTL_SECONDS: float = 6 * 3600.0

# Penyimpanan cache in-memory
_cached_rate: Optional[float] = None
_last_fetched_time: float = 0.0
_last_rate_source: str = "init"


def fetch_live_usd_to_idr() -> Optional[float]:
    """
    Menembak API valuta asing publik gratis untuk mendapatkan kurs 1 USD ke IDR.
    Menggunakan timeout 1 detik agar tidak memblokir server saat offline / sandbox.
    """
    endpoints = [
        # Provider 1: Open Exchange Rates public mirror (sangat stabil & tanpa API key)
        "https://open.er-api.com/v6/latest/USD",
        # Provider 2: Frankfurter ECB mirror (backup alternatif)
        "https://api.frankfurter.app/latest?from=USD&to=IDR"
    ]

    for url in endpoints:
        try:
            res = requests.get(url, timeout=1.0)
            if res.status_code == 200:
                data = res.json()
                if "rates" in data and "IDR" in data["rates"]:
                    val = float(data["rates"]["IDR"])
                    if val > 0:
                        return val
                elif "rates" in data and isinstance(data["rates"], dict):
                    val = float(data["rates"].get("IDR", 0))
                    if val > 0:
                        return val
        except Exception:
            continue

    return None


def get_usd_to_idr_rate() -> float:
    """
    Mengambil kurs USD ke IDR saat ini:
    - Jika cache masih segar (< 6 jam), langsung kembalikan dari memori RAM (0 ms).
    - Jika cache sudah kedaluwarsa, coba ambil nilai terbaru dari internet.
    - Jika gagal, gunakan cache terakhir atau nilai fallback yang aman.
    """
    global _cached_rate, _last_fetched_time, _last_rate_source

    current_time = time.time()

    # 1. Gunakan cache jika masih dalam batas masa berlaku
    if _cached_rate is not None and (current_time - _last_fetched_time < CACHE_TTL_SECONDS):
        return _cached_rate

    # 2. Ambil kurs live dari API publik
    live_rate = fetch_live_usd_to_idr()
    if live_rate and live_rate > 10000:
        _cached_rate = round(live_rate, 2)
        _last_fetched_time = current_time
        _last_rate_source = "live_api"
        return _cached_rate

    # 3. Fallback jika gagal mengambil data live
    if _cached_rate is not None:
        return _cached_rate

    # 4. Fallback awal jika belum pernah fetch sama sekali
    _cached_rate = FALLBACK_USD_TO_IDR
    _last_fetched_time = current_time
    _last_rate_source = "fallback"
    return _cached_rate


def convert_usd_to_idr(usd_amount: float) -> int:
    """Mengonversi nilai USD ke integer Rupiah IDR."""
    if not usd_amount or usd_amount <= 0:
        return 0
    rate = get_usd_to_idr_rate()
    return int(round(usd_amount * rate))


def get_currency_status() -> Dict[str, Any]:
    """Mengembalikan status kurs saat ini untuk endpoint informasi."""
    rate = get_usd_to_idr_rate()
    return {
        "base_currency": "USD",
        "target_currency": "IDR",
        "rate": rate,
        "formatted_rate": f"Rp {int(rate):,}".replace(",", "."),
        "source": _last_rate_source,
        "last_updated_epoch": _last_fetched_time,
        "cache_ttl_hours": CACHE_TTL_SECONDS / 3600.0
    }
