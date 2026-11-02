"""
backend/models/rf_forecaster.py
Engine Peramalan Harga Deret Waktu Multi-Langkah Menggunakan Random Forest Panel Regressor.

Menggabungkan 8 fitur dinamika pasar (lag harga, moving average, volatilitas, momentum)
dan 9 fitur fundamental domain Pokémon TCG (rarity, karakter, set, era, ilustrator).
Menghasilkan proyeksi 7 hari ke depan beserta pita kuantil ensemble (P10, P50, P90)
dari distribusi prediksi pohon keputusan dan sinyal adaptif berbasis volatilitas.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "price_lag_1",
    "price_lag_2",
    "price_lag_3",
    "ma_3",
    "volatility_3",
    "momentum_1d",
    "momentum_3d",
    "price_to_ma_ratio",
    "rarity_rank",
    "char_popularity_rank",
    "set_rank",
    "series_rank",
    "subtype_rank",
    "supertype_rank",
    "artist_rank",
    "release_year",
    "is_vintage",
]

_rf_model = None
_card_static_features: Dict[str, Dict[str, float]] = {}
_default_static_features: Dict[str, float] = {
    "rarity_rank": 0.0,
    "char_popularity_rank": 0.0,
    "set_rank": 0.0,
    "series_rank": 0.0,
    "subtype_rank": 0.0,
    "supertype_rank": 0.0,
    "artist_rank": 0.0,
    "release_year": 2024.0,
    "is_vintage": 0.0,
}
_initialized = False


def _rank_encode(df: pd.DataFrame, col: str, target: str = "effective_market_price") -> pd.Series:
    filled = df[col].fillna("Unknown")
    order = df.groupby(filled)[target].median().sort_values().index
    mapping = {val: float(idx) for idx, val in enumerate(order)}
    return filled.map(mapping).fillna(0.0)


def _init_rf_engine() -> None:
    """Memuat model Random Forest dan mengindeks fitur fundamental statis untuk 20.617 kartu."""
    global _rf_model, _card_static_features, _default_static_features, _initialized
    if _initialized:
        return

    _initialized = True
    models_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(models_dir)

    model_path = os.path.join(models_dir, "forecast_model.pkl")
    if os.path.exists(model_path):
        try:
            loaded = joblib.load(model_path)
            if isinstance(loaded, dict) and "model" in loaded:
                _rf_model = loaded["model"]
            else:
                _rf_model = loaded
            # n_jobs=1 mencegah overhead loky multiprocessing untuk inferensi 1 kartu
            _rf_model.n_jobs = 1
            print(f"[OK] [RF Forecaster] Berhasil memuat Random Forest dari {model_path}")
        except Exception as e:
            print(f"[ERROR] [RF Forecaster] Gagal memuat model {model_path}: {e}")
            _rf_model = None
    else:
        print(f"[WARN] [RF Forecaster] File model tidak ditemukan di {model_path}")

    dataset_path = os.path.join(backend_dir, "dataset", "pokemon_cards_dataset_cleaned.csv")
    if os.path.exists(dataset_path):
        try:
            df = pd.read_csv(dataset_path)
            df["rarity_rank"] = _rank_encode(df, "rarity")
            df["subtype_rank"] = _rank_encode(df, "subtypes")
            df["supertype_rank"] = _rank_encode(df, "supertype")
            df["set_rank"] = _rank_encode(df, "set.id")
            df["series_rank"] = _rank_encode(df, "set.series")
            df["artist_rank"] = _rank_encode(df, "artist")
            df["char_popularity_rank"] = _rank_encode(df, "name")
            df["release_year_clean"] = pd.to_numeric(df["release_year"], errors="coerce").fillna(2024.0)
            df["is_vintage"] = (df["release_year_clean"] < 2005).astype(float)

            static_cols = [
                "rarity_rank",
                "char_popularity_rank",
                "set_rank",
                "series_rank",
                "subtype_rank",
                "supertype_rank",
                "artist_rank",
                "release_year_clean",
                "is_vintage",
            ]
            _default_static_features = {
                "rarity_rank": float(df["rarity_rank"].median()),
                "char_popularity_rank": float(df["char_popularity_rank"].median()),
                "set_rank": float(df["set_rank"].median()),
                "series_rank": float(df["series_rank"].median()),
                "subtype_rank": float(df["subtype_rank"].median()),
                "supertype_rank": float(df["supertype_rank"].median()),
                "artist_rank": float(df["artist_rank"].median()),
                "release_year": 2024.0,
                "is_vintage": 0.0,
            }

            records = df[["card_id"] + static_cols].drop_duplicates(subset=["card_id"]).to_dict("records")
            _card_static_features = {
                str(r["card_id"]): {
                    "rarity_rank": float(r["rarity_rank"]),
                    "char_popularity_rank": float(r["char_popularity_rank"]),
                    "set_rank": float(r["set_rank"]),
                    "series_rank": float(r["series_rank"]),
                    "subtype_rank": float(r["subtype_rank"]),
                    "supertype_rank": float(r["supertype_rank"]),
                    "artist_rank": float(r["artist_rank"]),
                    "release_year": float(r["release_year_clean"]),
                    "is_vintage": float(r["is_vintage"]),
                }
                for r in records
            }
            print(f"[OK] [RF Forecaster] Indeks fitur fundamental siap ({len(_card_static_features):,} kartu)")
        except Exception as e:
            print(f"[ERROR] [RF Forecaster] Gagal membangun indeks fitur fundamental: {e}")


def get_static_features(card_id: str) -> Dict[str, float]:
    _init_rf_engine()
    return _card_static_features.get(card_id, _default_static_features)


def _predict_step_quantiles(x_row: np.ndarray) -> Tuple[float, float, float]:
    """Menghitung kuantil P10, P50, dan P90 dari distribusi prediksi pohon di dalam Random Forest."""
    if _rf_model is None:
        val = float(x_row[0, 0])
        return round(val * 0.90, 2), round(val, 2), round(val * 1.10, 2)

    tree_logs = np.array([tree.predict(x_row)[0] for tree in _rf_model.estimators_], dtype=np.float64)
    tree_dollars = np.maximum(np.expm1(tree_logs), 0.01)

    p10 = float(np.percentile(tree_dollars, 10))
    # Gunakan eksponensial dari rata-rata log pohon agar konsisten dengan RandomForestRegressor.predict()
    p50 = float(max(0.01, np.expm1(np.mean(tree_logs))))
    p90 = float(np.percentile(tree_dollars, 90))

    p50 = max(p50, p10)
    p90 = max(p90, p50)
    return p10, p50, p90


class RFForecaster:
    @staticmethod
    def is_ready() -> bool:
        _init_rf_engine()
        return _rf_model is not None

    @staticmethod
    def predict_fair_value(card_id: str, history_prices: List[float], fallback_price: float = 0.0) -> float:
        """Menghitung estimasi harga wajar 1 langkah (H+1) menggunakan 17 fitur Random Forest."""
        _init_rf_engine()
        if _rf_model is None:
            return 0.0

        valid_prices = [float(p) for p in history_prices if p is not None and float(p) > 0]
        if not valid_prices:
            if fallback_price <= 0:
                return 0.0
            valid_prices = [fallback_price]

        p1 = valid_prices[-1]
        p2 = valid_prices[-2] if len(valid_prices) >= 2 else p1
        p3 = valid_prices[-3] if len(valid_prices) >= 3 else p2

        ma_3 = (p1 + p2 + p3) / 3.0
        vol_3 = float(np.std([p1, p2, p3], ddof=1))
        mom_1d = float(np.clip((p1 - p2) / p2, -5.0, 5.0)) if p2 > 0 else 0.0
        mom_3d = float(np.clip((p1 - p3) / p3, -5.0, 5.0)) if p3 > 0 else 0.0
        p_ma_ratio = float(np.clip(p1 / ma_3, 0.1, 10.0)) if ma_3 > 0 else 1.0

        sf = get_static_features(card_id)
        x_row = np.array([[
            p1, p2, p3, ma_3, vol_3, mom_1d, mom_3d, p_ma_ratio,
            sf["rarity_rank"], sf["char_popularity_rank"], sf["set_rank"],
            sf["series_rank"], sf["subtype_rank"], sf["supertype_rank"],
            sf["artist_rank"], sf["release_year"], sf["is_vintage"],
        ]], dtype=np.float64)

        _, p50, _ = _predict_step_quantiles(x_row)
        return round(p50, 2)

    @staticmethod
    def calculate_adaptive_signal(
        current_price: float,
        predicted_day7: float,
        history_prices: List[float],
        p10_day1: float,
        p90_day1: float,
    ) -> Tuple[str, str, float, float]:
        """Menentukan sinyal BUY/HOLD/SELL dengan ambang batas volatilitas adaptif kartu.

        Returns:
            Tuple (signal, reason, adaptive_threshold_pct, card_volatility_pct).
        """
        if current_price <= 0 or predicted_day7 <= 0:
            return "HOLD", "Data harga acuan tidak mencukupi untuk penentuan sinyal transaksi.", 5.0, 0.0

        pct_chg = ((predicted_day7 - current_price) / current_price) * 100.0

        valid_prices = [float(p) for p in history_prices if p is not None and float(p) > 0]
        if len(valid_prices) >= 3:
            returns = pd.Series(valid_prices).pct_change().dropna() * 100.0
            vol = float(returns.std()) if len(returns) >= 2 else 0.0
        else:
            vol = 0.0

        if np.isnan(vol) or vol <= 0.0:
            threshold = 5.0
            vol = 0.0
        else:
            threshold = float(max(3.0, min(15.0, 1.5 * vol)))

        if pct_chg >= threshold:
            reason = (
                f"Proyeksi Random Forest 7 hari naik {pct_chg:+.2f}% (${current_price:.2f} -> ${predicted_day7:.2f}), "
                f"melampaui ambang volatilitas adaptif kartu (+/-{threshold:.1f}%)."
            )
            return "BUY", reason, round(threshold, 2), round(vol, 2)

        if pct_chg <= -threshold:
            reason = (
                f"Proyeksi Random Forest 7 hari terkoreksi {pct_chg:+.2f}% (${current_price:.2f} -> ${predicted_day7:.2f}), "
                f"melewati batas toleransi volatilitas adaptif (+/-{threshold:.1f}%)."
            )
            return "SELL", reason, round(threshold, 2), round(vol, 2)

        reason = (
            f"Proyeksi 7 hari ({pct_chg:+.2f}%) bergerak stabil di dalam batas volatilitas adaptif "
            f"+/-{threshold:.1f}% (rentang kuantil pohon [${p10_day1:.2f} - ${p90_day1:.2f}])."
        )
        return "HOLD", reason, round(threshold, 2), round(vol, 2)

    @staticmethod
    def forecast_7d(
        card_id: str,
        history_dates: List[str],
        history_prices: List[float],
        fallback_price: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Menghasilkan proyeksi rekursif 7 hari ke depan beserta kuantil P10, P50, P90 dan metrik volatilitas."""
        _init_rf_engine()
        if _rf_model is None:
            return None

        try:
            clean_prices: List[float] = []
            last_date = datetime.now()

            if history_dates and history_prices and len(history_dates) == len(history_prices):
                df = pd.DataFrame({"date": pd.to_datetime(history_dates), "price": pd.to_numeric(history_prices, errors="coerce")})
                df = df.dropna(subset=["price"])
                df = df[df["price"] > 0].drop_duplicates(subset=["date"]).sort_values("date")
                if not df.empty:
                    last_recorded = df["date"].iloc[-1].to_pydatetime()
                    if last_recorded > last_date:
                        last_date = last_recorded
                    df_resampled = df.set_index("date").resample("D").ffill().dropna()
                    clean_prices = [float(x) for x in df_resampled["price"].values]

            if not clean_prices:
                if fallback_price <= 0:
                    return None
                clean_prices = [float(fallback_price)]

            p_lag_1 = clean_prices[-1]
            p_lag_2 = clean_prices[-2] if len(clean_prices) >= 2 else p_lag_1
            p_lag_3 = clean_prices[-3] if len(clean_prices) >= 3 else p_lag_2

            sf = get_static_features(card_id)
            p10_list: List[float] = []
            p50_list: List[float] = []
            p90_list: List[float] = []
            future_dates: List[str] = []

            for day in range(1, 8):
                next_date_str = (last_date + timedelta(days=day)).strftime("%Y-%m-%d")
                future_dates.append(next_date_str)

                ma_3 = (p_lag_1 + p_lag_2 + p_lag_3) / 3.0
                vol_3 = float(np.std([p_lag_1, p_lag_2, p_lag_3], ddof=1))
                mom_1d = float(np.clip((p_lag_1 - p_lag_2) / p_lag_2, -5.0, 5.0)) if p_lag_2 > 0 else 0.0
                mom_3d = float(np.clip((p_lag_1 - p_lag_3) / p_lag_3, -5.0, 5.0)) if p_lag_3 > 0 else 0.0
                p_ma_ratio = float(np.clip(p_lag_1 / ma_3, 0.1, 10.0)) if ma_3 > 0 else 1.0

                x_row = np.array([[
                    p_lag_1, p_lag_2, p_lag_3, ma_3, vol_3, mom_1d, mom_3d, p_ma_ratio,
                    sf["rarity_rank"], sf["char_popularity_rank"], sf["set_rank"],
                    sf["series_rank"], sf["subtype_rank"], sf["supertype_rank"],
                    sf["artist_rank"], sf["release_year"], sf["is_vintage"],
                ]], dtype=np.float64)

                p10, p50, p90 = _predict_step_quantiles(x_row)
                p10_list.append(round(p10, 2))
                p50_list.append(round(p50, 2))
                p90_list.append(round(p90, 2))

                p_lag_3 = p_lag_2
                p_lag_2 = p_lag_1
                p_lag_1 = p50

            signal, signal_reason, threshold, vol = RFForecaster.calculate_adaptive_signal(
                current_price=clean_prices[-1],
                predicted_day7=p50_list[-1],
                history_prices=clean_prices,
                p10_day1=p10_list[0],
                p90_day1=p90_list[0],
            )

            return {
                "future_dates": future_dates,
                "p10": p10_list,
                "p50": p50_list,
                "p90": p90_list,
                "last_known_price": round(float(clean_prices[-1]), 2),
                "signal": signal,
                "signal_reason": signal_reason,
                "adaptive_threshold_pct": threshold,
                "volatility_pct": vol,
            }
        except Exception as e:
            print(f"[ERROR] [RF Forecaster] Gagal melakukan inferensi peramalan: {e}")
            return None

