"""
backend/app/offline_service.py
==============================
Layanan Ban Serep (Offline Fallback Service) untuk Regokemon.
Menyediakan data katalog, set, histori harga, dan kartu trending
langsung dari dataset lokal (pokemon_cards_dataset_cleaned.csv)
ketika koneksi internet terputus, Supabase tidak dapat dijangkau,
atau kuota API habis saat demonstrasi pameran.
"""

import os
import math
import datetime
from typing import Optional, List, Dict, Any
import pandas as pd

from app.currency_service import get_usd_to_idr_rate, convert_usd_to_idr

# Path ke dataset master bersih
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
DATASET_PATH = os.path.join(BACKEND_DIR, "dataset", "pokemon_cards_dataset_cleaned.csv")

# Cache DataFrame di memori agar cepat (sub-milidetik)
_df_offline_master: Optional[pd.DataFrame] = None


def _get_master_df() -> pd.DataFrame:
    """Mengambil atau memuat DataFrame master secara aman ke memori RAM."""
    global _df_offline_master
    if _df_offline_master is None:
        if os.path.exists(DATASET_PATH):
            _df_offline_master = pd.read_csv(DATASET_PATH)
            print(f"[Offline Service] Memuat dataset master offline ({len(_df_offline_master):,} baris)")
        else:
            print(f"[Offline Service] PERINGATAN: Dataset master tidak ditemukan di {DATASET_PATH}")
            _df_offline_master = pd.DataFrame()
    return _df_offline_master


def get_offline_cards(
    limit: int = 20,
    page: int = 1,
    search: Optional[str] = None,
    supertype: Optional[str] = None,
    rarity: Optional[str] = None,
    holo: Optional[str] = None,
    set_id: Optional[str] = None,
    sort_by: Optional[str] = "newest"
) -> Dict[str, Any]:
    """
    Mengambil data kartu katalog dari CSV lokal dengan pagination,
    pencarian nama, filter set/supertype/rarity/holo, dan pengurutan harga/rilis.
    """
    df = _get_master_df()
    if df.empty:
        return {
            "total": 0,
            "page": 1,
            "limit": limit,
            "total_pages": 1,
            "currency_rate": get_usd_to_idr_rate(),
            "cards": [],
            "is_offline_fallback": True
        }

    df_filtered = df

    # Filter pencarian nama kartu
    if search and search.strip():
        q = search.strip()
        df_filtered = df_filtered[df_filtered["name"].str.contains(q, case=False, na=False)]

    # Filter Supertype (misal: Pokémon, Trainer, Energy)
    if supertype and supertype.strip() and supertype.lower() != "all":
        s = supertype.strip()
        df_filtered = df_filtered[df_filtered["supertype"].str.contains(s, case=False, na=False)]

    # Filter Rarity
    if rarity and rarity.strip() and rarity.lower() != "all":
        r = rarity.strip()
        df_filtered = df_filtered[df_filtered["rarity"].str.contains(r, case=False, na=False)]

    # Filter Holo
    if holo and holo.strip() and holo.lower() != "all":
        if holo.lower() == "holo":
            df_filtered = df_filtered[df_filtered["rarity"].str.contains("Holo", case=False, na=False)]
        elif holo.lower() == "non_holo":
            df_filtered = df_filtered[~df_filtered["rarity"].str.contains("Holo", case=False, na=False)]

    # Filter Set ID
    if set_id and set_id.strip() and set_id.lower() != "all":
        sid = set_id.strip().lower()
        df_filtered = df_filtered[df_filtered["set.id"].str.lower() == sid]

    # Pengurutan
    if sort_by in ("newest", "release_desc"):
        df_filtered = df_filtered.sort_values(by=["set.release_date", "name"], ascending=[False, True])
    elif sort_by in ("oldest", "release_asc"):
        df_filtered = df_filtered.sort_values(by=["set.release_date", "name"], ascending=[True, True])
    elif sort_by == "price_desc":
        df_filtered = df_filtered.sort_values(by=["effective_market_price", "name"], ascending=[False, True])
    elif sort_by == "price_asc":
        df_filtered = df_filtered.sort_values(by=["effective_market_price", "name"], ascending=[True, True])
    elif sort_by == "name_asc":
        df_filtered = df_filtered.sort_values(by="name", ascending=True)
    elif sort_by == "name_desc":
        df_filtered = df_filtered.sort_values(by="name", ascending=False)
    elif sort_by == "hp_desc":
        df_filtered = df_filtered.sort_values(by="hp", ascending=False)

    total_count = len(df_filtered)
    safe_limit = max(1, min(limit, 100))
    safe_page = max(1, page)
    offset = (safe_page - 1) * safe_limit

    page_df = df_filtered.iloc[offset : offset + safe_limit]

    formatted_cards = []
    for _, row in page_df.iterrows():
        price_val = float(row["effective_market_price"]) if pd.notna(row.get("effective_market_price")) else 0.0
        if price_val > 0:
            price_usd_str = f"$ {price_val:.2f}"
            price_idr_val = convert_usd_to_idr(price_val)
            price_idr_str = f"Rp {price_idr_val:,}".replace(",", ".")
            is_unlisted = False
        else:
            price_usd_str = "Unlisted"
            price_idr_str = "Belum Ada Data"
            is_unlisted = True

        rarity_str = str(row.get("rarity") or "Common")
        words = rarity_str.split()
        rarity_icon = "".join([w[0].upper() for w in words]) if words else "C"
        if len(rarity_icon) > 2:
            rarity_icon = rarity_icon[:2]

        set_info = str(row.get("set.id") or "unknown")

        formatted_cards.append({
            "id": str(row.get("card_id")),
            "name": str(row.get("name")),
            "supertype": str(row.get("supertype") or "Pokémon"),
            "price": price_usd_str,
            "price_usd": price_usd_str,
            "price_idr": price_idr_str,
            "price_num": price_val,
            "is_unlisted": is_unlisted,
            "rarityText": rarity_str,
            "rarityIcon": rarity_icon,
            "set": set_info,
            "image": str(row.get("images.small") or "/card-result.png")
        })

    total_pages = math.ceil(total_count / safe_limit) if safe_limit > 0 else 1

    return {
        "total": total_count,
        "page": safe_page,
        "limit": safe_limit,
        "total_pages": total_pages,
        "currency_rate": get_usd_to_idr_rate(),
        "cards": formatted_cards,
        "is_offline_fallback": True
    }


def get_offline_sets(limit: int = 250) -> List[Dict[str, Any]]:
    """
    Mengambil daftar Set Pokémon unik dari CSV lokal,
    diurutkan dari tanggal rilis paling baru ke lawas.
    """
    df = _get_master_df()
    if df.empty:
        return []

    sets_df = df[["set.id", "set.name", "set.series", "set.release_date", "release_year"]].drop_duplicates(subset=["set.id"])
    sets_df = sets_df.sort_values(by="set.release_date", ascending=False)
    if limit > 0:
        sets_df = sets_df.head(limit)

    result = []
    for _, row in sets_df.iterrows():
        result.append({
            "set_id": str(row["set.id"]),
            "name": str(row["set.name"]),
            "series": str(row["set.series"]),
            "release_date": str(row["set.release_date"]) if pd.notna(row["set.release_date"]) else None,
            "release_year": int(row["release_year"]) if pd.notna(row["release_year"]) else None
        })
    return result


def get_offline_card_history(card_id: str) -> List[Dict[str, Any]]:
    """
    Menghasilkan histori harga sintetis berbasis data acuan pasar CSV lokal
    agar grafik di pop-up katalog dan dashboard tetap aktif saat offline.
    """
    df = _get_master_df()
    if df.empty:
        return []

    match = df[df["card_id"] == card_id]
    if match.empty:
        return []

    row = match.iloc[0]
    base_price = float(row.get("effective_market_price") or 0.0)
    if base_price <= 0:
        return []

    today = datetime.date.today()
    points = [
        {"recorded_date": (today - datetime.timedelta(days=28)).strftime("%Y-%m-%d"), "effective_market_price": round(base_price * 0.94, 2)},
        {"recorded_date": (today - datetime.timedelta(days=14)).strftime("%Y-%m-%d"), "effective_market_price": round(base_price * 0.97, 2)},
        {"recorded_date": (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d"), "effective_market_price": round(base_price * 0.99, 2)},
        {"recorded_date": (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "effective_market_price": round(base_price, 2)}
    ]
    return points


def get_offline_trending_cards(limit: int = 4) -> List[Dict[str, Any]]:
    """
    Mengambil kartu populer bernilai tinggi untuk widget trending di Dashboard saat offline.
    """
    df = _get_master_df()
    if df.empty:
        return []

    popular_names = ["Charizard", "Pikachu", "Mewtwo", "Gengar", "Rayquaza", "Lugia"]
    matches = df[df["name"].isin(popular_names)].drop_duplicates(subset=["name"])
    if len(matches) < limit:
        matches = df.head(limit)
    else:
        matches = matches.head(limit)

    trending = []
    for i, (_, row) in enumerate(matches.iterrows()):
        price_val = float(row.get("effective_market_price") or 0.0)
        set_id = str(row.get("set.id") or "base1")
        trending.append({
            "id": i + 1,
            "card_id": str(row.get("card_id")),
            "name": str(row.get("name")),
            "rarity": str(row.get("rarity") or "Rare Holo"),
            "holo": "Holo Print" if "holo" in str(row.get("rarity", "")).lower() else "Normal Print",
            "price": f"$ {price_val:.2f}",
            "image": str(row.get("images.small") or "/card-result.png"),
            "setIcon": f"/{set_id}-logo.png",
            "flagIcon": "US"
        })
    return trending
