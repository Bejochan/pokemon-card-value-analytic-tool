"""
backend/app/cv_service.py
=========================
Layanan Computer Vision (CV Service) untuk Regokemon:
1. Memuat dan mengelola Model 1 (OpenAI CLIP ViT-B-32 + FAISS Index 20.617 kartu).
2. Menghubungkan Model 2 (Local YOLOv8 Condition Grader & Roboflow fallback) untuk deteksi cacat fisik depan & belakang.
3. Mendekode gambar Base64 / Bytes murni di memori RAM tanpa I/O file sampah di disk.
"""

import os
import sys
import base64
import requests
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

import threading

# Mencegah fragmentasi VRAM CUDA di PyTorch
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Pastikan terminal Windows tidak crash saat print karakter/emoji
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Inisialisasi awal PyTorch di Windows sebelum modul OpenCV/NumPy dimuat
try:
    import torch
except Exception:
    pass
    # Pastikan dependensi DLL PyTorch (c10.dll, libiomp5md.dll) dapat ditemukan di Windows
    try:
        torch_lib = os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib")
        if os.path.exists(torch_lib):
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(torch_lib)
            os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

from app.analytics_engine import evaluate_card_valuation, DEFAULT_USD_TO_IDR
from app.currency_service import get_usd_to_idr_rate, convert_usd_to_idr


# =====================================================================
# INISIALISASI MODEL VISION SINGLETON (LAZY LOADING DENGAN THREAD LOCK)
# =====================================================================

_card_identifier = None
_defect_model = None
_identifier_lock = threading.Lock()
_defect_lock = threading.Lock()

def get_card_identifier():
    """
    Mengambil instance CardIdentifier secara Lazy (hanya dimuat saat pertama kali dibutuhkan).
    Menggunakan thread lock (double-checked locking) untuk mencegah race condition
    ketika banyak request masuk bersamaan, menghindari pemuatan model CLIP ganda
    yang dapat memicu CUDA Out of Memory di GPU 4GB.
    """
    global _card_identifier
    if _card_identifier is None:
        with _identifier_lock:
            if _card_identifier is None:
                try:
                    if "torch" in sys.modules:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    print("[INFO] [CV Service] Permintaan scan diterima. Memuat Model 1 (CLIP + FAISS)...")
                    from models.card_identifier import CardIdentifier
                    _card_identifier = CardIdentifier()
                    print("[OK] [CV Service] Model 1 berhasil dimuat dan siap digunakan!")
                except Exception as e:
                    print(f"[ERROR] [CV Service] Gagal memuat Model 1 AI Engine: {e}")
                    if "torch" in sys.modules:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    return None
    return _card_identifier


def get_defect_model():
    """
    Mengambil instance model YOLOv8 Condition Grader lokal secara Lazy dengan thread lock.
    Menggunakan model 'best-model-v5-card-condition.pt' yang sudah dilatih secara lokal.
    """
    global _defect_model
    if _defect_model is None:
        with _defect_lock:
            if _defect_model is None:
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    backend_dir = os.path.dirname(current_dir)
                    model_path = os.path.join(backend_dir, "models", "best-model-v5-card-condition.pt")
                    if os.path.exists(model_path):
                        from ultralytics import YOLO
                        _defect_model = YOLO(model_path)
                        print(f"[OK] [CV Service] Model 2 YOLOv8 Condition Grader lokal berhasil dimuat dari {model_path}")
                    else:
                        print(f"[WARN] [CV Service] File model lokal tidak ditemukan di: {model_path}")
                except Exception as e:
                    print(f"[WARN] [CV Service] Gagal memuat Model 2 YOLO lokal: {e}")
                    return None
    return _defect_model


ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_CONFIDENCE = int(os.getenv("ROBOFLOW_CONFIDENCE", "80"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def get_live_price(card_id: str, default_price: float) -> float:
    if not SUPABASE_URL or not SUPABASE_KEY or not card_id:
        return default_price
    try:
        url = f"{SUPABASE_URL}/rest/v1/card_prices?select=effective_market_price&card_id=eq.{card_id}"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0 and data[0].get("effective_market_price") is not None:
                return float(data[0]["effective_market_price"])
    except Exception as e:
        print(f"[CV Service] Gagal fetch harga live dari Supabase: {e}")
    return default_price


# =====================================================================
# FUNGSI HELPER DECODING GAMBAR DI RAM
# =====================================================================

def decode_base64_to_cv2(image_b64: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Mendekode string Base64 langsung menjadi gambar OpenCV BGR (np.ndarray) di RAM.
    Mengembalikan (img_bgr, clean_base64_string).
    """
    try:
        if not image_b64:
            return None, None
            
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
        if not image_bytes:
            return None, None
            
        img_arr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        clean_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return img_bgr, clean_b64
    except Exception as e:
        print(f"[CV Service] Gagal mendekode Bytes: {e}")
        return None, None


# =====================================================================
# DETEKSI CACAT FISIK KARTU (MODEL 2 YOLO LOKAL & ROBOFLOW FALLBACK)
# =====================================================================

def detect_defects_from_image(img_bgr: np.ndarray, conf_threshold: float = 0.15) -> List[Dict[str, Any]]:
    """
    Mendeteksi cacat fisik (Corner Wear, Edge Wear, Scratch) menggunakan Model 2 YOLO lokal.
    Mengabaikan bounding box kartu itu sendiri ('Card').
    """
    model = get_defect_model()
    if model is None or img_bgr is None:
        return []

    try:
        results = model.predict(img_bgr, conf=conf_threshold, verbose=False)
        result = results[0]
        defects = []
        for box in result.boxes:
            cls_name = result.names[int(box.cls[0])]
            if cls_name == "Card":
                continue  # 'Card' adalah deteksi kontur kartu, bukan cacat fisik

            cx, cy, w, h = box.xywh[0].tolist()
            conf = float(box.conf[0])
            defects.append({
                "label": cls_name,
                "confidence": round(conf, 2),
                "bbox": {
                    "x": round(cx, 1),
                    "y": round(cy, 1),
                    "width": round(w, 1),
                    "height": round(h, 1)
                }
            })
        return defects
    except Exception as e:
        print(f"[CV Service] Error inference local YOLO defect model: {e}")
        return []


def detect_defects_in_memory(clean_base64_data: str) -> List[Dict[str, Any]]:
    """
    Fallback: Mengirimkan payload Base64 ke endpoint Roboflow Cloud Inference via HTTP.
    """
    if not ROBOFLOW_API_KEY:
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
            timeout=2.0
        )
        if response.status_code != 200:
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


def detect_card_defects_dual_side(
    front_bgr: Optional[np.ndarray],
    back_bgr: Optional[np.ndarray] = None,
    front_b64: Optional[str] = None,
    back_b64: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Mendeteksi cacat fisik pada kedua sisi kartu (Tampak Depan & Tampak Belakang).
    Memprioritaskan local YOLOv8 model, lalu fallback ke Roboflow jika model lokal tidak aktif.
    """
    front_defects = []
    back_defects = []

    model = get_defect_model()
    if model is not None:
        if front_bgr is not None:
            front_defects = detect_defects_from_image(front_bgr)
        if back_bgr is not None:
            back_defects = detect_defects_from_image(back_bgr)
    else:
        # Fallback Roboflow Cloud
        if front_b64:
            front_defects = detect_defects_in_memory(front_b64)
        if back_b64:
            back_defects = detect_defects_in_memory(back_b64)

    return front_defects, back_defects


# =====================================================================
# FUNGSI SERVICE UTAMA
# =====================================================================

def process_card_identification(img_bgr: np.ndarray, top_k: int = 4) -> Dict[str, Any]:
    """
    Menjalankan Model 1 CLIP ViT-B-32 pada gambar OpenCV di memori RAM.
    Mengembalikan data kartu utama dan daftar kandidat alternatif.
    """
    identifier = get_card_identifier()
    
    if identifier is None:
        return {
            "status": "error",
            "message": "Layanan AI Scanner sedang offline atau mengalami kendala modul di server.",
            "top_match": None,
            "candidates": [],
            "execution_time_ms": 0.0
        }

    ai_result = identifier.identify_card(
        image_input=img_bgr,
        top_k=top_k,
        debug=False
    )
    return ai_result


def build_candidates_list(candidates_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Memformat daftar runner-up kandidat kartu untuk ditampilkan di UI."""
    candidates = []
    for c in candidates_raw[1:]:
        p_usd = None
        p_idr = None
        raw_price = c.get("effective_market_price")
        if raw_price is not None and str(raw_price).strip() != "":
            try:
                p_usd = float(raw_price)
                if not np.isnan(p_usd) and p_usd > 0:
                    p_idr = convert_usd_to_idr(p_usd)
                else:
                    p_usd = None
            except (ValueError, TypeError):
                p_usd = None
                p_idr = None

        candidates.append({
            "rank": c.get("rank", 0),
            "card_id": c.get("card_id", ""),
            "name": c.get("name", "Unknown"),
            "confidence_percentage": c.get("confidence_percentage", 0.0),
            "raw_similarity_score": c.get("raw_similarity_score", 0.0),
            "orb_verification_score": c.get("orb_verification_score"),
            "set_name": c.get("set_name"),
            "rarity": c.get("rarity"),
            "official_image_url": c.get("image_url_large"),
            "price_usd": p_usd,
            "price_idr": p_idr
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
            "message": ai_result.get("message") or "AI tidak dapat mengenali kartu dari foto yang diberikan.",
            "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
        }

    price_usd = float(top_match.get("effective_market_price") or 0.0)
    price_usd = get_live_price(top_match.get("card_id"), price_usd)
    current_rate = get_usd_to_idr_rate()
    price_idr = convert_usd_to_idr(price_usd)

    candidates = build_candidates_list(ai_result.get("candidates", []))

    return {
        "status": "success",
        "message": f"Berhasil mendeteksi: {top_match.get('name', 'Unknown')}",
        "card_id": top_match.get("card_id"),
        "name": top_match.get("name"),
        "number": str(top_match.get("number")) if top_match.get("number") is not None else None,
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
        "raw_similarity_score": top_match.get("raw_similarity_score"),
        "orb_verification_score": top_match.get("orb_verification_score"),
        "margin_to_runner_up": top_match.get("margin_to_runner_up"),
        "official_image_url": top_match.get("image_url_large"),
        "pricing": {
            "base_price_usd": price_usd,
            "base_price_idr": price_idr,
            "condition_multiplier": 1.0,
            "condition_discount_pct": 0.0,
            "final_price_usd": price_usd,
            "final_price_idr": price_idr,
            "currency_rate": current_rate
        },
        "estimated_price": price_idr,
        "card_condition": "Tidak Dievaluasi (Mode On-Cam)",
        "candidates": candidates,
        "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
    }


def run_analyze_flow(
    img_bgr: np.ndarray,
    clean_b64: str,
    back_bgr: Optional[np.ndarray] = None,
    back_b64: Optional[str] = None,
    card_id_override: Optional[str] = None,
    top_k: int = 4
) -> Dict[str, Any]:
    """
    Alur khusus UPLOAD FOTO STATIS:
    Menjalankan Model 1 (Identifikasi Kartu dari foto depan / card_id override) + 
    Model 2 (YOLO Condition Grader pada foto depan & belakang jika disediakan).
    """
    top_match = None
    ai_result = {}

    if card_id_override and card_id_override.strip():
        from app.analytics_engine import get_card_metadata
        meta = get_card_metadata(card_id_override.strip())
        top_match = {
            "card_id": meta["card_id"],
            "name": meta["name"],
            "set_name": meta.get("set_name", ""),
            "set_id": meta.get("set_id", ""),
            "set_series": meta.get("set_series", ""),
            "release_year": meta.get("release_year"),
            "rarity": meta.get("rarity", ""),
            "supertype": meta.get("supertype", ""),
            "subtypes": meta.get("subtypes", ""),
            "types": meta.get("types", ""),
            "hp": meta.get("hp"),
            "effective_market_price": meta.get("effective_market_price", 0.0),
            "confidence_percentage": 100.0,
            "confidence_label": "Manual / Known ID",
            "image_url_large": meta.get("image_large", None)
        }
    else:
        # 1. Identifikasi Jenis Kartu (Model 1 pada tampak depan via CLIP)
        ai_result = process_card_identification(img_bgr, top_k=top_k)
        top_match = ai_result.get("top_match")

    if not top_match:
        return {
            "status": "error",
            "message": ai_result.get("message") or "Model 1 (CLIP Index) sedang offline atau belum dibangun (card_embeddings.index tidak ditemukan). Silakan gunakan form 'card_id' atau gunakan endpoint spesifik '/upload/cards/{card_id}/condition'.",
            "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
        }

    # 2. Deteksi Cacat Fisik (Model 2 YOLOv8 Lokal atau Roboflow pada depan & belakang)
    front_defects, back_defects = detect_card_defects_dual_side(
        front_bgr=img_bgr,
        back_bgr=back_bgr,
        front_b64=clean_b64,
        back_b64=back_b64
    )
    defects = front_defects + back_defects

    # 3. Hitung Valuasi Harga Wajar Akhir & Diskon Kerusakan
    base_price_usd = float(top_match.get("effective_market_price") or 0.0)
    base_price_usd = get_live_price(top_match.get("card_id"), base_price_usd)
    release_year = top_match.get("release_year")
    rarity = top_match.get("rarity", "")

    valuation = evaluate_card_valuation(
        card_id=top_match.get("card_id"),
        base_price_usd=base_price_usd,
        release_year=release_year,
        rarity=rarity,
        supertype=top_match.get("supertype"),
        hp=top_match.get("hp"),
        defects=defects,
        usd_rate=get_usd_to_idr_rate()
    )

    valuation["condition_report"]["front_defects"] = front_defects
    valuation["condition_report"]["back_defects"] = back_defects

    candidates = build_candidates_list(ai_result.get("candidates", []))

    return {
        "status": "success",
        "message": f"Berhasil menganalisis: {top_match.get('name', 'Unknown')}",
        "card_id": top_match.get("card_id"),
        "name": top_match.get("name"),
        "number": str(top_match.get("number")) if top_match.get("number") is not None else None,
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
        "raw_similarity_score": top_match.get("raw_similarity_score"),
        "orb_verification_score": top_match.get("orb_verification_score"),
        "margin_to_runner_up": top_match.get("margin_to_runner_up"),
        "official_image_url": top_match.get("image_url_large"),
        "pricing": valuation["pricing"],
        "estimated_price": valuation["pricing"]["final_price_idr"],
        "card_condition": valuation["condition_report"]["condition_tier"],
        "condition_report": valuation["condition_report"],
        "market_analytics": valuation.get("market_analytics", {}),
        "candidates": candidates,
        "recommendation_signal": valuation["recommendation_signal"],
        "execution_time_ms": ai_result.get("execution_time_ms", 0.0)
    }
