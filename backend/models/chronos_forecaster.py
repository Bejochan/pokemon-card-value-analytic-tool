"""
backend/models/chronos_forecaster.py
====================================
Engine Peramalan Harga Deret Waktu Multi-Langkah Menggunakan Amazon Chronos-Bolt
(AWS Research Foundation Model 2024).

Menghasilkan proyeksi 7 hari ke depan secara probabilistik dengan tiga kurva kuantil serentak:
- P10: Batas Bawah / Skenario Pesimis Pasar
- P50: Median Wajar / Target Nilai Pasar Wajar (Fair Market Value)
- P90: Batas Atas / Skenario Optimis Pasar
"""
import os
if "HF_HUB_OFFLINE" not in os.environ:
    os.environ["HF_HUB_OFFLINE"] = "1"
if "TRANSFORMERS_OFFLINE" not in os.environ:
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import torch

_chronos_pipeline = None


def get_chronos_pipeline():
    """Lazy loader untuk model Amazon Chronos-Bolt.
    
    Model hanya dimuat ke memori VRAM/RAM saat inferensi pertama kali dipanggil,
    sehingga waktu startup server FastAPI tetap instan (< 1 detik).
    """
    global _chronos_pipeline
    if _chronos_pipeline is None:
        try:
            print("[INFO] [Chronos Engine] Memuat bobot model Amazon Chronos-Bolt...")
            from chronos import ChronosBoltPipeline  # type: ignore
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _chronos_pipeline = ChronosBoltPipeline.from_pretrained(
                "amazon/chronos-bolt-mini",
                device_map=device,
                dtype=torch.float32,
            )
            print(f"[OK] [Chronos Engine] Amazon Chronos-Bolt siap digunakan pada device: {device.upper()}!")
        except Exception as e:
            print(f"[ERROR] [Chronos Engine] Gagal memuat Amazon Chronos-Bolt: {e}")
            return None
    return _chronos_pipeline


class ChronosForecaster:
    @staticmethod
    def forecast_7d(history_dates: List[str], history_prices: List[float]) -> Optional[Dict[str, Any]]:
        """Menghasilkan proyeksi harga 7 hari ke depan lengkap dengan batas kuantil P10, P50, dan P90.
        
        Args:
            history_dates: Daftar tanggal riwayat transaksi pasar (format 'YYYY-MM-DD').
            history_prices: Daftar harga pasar aktual (effective_market_price dalam USD).
            
        Returns:
            Dictionary berisi future_dates, p10, p50, p90, dan last_known_price,
            atau None jika data riwayat < 5 hari atau model gagal memproses.
        """
        if not history_prices or len(history_prices) < 5:
            return None

        pipeline = get_chronos_pipeline()
        if pipeline is None:
            return None

        try:
            # 1. Bersihkan deret waktu: forward-fill dan buat kalender harian berurutan
            df = pd.DataFrame({"date": pd.to_datetime(history_dates), "price": history_prices})
            df = df.drop_duplicates(subset=["date"]).sort_values("date").set_index("date")
            df_resampled = df.resample("D").ffill().dropna()

            clean_prices = df_resampled["price"].values
            if len(clean_prices) < 5:
                return None

            # 2. Konversi ke tensor 1D konteks waktu
            context = torch.tensor(clean_prices, dtype=torch.float32)

            # 3. Inferensi langsung kuantil multi-step 7 hari (Chronos-Bolt zero-shot)
            prediction_length = 7
            forecast = pipeline.predict(context, prediction_length=prediction_length)
            # Output tensor shape: [1, 9, prediction_length]
            # 9 kuantil resmi Chronos-Bolt: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

            # 4. Ekstrak Kuantil P10 (indeks 0), P50 (indeks 4), dan P90 (indeks 8)
            low_p10 = forecast[0, 0, :].cpu().numpy()
            median_p50 = forecast[0, 4, :].cpu().numpy()
            high_p90 = forecast[0, 8, :].cpu().numpy()

            # Pastikan tidak ada nilai negatif pada harga pasar (floor at $0.01)
            low_p10 = np.maximum(low_p10, 0.01)
            median_p50 = np.maximum(median_p50, 0.01)
            high_p90 = np.maximum(high_p90, 0.01)

            # Jamin keterurutan monoton P10 <= P50 <= P90
            median_p50 = np.maximum(median_p50, low_p10)
            high_p90 = np.maximum(high_p90, median_p50)

            # 5. Susun deret tanggal masa depan (7 hari ke depan dari tanggal terakhir)
            last_date = df_resampled.index[-1]
            future_dates = [(last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(prediction_length)]

            return {
                "future_dates": future_dates,
                "p10": [round(float(x), 2) for x in low_p10],
                "p50": [round(float(x), 2) for x in median_p50],
                "p90": [round(float(x), 2) for x in high_p90],
                "last_known_price": round(float(clean_prices[-1]), 2),
            }
        except Exception as e:
            print(f"[ERROR] [Chronos Engine] Gagal melakukan inferensi peramalan: {e}")
            return None
