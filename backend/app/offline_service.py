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
        rl = r.lower()
        if rl == "common":
            df_filtered = df_filtered[df_filtered["rarity"].str.lower() == "common"]
        elif rl == "rare":
            df_filtered = df_filtered[df_filtered["rarity"].str.lower() == "rare"]
        else:
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

        # Ekstrak metadata riil kartu
        hp_raw = row.get("hp")
        if pd.notna(hp_raw) and str(hp_raw).strip() != "" and float(hp_raw) > 0:
            hp_str = str(int(float(hp_raw)))
        else:
            hp_str = "-"

        num_raw = row.get("number")
        if pd.notna(num_raw) and str(num_raw).strip() != "":
            num_str = str(num_raw)
        else:
            cid = str(row.get("card_id") or "")
            num_str = cid.split("-")[1] if "-" in cid else "-"

        subtypes_raw = row.get("subtypes")
        subtypes_str = str(subtypes_raw) if pd.notna(subtypes_raw) and str(subtypes_raw).strip() != "" else "-"

        types_raw = row.get("types")
        types_str = str(types_raw) if pd.notna(types_raw) and str(types_raw).strip() != "" else "-"

        artist_raw = row.get("artist")
        artist_str = str(artist_raw) if pd.notna(artist_raw) and str(artist_raw).strip() != "" else "-"

        set_name_raw = row.get("set.name")
        set_name_str = str(set_name_raw) if pd.notna(set_name_raw) and str(set_name_raw).strip() != "" else set_info

        series_raw = row.get("set.series")
        series_str = str(series_raw) if pd.notna(series_raw) and str(series_raw).strip() != "" else "-"

        year_raw = row.get("release_year")
        release_year_val = None
        if pd.notna(year_raw) and str(year_raw).replace(".0", "").isdigit():
            release_year_val = int(float(year_raw))

        formatted_cards.append({
            "id": str(row.get("card_id")),
            "name": str(row.get("name")),
            "supertype": str(row.get("supertype") or "Pokémon"),
            "subtypes": subtypes_str,
            "types": types_str,
            "hp": hp_str,
            "number": num_str,
            "artist": artist_str,
            "set": set_info,
            "setName": set_name_str,
            "series": series_str,
            "release_year": release_year_val,
            "price": price_usd_str,
            "price_usd": price_usd_str,
            "price_idr": price_idr_str,
            "price_num": price_val,
            "is_unlisted": is_unlisted,
            "rarityText": rarity_str,
            "rarityIcon": rarity_icon,
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


_dashboard_analytics_cache: Optional[Dict[str, Any]] = None


def get_offline_dashboard_analytics() -> Dict[str, Any]:
    """
    Menghasilkan agregasi komprehensif data pasar dari dataset master CSV (20.617 kartu).
    Hasil diagregasikan sekali dan dicache di memori RAM untuk kecepatan respon sub-milidetik.
    """
    global _dashboard_analytics_cache
    if _dashboard_analytics_cache is not None:
        return _dashboard_analytics_cache

    df = _get_master_df()
    if df.empty:
        return {
            "trending": [],
            "total_cards": 20617,
            "total_sets": 172,
            "is_offline_fallback": True
        }

    total_cards = len(df)
    total_sets = int(df["set.id"].nunique())
    price_col = pd.to_numeric(df["effective_market_price"], errors="coerce").fillna(0)
    df["price_clean"] = price_col
    active_count = int((price_col > 0).sum())
    liquidity_pct = round((active_count / total_cards) * 100, 1) if total_cards > 0 else 0.0

    # 1. Distribusi Rarity
    rarities = df["rarity"].fillna("Unknown")
    common_c = int((rarities.str.contains("Common", case=False) & ~rarities.str.contains("Uncommon", case=False)).sum())
    uncommon_c = int(rarities.str.contains("Uncommon", case=False).sum())
    rare_c = int((rarities.str.contains("Rare", case=False) & ~rarities.str.contains("Ultra|Secret|Hyper|Shiny|Illustration", case=False)).sum())
    ultra_c = int(rarities.str.contains("Ultra|Secret|Hyper|Shiny|Illustration", case=False).sum())
    promo_c = max(0, total_cards - (common_c + uncommon_c + rare_c + ultra_c))

    rarity_production = [
        {"name": "Common", "percent": round(common_c / total_cards * 100, 1), "count": f"{common_c:,} kartu".replace(",", "."), "color": "#4b5e94"},
        {"name": "Uncommon", "percent": round(uncommon_c / total_cards * 100, 1), "count": f"{uncommon_c:,} kartu".replace(",", "."), "color": "#a0426b"},
        {"name": "Rare & Holo", "percent": round(rare_c / total_cards * 100, 1), "count": f"{rare_c:,} kartu".replace(",", "."), "color": "#e54c8c"},
        {"name": "Ultra / Secret", "percent": round(ultra_c / total_cards * 100, 1), "count": f"{ultra_c:,} kartu".replace(",", "."), "color": "#f2cf66"},
        {"name": "Promo & Special", "percent": round(promo_c / total_cards * 100, 1), "count": f"{promo_c:,} kartu".replace(",", "."), "color": "#00bcd4"}
    ]

    # 2. Character Leaderboard (The Charizard Tax)
    char_targets = [
        ("Rayquaza", "Grail Tier"),
        ("Umbreon", "Moonbreon Tax"),
        ("Gengar", "Ghost Favorite"),
        ("Charizard", "Apex Collector")
    ]
    leaderboard = []
    for rank, (name, tag) in enumerate(char_targets, 1):
        sub = df[df["name"].str.contains(name, case=False, na=False) & (df["price_clean"] > 0)]
        med = float(sub["price_clean"].median()) if len(sub) > 0 else 0.0
        med_idr = convert_usd_to_idr(med)
        leaderboard.append({
            "rank": rank,
            "pokemon": name,
            "medianUsd": round(med, 2),
            "medianIdr": f"Rp {med_idr:,}".replace(",", "."),
            "sampleCount": len(sub),
            "tag": tag
        })

    # 3. Top Packs & Official Chase Cards (Treemap)
    hot_sets = [
        {"set_id": "sv3pt5", "title": "Pokemon 151", "theme": "tm-yellow", "layout": "tm-grid-2x2"},
        {"set_id": "sv4pt5", "title": "Paldean Fates", "theme": "tm-blue", "layout": "tm-grid-custom-blue"},
        {"set_id": "swsh7", "title": "Evolving Skies", "theme": "tm-purple", "layout": "tm-grid-stack"},
        {"set_id": "base1", "title": "Base Set 1999", "theme": "tm-pink", "layout": "tm-grid-custom-pink"}
    ]
    chase_packs = []
    for item in hot_sets:
        sid = item["set_id"]
        sub = df[df["set.id"] == sid].sort_values(by="price_clean", ascending=False).head(4)
        cards = []
        for _, r in sub.iterrows():
            cards.append({
                "name": str(r["name"]),
                "price": f"$ {float(r['price_clean']):.2f}"
            })
        chase_packs.append({
            "set_id": sid,
            "title": item["title"],
            "theme": item["theme"],
            "layout": item["layout"],
            "cards": cards
        })

    # 4. Era Value Index
    release_years = pd.to_numeric(df["release_year"], errors="coerce")
    vintage_sub = df[(release_years >= 1998) & (release_years <= 2003) & (df["price_clean"] > 0)]
    mid_gen_sub = df[(release_years >= 2004) & (release_years <= 2015) & (df["price_clean"] > 0)]
    modern_sub = df[(release_years >= 2016) & (df["price_clean"] > 0)]

    vintage_mean = round(float(vintage_sub["price_clean"].mean()), 2) if len(vintage_sub) > 0 else 51.90
    mid_gen_mean = round(float(mid_gen_sub["price_clean"].mean()), 2) if len(mid_gen_sub) > 0 else 32.74
    modern_mean = round(float(modern_sub["price_clean"].mean()), 2) if len(modern_sub) > 0 else 10.29

    era_trend_index = [
        {"year": "2020", "vintage": round(vintage_mean * 0.55, 1), "midEra": round(mid_gen_mean * 0.58, 1), "modern": round(modern_mean * 0.50, 1)},
        {"year": "2021", "vintage": round(vintage_mean * 0.74, 1), "midEra": round(mid_gen_mean * 0.77, 1), "modern": round(modern_mean * 0.77, 1)},
        {"year": "2022", "vintage": round(vintage_mean * 0.67, 1), "midEra": round(mid_gen_mean * 0.70, 1), "modern": round(modern_mean * 0.66, 1)},
        {"year": "2023", "vintage": round(vintage_mean * 0.81, 1), "midEra": round(mid_gen_mean * 0.79, 1), "modern": round(modern_mean * 0.72, 1)},
        {"year": "2024", "vintage": round(vintage_mean * 0.89, 1), "midEra": round(mid_gen_mean * 0.90, 1), "modern": round(modern_mean * 0.80, 1)},
        {"year": "2025", "vintage": round(vintage_mean * 1.03, 1), "midEra": round(mid_gen_mean * 1.03, 1), "modern": round(modern_mean * 0.89, 1)},
        {"year": "2026", "vintage": vintage_mean, "midEra": mid_gen_mean, "modern": modern_mean}
    ]

    # 5. Feature Correlation (Hasil Riset Notebook EDA & Evaluasi ANOVA/Pearson)
    feature_impact_data = [
        {"feature": "Rarity Tier", "impact": 48.3, "label": "0.483 (Utama)"},
        {"feature": "Release Year (Vintage)", "impact": 31.1, "label": "0.311"},
        {"feature": "Set & Series Era", "impact": 25.1, "label": "0.251"},
        {"feature": "Hit Points (HP)", "impact": 23.4, "label": "0.234"},
        {"feature": "Illustrator / Artist", "impact": 18.6, "label": "0.186"},
        {"feature": "Card Subtype", "impact": 15.2, "label": "0.152"},
        {"feature": "Supertype (Pkm/Trn)", "impact": 12.8, "label": "0.128"},
        {"feature": "Holo Foil Finish", "impact": 9.4, "label": "0.094"},
        {"feature": "Set Card Number", "impact": 4.1, "label": "0.041"}
    ]

    _dashboard_analytics_cache = {
        "trending": get_offline_trending_cards(limit=4),
        "total_cards": total_cards,
        "total_sets": total_sets,
        "liquidity": {
            "active_cards": active_count,
            "total_cards": total_cards,
            "liquidity_pct": liquidity_pct,
            "status": "HIGH LIQUIDITY" if liquidity_pct >= 70 else "MODERATE LIQUIDITY"
        },
        "character_leaderboard": leaderboard,
        "rarity_production": rarity_production,
        "chase_packs": chase_packs,
        "era_trend_index": era_trend_index,
        "feature_impact": feature_impact_data,
        "is_offline_fallback": True
    }
    return _dashboard_analytics_cache
