"""
backend/app/analytics_engine.py
===============================
Mesin Analitika & Valuasi Harga Wajar Kartu Pokémon (Regokemon Engine).
Mengimplementasikan formula valuasi resmi dari Laporan Akademik Bab II:

    P_final = P_base * M_variant * F_condition * F_market

Fungsi utama:
1. Menghitung pengali kondisi fisik (F_condition) berdasarkan deteksi cacat fisik Model 2.
2. Menghitung pengali kelangkaan & vintage (M_variant).
3. Mengonversi mata uang (USD -> IDR).
4. Menghasilkan sinyal transaksi wajar (BUY / HOLD / SELL).
5. Multi-step recursive forecasting harga 7 hari ke depan.
6. Standalone evaluation untuk kondisi fisik kartu (Card Condition Model) dua sisi.
"""

from typing import Dict, List, Any, Tuple, Optional
import os
import datetime
import requests
import joblib
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Path setup & load .env
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(backend_dir, ".env"))

import sys
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    from models.chronos_forecaster import ChronosForecaster
except Exception as e:
    print(f"[Analytics Engine] Peringatan: Gagal memuat ChronosForecaster: {e}")
    ChronosForecaster = None

from app.currency_service import get_usd_to_idr_rate, convert_usd_to_idr

# Fallback konstanta jika dibutuhkan secara statis
DEFAULT_USD_TO_IDR = 16500

# =====================================================================
# INISIALISASI MODEL ML FORECASTING & DATASET MASTER
# =====================================================================
_forecast_model = None
_df_master = None
_df_master_indexed = None
_rarity_categories = []
_supertype_categories = []
_lags_cache: Dict[str, Tuple[float, float]] = {}

try:
    model_path = os.path.join(backend_dir, "models", "forecast_model.pkl")
    if os.path.exists(model_path):
        _forecast_model = joblib.load(model_path)
        # Set n_jobs = 1 agar inferensi single-sample berjalan sub-milidetik di Windows tanpa overhead loky multiprocess
        _forecast_model.n_jobs = 1
        print(f"[Analytics Engine] Berhasil memuat model ML dari {model_path} (n_jobs=1)")
    else:
        print(f"[Analytics Engine] Peringatan: File model tidak ditemukan di {model_path}")
    
    # Load dataset for categorical mapping & metadata lookup
    dataset_path = os.path.join(backend_dir, "dataset", "pokemon_cards_dataset_cleaned.csv")
    if os.path.exists(dataset_path):
        _df_master = pd.read_csv(dataset_path)
        _df_master_indexed = _df_master.set_index("card_id")
        _rarity_categories = _df_master["rarity"].astype("category").cat.categories.tolist()
        _supertype_categories = _df_master["supertype"].astype("category").cat.categories.tolist()
        print(f"[Analytics Engine] Berhasil memuat dataset master ({len(_df_master):,} kartu)")
except Exception as e:
    print(f"[Analytics Engine] Peringatan: Gagal memuat ML/Dataset: {e}")


def encode_category(val: str, categories: List[str]) -> int:
    try:
        return categories.index(val)
    except (ValueError, AttributeError):
        return -1


def get_card_metadata(card_id: str) -> Dict[str, Any]:
    """Mengambil metadata spesifikasi kartu dari dataset master lokal."""
    if _df_master_indexed is not None and card_id in _df_master_indexed.index:
        row = _df_master_indexed.loc[card_id]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        
        name = str(row.get("name", card_id))
        release_year = int(row["release_year"]) if pd.notna(row.get("release_year")) else 2024
        rarity = str(row.get("rarity", "Common"))
        supertype = str(row.get("supertype", "Pokémon"))
        subtypes = str(row.get("subtypes", "")) if pd.notna(row.get("subtypes")) else ""
        types = str(row.get("types", "")) if pd.notna(row.get("types")) else ""
        hp = float(row["hp"]) if pd.notna(row.get("hp")) else 0.0
        mkt_price = float(row["effective_market_price"]) if pd.notna(row.get("effective_market_price")) else 0.0
        set_name = str(row.get("set.name", "")) if pd.notna(row.get("set.name")) else ""
        set_id = str(row.get("set.id", "")) if pd.notna(row.get("set.id")) else ""
        set_series = str(row.get("set.series", "")) if pd.notna(row.get("set.series")) else ""
        img_large = str(row.get("images.large", "")) if pd.notna(row.get("images.large")) else ""

        return {
            "card_id": card_id,
            "name": name,
            "release_year": release_year,
            "rarity": rarity,
            "supertype": supertype,
            "subtypes": subtypes,
            "types": types,
            "hp": hp,
            "effective_market_price": mkt_price,
            "set_name": set_name,
            "set_id": set_id,
            "set_series": set_series,
            "image_large": img_large
        }

    return {
        "card_id": card_id,
        "name": card_id,
        "release_year": 2024,
        "rarity": "Common",
        "supertype": "Pokémon",
        "subtypes": "",
        "types": "",
        "hp": 0.0,
        "effective_market_price": 0.0,
        "set_name": "",
        "set_id": "",
        "set_series": "",
        "image_large": ""
    }


def get_price_lags(card_id: str) -> Tuple[float, float]:
    """
    Mengambil data riwayat harga lag_1 dan lag_2.
    Memprioritaskan cache lokal & tabel Supabase card_price_history.
    Jika tidak ada / offline, menggunakan harga pasar dataset master.
    """
    global _lags_cache
    if card_id in _lags_cache:
        return _lags_cache[card_id]

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if supabase_url and supabase_key and card_id:
        try:
            url = f"{supabase_url}/rest/v1/card_price_history?select=effective_market_price&card_id=eq.{card_id}&order=recorded_date.desc&limit=2"
            headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
            res = requests.get(url, headers=headers, timeout=1.0)
            if res.status_code == 200:
                data = res.json()
                if len(data) >= 2:
                    p1 = float(data[0].get("effective_market_price") or 0.0)
                    p2 = float(data[1].get("effective_market_price") or 0.0)
                    if p1 > 0:
                        _lags_cache[card_id] = (p1, (p2 if p2 > 0 else p1))
                        return _lags_cache[card_id]
                elif len(data) == 1:
                    p1 = float(data[0].get("effective_market_price") or 0.0)
                    if p1 > 0:
                        _lags_cache[card_id] = (p1, p1)
                        return _lags_cache[card_id]
        except Exception:
            pass

    # Fallback ke dataset master
    meta = get_card_metadata(card_id)
    fallback_price = float(meta.get("effective_market_price") or 0.0)
    _lags_cache[card_id] = (fallback_price, fallback_price)
    return _lags_cache[card_id]


def predict_fair_value_ml(
    card_id: str,
    release_year: Any,
    rarity: str,
    supertype: str,
    hp: Any,
    lags: Optional[Tuple[float, float]] = None
) -> float:
    """Prediksi harga wajar (fair value) kartu dengan model ML RandomForest."""
    if _forecast_model is None:
        return 0.0
    
    age = 2026 - int(release_year) if release_year else 0
    hp_val = float(hp) if hp and not pd.isna(hp) else 0.0
    rarity_enc = encode_category(rarity, _rarity_categories)
    supertype_enc = encode_category(supertype, _supertype_categories)
    
    if lags is not None:
        lag_1, lag_2 = lags
    else:
        lag_1, lag_2 = get_price_lags(card_id)
    
    features = pd.DataFrame([[lag_1, lag_2, rarity_enc, supertype_enc, age, hp_val]], 
                            columns=['price_lag_1', 'price_lag_2', 'rarity_enc', 'supertype_enc', 'age', 'hp'])
    try:
        pred_log = _forecast_model.predict(features)[0]
        return round(float(np.expm1(pred_log)), 2)
    except Exception as e:
        print(f"[Analytics Engine] Error ML Predict: {e}")
        return 0.0


def calculate_mispricing_signal(actual_price: float, predicted_price: float) -> Tuple[str, float]:
    """Menghitung mispricing gap dan sinyal transaksi wajar."""
    if predicted_price <= 0:
        return "HOLD", 0.0
    
    gap_pct = ((actual_price - predicted_price) / predicted_price) * 100
    gap_pct = round(gap_pct, 2)
    
    if gap_pct < -15.0:
        return "BUY", gap_pct
    elif gap_pct > 5.0:
        return "SELL", gap_pct
    else:
        return "HOLD", gap_pct


# =====================================================================
# TIME-SERIES DATA FETCHING & DYNAMIC TUNNEL SIGNALS
# =====================================================================

def fetch_card_price_series(card_id: str) -> Tuple[List[str], List[float]]:
    """Mengambil deret waktu riwayat harga dari Supabase card_price_history.
    
    Diurutkan secara kronologis (ascending) berdasarkan tanggal rekaman.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key or not card_id:
        return [], []
    try:
        url = f"{supabase_url}/rest/v1/card_price_history?card_id=eq.{card_id}&select=recorded_date,effective_market_price&order=recorded_date.asc"
        headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
        res = requests.get(url, headers=headers, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            dates = [item["recorded_date"] for item in data if item.get("effective_market_price") is not None]
            prices = [float(item["effective_market_price"]) for item in data if item.get("effective_market_price") is not None]
            return dates, prices
    except Exception as e:
        print(f"[Analytics Engine] Gagal fetch card_price_history: {e}")
    return [], []


def calculate_dynamic_tunnel_signal(current_price: float, p10_next: float, p90_next: float, p50_next: float) -> Tuple[str, str, float]:
    """Evaluasi posisi harga riil saat ini terhadap lorong keyakinan kuantil P10-P90 (Dynamic Confidence Tunnel).
    
    Mengembalikan tuple (signal, reason, gap_to_p50_pct).
    """
    if current_price <= 0 or p50_next <= 0:
        return "HOLD", "Data harga acuan tidak mencukupi untuk penentuan sinyal preskriptif.", 0.0

    gap_to_p50_pct = round(((current_price - p50_next) / p50_next) * 100, 2)

    # 1. Menembus batas bawah pesimis -> Margin of Safety Tinggi (Undervalued)
    if current_price < p10_next:
        reason = f"Harga pasar (${current_price:.2f}) berada di bawah batas pesimis P10 (${p10_next:.2f}), memberikan margin keamanan beli tinggi (Undervalued)."
        return "BUY", reason, gap_to_p50_pct

    # 2. Menembus batas atas optimis -> Kemahalan Ekstrem (Overvalued)
    elif current_price > p90_next:
        reason = f"Harga pasar (${current_price:.2f}) melambung di atas batas optimis P90 (${p90_next:.2f}), momentum ideal merealisasikan profit (Overvalued)."
        return "SELL", reason, gap_to_p50_pct

    # 3. Berada di dalam lorong keyakinan -> Transaksi Wajar
    else:
        reason = f"Harga pasar (${current_price:.2f}) stabil bergerak di dalam lorong wajar model [${p10_next:.2f} - ${p90_next:.2f}]."
        return "HOLD", reason, gap_to_p50_pct


# =====================================================================
# 7-DAY MULTI-STEP FORECASTING ENGINE (AMAZON CHRONOS-BOLT)
# =====================================================================

def forecast_7_days(card_id: str, current_price_override: Optional[float] = None) -> Dict[str, Any]:
    """Peramalan harga 7 hari ke depan dengan Amazon Chronos-Bolt Foundation Model & Dynamic Confidence Tunnel.
    
    Menghasilkan pita kuantil P10, P50, dan P90 serta rekomendasi sinyal transaksi (BUY/HOLD/SELL).
    """
    meta = get_card_metadata(card_id)
    card_name = meta["name"]
    release_year = meta["release_year"]
    rarity = meta["rarity"]
    supertype = meta["supertype"]
    hp = meta["hp"]

    current_rate = get_usd_to_idr_rate()
    today = datetime.date.today()

    # 1. Ambil deret waktu harga riil dari Supabase
    hist_dates, hist_prices = fetch_card_price_series(card_id)

    # Tentukan harga dasar saat ini
    if current_price_override is not None and current_price_override > 0:
        curr_price = float(current_price_override)
    elif hist_prices:
        curr_price = float(hist_prices[-1])
    else:
        curr_price = float(meta["effective_market_price"] or 0.0)

    # 2. Eksekusi Amazon Chronos-Bolt jika data riwayat memadai (>= 5 observasi)
    forecast_res = None
    if ChronosForecaster is not None and len(hist_prices) >= 5:
        forecast_res = ChronosForecaster.forecast_7d(hist_dates, hist_prices)

    if forecast_res:
        future_dates = forecast_res["future_dates"]
        p10 = forecast_res["p10"]
        p50 = forecast_res["p50"]
        p90 = forecast_res["p90"]
        predicted_day7 = p50[-1]

        pct_chg = round(((predicted_day7 - curr_price) / curr_price) * 100, 2) if curr_price > 0 else 0.0
        signal, signal_reason, gap_pct = calculate_dynamic_tunnel_signal(curr_price, p10[0], p90[0], p50[0])

        # Hitung tingkat keyakinan AI dinamis berbasis rasio sebaran kuantil
        spread_ratio = (p90[0] - p10[0]) / max(p50[0], 0.01)
        ai_confidence = round(max(55.0, min(98.5, 100.0 - (spread_ratio * 25.0))), 1)

        forecast_points = []
        for d in range(7):
            forecast_points.append({
                "day": d + 1,
                "date": future_dates[d],
                "predicted_price_usd": p50[d],
                "p10_usd": p10[d],
                "p50_usd": p50[d],
                "p90_usd": p90[d]
            })

        quantile_ribbon = {
            "future_dates": future_dates,
            "p10": p10,
            "p50": p50,
            "p90": p90
        }

        return {
            "status": "success",
            "message": f"Berhasil menghitung peramalan harga 7 hari dengan Amazon Chronos-Bolt untuk {card_name}.",
            "card_id": card_id,
            "card_name": card_name,
            "current_price_usd": round(curr_price, 2),
            "current_price_idr": int(round(curr_price * current_rate)),
            "forecast": forecast_points,
            "predicted_price_day7_usd": round(predicted_day7, 2),
            "predicted_price_day7_idr": int(round(predicted_day7 * current_rate)),
            "change_pct": pct_chg,
            "signal": signal,
            "signal_reason": signal_reason,
            "mispricing_gap_pct": gap_pct,
            "ai_confidence_pct": ai_confidence,
            "quantile_ribbon": quantile_ribbon,
            "currency_rate": current_rate
        }

    # Fallback jika riwayat < 5 hari atau Chronos offline
    lag_1, lag_2 = get_price_lags(card_id)
    if curr_price <= 0:
        curr_price = lag_1 if lag_1 > 0 else float(meta["effective_market_price"] or 1.0)
    p_lag_1, p_lag_2 = (lag_1 if lag_1 > 0 else curr_price), (lag_2 if lag_2 > 0 else curr_price)

    age = 2026 - int(release_year) if release_year else 0
    hp_val = float(hp) if hp and not pd.isna(hp) else 0.0
    rarity_enc = encode_category(rarity, _rarity_categories)
    supertype_enc = encode_category(supertype, _supertype_categories)

    forecast_points = []
    p10_list, p50_list, p90_list, f_dates = [], [], [], []

    for day in range(1, 8):
        next_date = (today + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
        f_dates.append(next_date)
        if _forecast_model is not None:
            x_input = pd.DataFrame([{
                "price_lag_1": p_lag_1,
                "price_lag_2": p_lag_2,
                "rarity_enc": rarity_enc,
                "supertype_enc": supertype_enc,
                "age": age,
                "hp": hp_val
            }])
            try:
                pred_log = _forecast_model.predict(x_input)[0]
                next_price = max(0.01, round(float(np.expm1(pred_log)), 2))
            except Exception:
                next_price = p_lag_1
        else:
            next_price = round(curr_price, 2)

        p10_val = round(next_price * 0.90, 2)
        p50_val = next_price
        p90_val = round(next_price * 1.10, 2)

        p10_list.append(p10_val)
        p50_list.append(p50_val)
        p90_list.append(p90_val)

        forecast_points.append({
            "day": day,
            "date": next_date,
            "predicted_price_usd": p50_val,
            "p10_usd": p10_val,
            "p50_usd": p50_val,
            "p90_usd": p90_val
        })
        p_lag_2 = p_lag_1
        p_lag_1 = next_price

    predicted_day7 = forecast_points[-1]["predicted_price_usd"]
    pct_chg = round(((predicted_day7 - curr_price) / curr_price) * 100, 2) if curr_price > 0 else 0.0
    predicted_fair_value = predict_fair_value_ml(card_id, release_year, rarity, supertype, hp, lags=(lag_1, lag_2))
    ml_sig, mispricing_gap_pct = calculate_mispricing_signal(curr_price, predicted_fair_value)

    fallback_reason = "Riwayat deret waktu kartu kurang dari 5 hari; menggunakan estimasi regresi tabular dengan batas rentang default."

    return {
        "status": "success",
        "message": f"Estimasi tren 7 hari untuk {card_name} (Riwayat deret waktu < 5 hari).",
        "card_id": card_id,
        "card_name": card_name,
        "current_price_usd": round(curr_price, 2),
        "current_price_idr": int(round(curr_price * current_rate)),
        "forecast": forecast_points,
        "predicted_price_day7_usd": round(predicted_day7, 2),
        "predicted_price_day7_idr": int(round(predicted_day7 * current_rate)),
        "change_pct": pct_chg,
        "signal": ml_sig,
        "signal_reason": fallback_reason,
        "mispricing_gap_pct": mispricing_gap_pct,
        "ai_confidence_pct": None,
        "quantile_ribbon": {
            "future_dates": f_dates,
            "p10": p10_list,
            "p50": p50_list,
            "p90": p90_list
        },
        "currency_rate": current_rate
    }


# =====================================================================
# EVALUASI KONDISI FISIK KARTU (CARD CONDITION MODEL)
# =====================================================================

def calculate_condition_factor(defects: List[Dict[str, Any]]) -> Tuple[float, str, float]:
    """
    Menghitung pengali kondisi fisik (F_condition), kategori tier, dan persentase diskon.
    
    Aturan Diskon Cacat Fisik:
    - Tidak ada cacat    : Multiplier = 1.00 (Diskon 0%)  -> "Near Mint / Mint"
    - Scratched (Lecet)  : Multiplier = 0.85 (Diskon 15%) -> "Lightly Played (LP)"
    - Edge Wear (Aus)    : Multiplier = 0.80 (Diskon 20%) -> "Moderately Played (MP)"
    - Bent / Crease      : Multiplier = 0.65 (Diskon 35%) -> "Heavily Played (HP)"
    - Akumulasi cacat berat: Dibatasi minimal 0.40        -> "Damaged"
    """
    if not defects:
        return 1.00, "Near Mint / Mint", 0.0

    multiplier = 1.00
    defect_names = [d.get("label", "").lower() for d in defects]

    # Evaluasi potongan berdasarkan cacat terparah
    has_crease = any("crease" in name or "bent" in name for name in defect_names)
    has_edge = any("edge" in name or "wear" in name or "corner" in name for name in defect_names)
    has_scratch = any("scratch" in name for name in defect_names)

    if has_crease:
        multiplier *= 0.65
    if has_edge:
        multiplier *= 0.80
    if has_scratch:
        multiplier *= 0.85

    # Batas minimum multiplier agar tidak negatif / nol
    multiplier = max(0.40, round(multiplier, 2))
    discount_pct = round((1.0 - multiplier) * 100, 2)

    # Klasifikasi Tingkat Kondisi
    if multiplier >= 0.95:
        tier = "Near Mint / Mint"
    elif multiplier >= 0.80:
        tier = "Lightly Played (LP)"
    elif multiplier >= 0.65:
        tier = "Moderately Played (MP)"
    elif multiplier >= 0.50:
        tier = "Heavily Played (HP)"
    else:
        tier = "Damaged"

    return multiplier, tier, discount_pct


def calculate_variant_multiplier(release_year: Any, rarity: str = "") -> float:
    """
    Menghitung pengali vintage dan kelangkaan (M_variant).
    - Vintage Factor: Kartu dengan tahun rilis < 2005 diberi apresiasi nilai kelangkaan kolektor (+20%).
    """
    multiplier = 1.00
    try:
        if release_year is not None and int(release_year) < 2005:
            multiplier += 0.20  # +20% apresiasi vintage era WotC/EX awal
    except (ValueError, TypeError):
        pass

    return round(multiplier, 2)


def evaluate_card_condition_standalone(
    card_id: str,
    defects: Optional[List[Dict[str, Any]]] = None,
    front_defects: Optional[List[Dict[str, Any]]] = None,
    back_defects: Optional[List[Dict[str, Any]]] = None,
    base_price_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluasi standalone kondisi fisik kartu (Model 2 Card Condition Grader).
    Mendukung penilaian gabungan dua sisi (Tampak Depan & Tampak Belakang).
    Menghitung skor kondisi (0-100%), diskon cacat fisik, dan penyesuaian harga pasar.
    """
    meta = get_card_metadata(card_id)
    card_name = meta["name"]
    release_year = meta["release_year"]
    rarity = meta["rarity"]
    
    # Gabungkan defect dari tampak depan dan tampak belakang jika disediakan
    f_dets = front_defects or []
    b_dets = back_defects or []
    if front_defects is not None or back_defects is not None:
        all_defects = f_dets + b_dets
    else:
        all_defects = defects or []

    # Ambil base price
    if base_price_override is not None and base_price_override > 0:
        base_price_usd = float(base_price_override)
    else:
        base_price_usd = float(meta["effective_market_price"] or 0.0)

    current_rate = get_usd_to_idr_rate()
    base_price_idr = int(round(base_price_usd * current_rate))

    # 1. Hitung Pengali Kondisi Fisik
    f_condition, condition_tier, discount_pct = calculate_condition_factor(all_defects)
    condition_score_pct = round(f_condition * 100.0, 1)

    # 2. Hitung Pengali Varian/Vintage
    m_variant = calculate_variant_multiplier(release_year, rarity)

    # 3. Hitung Harga Pasar Akhir
    final_price_usd = round(base_price_usd * m_variant * f_condition, 2)
    final_price_idr = int(round(final_price_usd * current_rate))

    return {
        "status": "success",
        "message": f"Kondisi fisik kartu {card_name}: {condition_tier} ({condition_score_pct}%).",
        "card_id": card_id,
        "card_name": card_name,
        "condition_score_pct": condition_score_pct,
        "condition_report": {
            "condition_tier": condition_tier,
            "has_defects": len(all_defects) > 0,
            "defect_count": len(all_defects),
            "front_defects": f_dets,
            "back_defects": b_dets,
            "defects": all_defects,
            "evaluation_status": "evaluated"
        },
        "pricing": {
            "base_price_usd": round(base_price_usd, 2),
            "base_price_idr": base_price_idr,
            "condition_multiplier": f_condition,
            "condition_discount_pct": discount_pct,
            "final_price_usd": final_price_usd,
            "final_price_idr": final_price_idr,
            "currency_rate": current_rate
        }
    }


def evaluate_card_valuation(
    card_id: str,
    base_price_usd: float,
    release_year: Any = None,
    rarity: str = "",
    supertype: str = "",
    hp: Any = None,
    defects: List[Dict[str, Any]] = None,
    usd_rate: int = DEFAULT_USD_TO_IDR
) -> Dict[str, Any]:
    """
    Menghitung valuasi menyeluruh untuk satu kartu.
    Mengembalikan dictionary rincian harga dasar, pengali, harga akhir, dan sinyal.
    """
    defects = defects or []
    current_rate = float(usd_rate) if (usd_rate and usd_rate > 0) else get_usd_to_idr_rate()
    base_price = max(0.0, float(base_price_usd or 0.0))
    base_price_idr = int(round(base_price * current_rate))

    # 1. Hitung Pengali Kondisi Fisik
    f_condition, condition_tier, discount_pct = calculate_condition_factor(defects)

    # 2. Hitung Pengali Varian/Vintage
    m_variant = calculate_variant_multiplier(release_year, rarity)

    # 3. Hitung Harga Wajar Akhir (P_final)
    final_price_usd = round(base_price * m_variant * f_condition, 2)
    final_price_idr = int(round(final_price_usd * current_rate))

    # 4. Integrasi Model 3 Chronos-Bolt untuk Valuasi Preskriptif
    hist_dates, hist_prices = fetch_card_price_series(card_id)
    forecast_ribbon = None
    signal_reason = None

    if ChronosForecaster is not None and len(hist_prices) >= 5:
        forecast_res = ChronosForecaster.forecast_7d(hist_dates, hist_prices)
        if forecast_res:
            p10_1d = forecast_res["p10"][0]
            p50_1d = forecast_res["p50"][0]
            p90_1d = forecast_res["p90"][0]
            signal, signal_reason, gap_pct = calculate_dynamic_tunnel_signal(final_price_usd, p10_1d, p90_1d, p50_1d)
            predicted_fair_value_usd = p50_1d
            forecast_ribbon = {
                "future_dates": forecast_res["future_dates"],
                "p10": forecast_res["p10"],
                "p50": forecast_res["p50"],
                "p90": forecast_res["p90"]
            }

    if forecast_ribbon is None:
        predicted_fair_value_usd = predict_fair_value_ml(card_id, release_year, rarity, supertype, hp)
        ml_signal, gap_pct = calculate_mispricing_signal(final_price_usd, predicted_fair_value_usd)
        if discount_pct >= 30.0:
            signal = "HOLD"
            signal_reason = f"Kondisi fisik kartu memiliki diskon cacat {discount_pct:.1f}%; transaksi disarankan ditahan (HOLD)."
        elif predicted_fair_value_usd > 0:
            signal = ml_signal
            signal_reason = f"Selisih harga terhadap nilai wajar ML: {gap_pct:+.1f}%."
        else:
            signal = "HOLD"
            signal_reason = "Data riwayat transaksi deret waktu terbatas; rekomendasi ditahan."

    return {
        "pricing": {
            "base_price_usd": base_price,
            "base_price_idr": base_price_idr,
            "condition_multiplier": f_condition,
            "condition_discount_pct": discount_pct,
            "final_price_usd": final_price_usd,
            "final_price_idr": final_price_idr,
            "currency_rate": current_rate
        },
        "condition_report": {
            "condition_tier": condition_tier,
            "has_defects": len(defects) > 0,
            "defect_count": len(defects),
            "front_defects": [],
            "back_defects": [],
            "defects": defects,
            "evaluation_status": "evaluated"
        },
        "market_analytics": {
            "predicted_fair_value_usd": predicted_fair_value_usd,
            "predicted_fair_value_idr": int(predicted_fair_value_usd * current_rate),
            "mispricing_gap_pct": gap_pct,
            "signal_reason": signal_reason,
            "forecast_7d": forecast_ribbon
        },
        "recommendation_signal": signal
    }
