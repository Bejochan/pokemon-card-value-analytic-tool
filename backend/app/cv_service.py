"""
backend/app/cv_service.py
=========================
Layanan Computer Vision (CV Service) untuk Regokemon:
1. Memuat dan mengelola Model 1 (OpenAI CLIP ViT-B-32 + FAISS Index 20.617 kartu).
2. Menghubungkan Model 2 (Roboflow YOLOv8 Condition Grader) untuk deteksi cacat fisik.
3. Mendekode gambar Base64 / Bytes murni di memori RAM tanpa I/O file sampah di disk.
"""

import os
import sys
import base64
import requests
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

# Pastikan terminal Windows tidak crash saat print karakter/emoji
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from models.card_identifier import CardIdentifier
from app.analytics_engine import evaluate_card_valuation, DEFAULT_USD_TO_IDR


# =====================================================================
# INISIALISASI MODEL VISION SINGLETON
# =====================================================================

print("[INFO] [CV Service] Menginisialisasi Model 1 (Card Identifier CLIP + FAISS)...")
# Menggunakan default CardIdentifier (use_orb_rerank=True, orb_rerank_pool_size=150) untuk akurasi maksimal
_card_identifier = CardIdentifier()
print("[OK] [CV Service] Model 1 siap digunakan!")

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_CONFIDENCE = int(os.getenv("ROBOFLOW_CONFIDENCE", "80"))


# =====================================================================
# FUNGSI HELPER DECODING GAMBAR DI RAM
# =====================================================================

def decode_base64_to_cv2(image_b64: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Mendekode string Base64 langsung menjadi gambar OpenCV BGR (np.ndarray) di RAM.
    Mengembalikan (img_bgr, clean_base64_string).
    """
    try:
        # Bersihkan prefix data URL jika ada (e.g., 'data:image/jpeg;base64,...')
        if "," in image_b64:
            clean_b64 = image_b64.split(",")[1].strip()
        else:
            clean_b64 = image_b64.strip()

        img_bytes = base64.b64decode(clean_b64)
        img_arr = np.frombuffer(img_bytes, np.uint8)
        img_bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return None, None

        return img_bgr, clean_b64
    except Exception as e:
        print(f"[CV Service] Gagal mendekode Base64: {e}")
        return None, None


def decode_bytes_to_cv2(image_bytes: bytes) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Mendekode raw bytes menjadi gambar OpenCV BGR di RAM."""
    try:
        img_arr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        clean_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return img_bgr, clean_b64
    except Exception as e:
        print(f"[CV Service] Gagal mendekode Bytes: {e}")
        return None, None


# =====================================================================
# PEMANGGILAN MODEL 2 (ROBOFLOW CONDITION GRADER) DI RAM
# =====================================================================

def detect_defects_in_memory(clean_base64_data: str) -> List[Dict[str, Any]]:
    """
    Mengirimkan payload Base64 langsung ke endpoint Roboflow Cloud Inference via HTTP.
    Tidak ada penulisan file fisik sementara ke disk.
    """
    if not ROBOFLOW_API_KEY:
        print("[CV Service] Peringatan: ROBOFLOW_API_KEY belum diset di .env. Pengecekan cacat dilewati.")
        return []

    try:
        api_url = (
            f"https://detect.roboflow.com/card-grader/4"
            f"?api_key={ROBOFLOW_API_KEY}&confidence={ROBOFLOW_CONFIDENCE}"
        )
        response = requests.post(
            api_url,
            data=clean_base64_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )
        if response.status_code != 200:
            print(f"[CV Service] Roboflow API error HTTP {response.status_code}: {response.text[:200]}")
            return []

        result_json = response.json()
        predictions = result_json.get("predictions", [])

        formatted_defects = []
        for pred in predictions:
            formatted_defects.append({
                "label": pred.get("class", "defect"),
                "confidence": round(float(pred.get("confidence", 0.0)), 2),
                "bbox": {
                    "x": pred.get("x"),
                    "y": pred.get("y"),
                    "width": pred.get("width"),
                    "height": pred.get("height")
                }
            })
        return formatted_defects

    except Exception as e:
        print(f"[CV Service] Gagal memanggil Roboflow API: {e}")
        return []


# =====================================================================
# FUNGSI SERVICE UTAMA
# =====================================================================

def process_card_identification(img_bgr: np.ndarray, top_k: int = 4) -> Dict[str, Any]:
    """
    Menjalankan Model 1 CLIP ViT-B-32 pada gambar OpenCV di memori RAM.
    Mengembalikan data kartu utama dan daftar kandidat alternatif.
    """
    ai_result = _card_identifier.identify_card(
        image_input=img_bgr,
        top_k=top_k,
        debug=False
    )
    return ai_result


def build_candidates_list(candidates_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Memformat daftar runner-up kandidat kartu untuk ditampilkan di UI."""
    candidates = []
    # Mulai dari indeks 1 (kartu alternatif, karena indeks 0 adalah top match)
    for c in candidates_raw[1:]:
        candidates.append({
            "rank": c.get("rank", 0),
            "card_id": c.get("card_id", ""),
            "name": c.get("name", "Unknown"),
            "confidence_percentage": c.get("confidence_percentage", 0.0),
            "raw_similarity_score": c.get("raw_similarity_score", 0.0),
            "set_name": c.get("set_name"),
            "rarity": c.get("rarity"),
            "official_image_url": c.get("image_url_large")
        })
    return candidates


def run_identify_flow(img_bgr: np.ndarray, top_k: int = 4) -> Dict[str, Any]:
    """
    Alur khusus ON-CAM / Scanner Cepat:
    Hanya menjalankan Model 1 (Identifikasi jenis kartu) tanpa deteksi cacat.
    """
    ai_result = process_card_identification(img_bgr, top_k=top_k)
    top_match = ai_result.get("top_match")

    if not top_match:
        return {
            "status": "error",
            "message": "AI tidak dapat mengenali kartu dari foto yang diberikan.",
            "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
        }

    # Hitung harga dasar (tanpa diskon cacat fisik)
    price_usd = float(top_match.get("effective_market_price") or 0.0)
    price_idr = int(price_usd * DEFAULT_USD_TO_IDR)

    candidates = build_candidates_list(ai_result.get("candidates", []))

    return {
        "status": "success",
        "message": f"Berhasil mendeteksi: {top_match.get('name', 'Unknown')}",
        "card_id": top_match.get("card_id"),
        "name": top_match.get("name"),
        "set_name": top_match.get("set_name"),
        "set_id": top_match.get("set_id"),
        "set_series": top_match.get("set_series"),
        "release_year": int(top_match.get("release_year")) if top_match.get("release_year") else None,
        "rarity": top_match.get("rarity"),
        "supertype": top_match.get("supertype"),
        "subtypes": top_match.get("subtypes"),
        "types": top_match.get("types"),
        "hp": float(top_match.get("hp")) if top_match.get("hp") else None,
        "confidence_percentage": top_match.get("confidence_percentage", 0.0),
        "confidence_label": top_match.get("confidence_label", "Uncertain"),
        "official_image_url": top_match.get("image_url_large"),
        "pricing": {
            "base_price_usd": price_usd,
            "base_price_idr": price_idr,
            "condition_multiplier": 1.0,
            "condition_discount_pct": 0.0,
            "final_price_usd": price_usd,
            "final_price_idr": price_idr,
            "currency_rate": DEFAULT_USD_TO_IDR
        },
        "estimated_price": price_idr,
        "card_condition": "Tidak Dievaluasi (Mode On-Cam)",
        "candidates": candidates,
        "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
    }


def run_analyze_flow(img_bgr: np.ndarray, clean_b64: str, top_k: int = 4) -> Dict[str, Any]:
    """
    Alur khusus UPLOAD FOTO STATIS:
    Menjalankan Model 1 (Identifikasi Kartu) + Model 2 (Roboflow YOLO Condition Grader).
    """
    # 1. Identifikasi Jenis Kartu (Model 1)
    ai_result = process_card_identification(img_bgr, top_k=top_k)
    top_match = ai_result.get("top_match")

    if not top_match:
        return {
            "status": "error",
            "message": "AI tidak dapat mengenali kartu dari foto yang diberikan.",
            "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
        }

    # 2. Deteksi Cacat Fisik (Model 2 YOLOv8 via Roboflow Cloud)
    defects = detect_defects_in_memory(clean_b64)

    # 3. Hitung Valuasi Harga Wajar Akhir & Diskon Kerusakan
    base_price_usd = float(top_match.get("effective_market_price") or 0.0)
    release_year = top_match.get("release_year")
    rarity = top_match.get("rarity", "")

    valuation = evaluate_card_valuation(
        base_price_usd=base_price_usd,
        release_year=release_year,
        rarity=rarity,
        defects=defects,
        usd_rate=DEFAULT_USD_TO_IDR
    )

    candidates = build_candidates_list(ai_result.get("candidates", []))

    return {
        "status": "success",
        "message": f"Berhasil menganalisis: {top_match.get('name', 'Unknown')}",
        "card_id": top_match.get("card_id"),
        "name": top_match.get("name"),
        "set_name": top_match.get("set_name"),
        "set_id": top_match.get("set_id"),
        "set_series": top_match.get("set_series"),
        "release_year": int(release_year) if release_year else None,
        "rarity": rarity,
        "supertype": top_match.get("supertype"),
        "subtypes": top_match.get("subtypes"),
        "types": top_match.get("types"),
        "hp": float(top_match.get("hp")) if top_match.get("hp") else None,
        "confidence_percentage": top_match.get("confidence_percentage", 0.0),
        "confidence_label": top_match.get("confidence_label", "Uncertain"),
        "official_image_url": top_match.get("image_url_large"),
        "pricing": valuation["pricing"],
        "estimated_price": valuation["pricing"]["final_price_idr"],
        "card_condition": valuation["condition_report"]["condition_tier"],
        "condition_report": valuation["condition_report"],
        "candidates": candidates,
        "recommendation_signal": valuation["recommendation_signal"],
        "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
    }
