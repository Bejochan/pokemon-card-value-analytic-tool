"""
backend/app/main.py
===================
Entrypoint Server REST API Regokemon (FastAPI).
Menyediakan antarmuka routing modular untuk integrasi Frontend React:
- GET  /           : Informasi status API
- GET  /health     : Healthcheck endpoint untuk Docker & Load Balancer
- POST /identify   : Khusus On-Cam / Scanner Cepat (Model 1 CLIP saja)
- POST /analyze    : Khusus Upload Foto Statis (Model 1 + Model 2 YOLO Condition Grader)
- POST /upload/identify : Upload file gambar langsung untuk On-Cam
- POST /upload/analyze  : Upload file gambar langsung untuk Full Analysis
- GET  /cards/{card_id}/forecast : Peramalan harga 7 hari & sinyal transaksi (BUY/HOLD/SELL)
- POST /cards/{card_id}/condition : Evaluasi kondisi fisik kartu tampak depan & belakang (Base64)
- POST /upload/cards/{card_id}/condition : Evaluasi kondisi fisik kartu tampak depan & belakang (File Upload)
- GET  /cards/{card_id}/history  : Riwayat harga kartu untuk visualisasi grafik
- GET  /cards      : Katalog dataset kartu (search, filter, pagination)
- GET  /sets       : Daftar set kartu Pokémon
- GET  /dashboard  : Data kartu trending untuk halaman Dashboard
- GET  /currency   : Informasi kurs live USD ke IDR
"""

import os
import sys
import math
import urllib.parse
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests

# Mencegah fragmentasi VRAM CUDA di PyTorch (terutama GPU 4GB)
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Pastikan terminal Windows tidak crash saat print karakter/emoji
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
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

# Inisialisasi awal PyTorch di Windows sebelum modul OpenCV/NumPy dimuat
try:
    import torch
except Exception:
    pass

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.schemas import (
    ImageDataRequest,
    CardConditionRequest,
    IdentifyResponse,
    AnalyzeResponse,
    ForecastResponse,
    CardConditionResponse
)
from app.cv_service import (
    decode_base64_to_cv2,
    decode_bytes_to_cv2,
    detect_defects_in_memory,
    detect_card_defects_dual_side,
    run_identify_flow,
    run_analyze_flow
)
from app.analytics_engine import (
    forecast_7_days,
    evaluate_card_condition_standalone
)
from app.currency_service import (
    get_usd_to_idr_rate,
    convert_usd_to_idr,
    get_currency_status
)
from app.offline_service import (
    get_offline_cards,
    get_offline_sets,
    get_offline_card_history,
    get_offline_trending_cards,
    get_offline_dashboard_analytics
)

# ---------------------------------------------------------------------
# 1. INISIALISASI FASTAPI APP, CORS, & KEAMANAN
# ---------------------------------------------------------------------

app = FastAPI(
    title="Regokemon Analytics & Valuation API",
    description="Triple-Engine AI (Vision & Time-Series) & Fair Value Estimator for Pokémon TCG Marketplace.",
    version="3.1.0"
)

# Mencegah remote network ping ke HuggingFace Hub jika bobot model sudah ada di local cache
if "HF_HUB_OFFLINE" not in os.environ:
    os.environ["HF_HUB_OFFLINE"] = "1"
if "TRANSFORMERS_OFFLINE" not in os.environ:
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Konfigurasi CORS Terbatas & Aman (Whitelist + Vercel Deployment)
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if raw_origins.strip():
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# KONSTANTA KEAMANAN & RATE LIMITER (SLIDING WINDOW)
# ---------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # Maksimum 15 MB untuk upload berkas
MAX_BASE64_CHARS = 22 * 1024 * 1024     # Maksimum ~15 MB representasi Base64

import time
import threading
from collections import defaultdict

_rate_limit_lock = threading.Lock()
_ip_request_timestamps = defaultdict(list)
AI_RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_AI_PER_MINUTE", "60"))


def check_ai_rate_limit(request: Request = None):
    """
    Memeriksa laju permintaan (rate limiting) per client IP khusus untuk endpoint inferensi AI berat.
    Mencegah pemborosan VRAM/CPU dari serangan spam request menggunakan in-memory sliding window.
    Jika request is None (pemanggilan langsung via fungsi Python/pengujian), rate limit dilewati secara aman.
    """
    if request is None:
        return
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    window_seconds = 60.0

    with _rate_limit_lock:
        timestamps = _ip_request_timestamps[client_ip]
        # Evict timestamp yang sudah melewati jendela 60 detik
        valid_timestamps = [t for t in timestamps if now - t < window_seconds]

        if len(valid_timestamps) >= AI_RATE_LIMIT_PER_MINUTE:
            _ip_request_timestamps[client_ip] = valid_timestamps
            retry_after = int(window_seconds - (now - valid_timestamps[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Terlalu banyak permintaan inferensi AI. Kuota maksimum: {AI_RATE_LIMIT_PER_MINUTE} req/menit per IP. Coba lagi dalam {retry_after} detik.",
                headers={"Retry-After": str(max(1, retry_after))}
            )

        valid_timestamps.append(now)
        _ip_request_timestamps[client_ip] = valid_timestamps


def read_upload_file_safely(file: UploadFile, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """Membaca berkas unggahan secara aman dan membatasi konsumsi memori jika ukuran melebihi batas."""
    contents = file.file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran berkas '{file.filename}' melebihi batas maksimum {max_bytes // (1024 * 1024)} MB."
        )
    return contents


@app.on_event("startup")
def prewarm_models_background():
    """Memanaskan (pre-warm) Model 1 (CLIP), Model 2 (YOLOv8), dan Model 3 (Chronos-Bolt) secara asinkron
    di latar belakang saat server pertama kali dinyalakan. Ini memastikan saat user melakukan upload manual pertama kali,
    model sudah siap di VRAM/RAM dan respons inferensi langsung berjalan instan (~1 detik) tanpa jeda cold-start."""
    import threading

    def _warmup_task():
        try:
            print("[INFO] [Startup Warmup] Memanaskan Model AI (CLIP + FAISS + YOLO + Chronos) di latar belakang...")
            from app.cv_service import get_card_identifier, get_defect_model
            from models.chronos_forecaster import get_chronos_pipeline
            get_card_identifier()
            get_defect_model()
            get_chronos_pipeline()
            print("[OK] [Startup Warmup] Seluruh engine AI (CLIP + YOLO + Chronos) siap melayani inferensi tanpa jeda!")
        except Exception as e:
            print(f"[WARN] [Startup Warmup] Warmup non-blocking notice: {e}")

    threading.Thread(target=_warmup_task, daemon=True).start()


# ---------------------------------------------------------------------
# 2. HEALTHCHECK & INFO ENDPOINTS
# ---------------------------------------------------------------------

@app.get("/")
def read_root():
    return {
        "app": "Regokemon Analytics API",
        "version": "3.1.0",
        "status": "online",
        "docs_url": "/docs",
        "endpoints": {
            "root_info": "GET /",
            "healthcheck": "GET /health",
            "oncam_identify": "POST /identify",
            "upload_identify": "POST /upload/identify",
            "full_analyze": "POST /analyze",
            "upload_analyze": "POST /upload/analyze",
            "cards_catalog": "GET /cards",
            "sets_catalog": "GET /sets",
            "card_history": "GET /cards/{card_id}/history",
            "card_forecast": "GET /cards/{card_id}/forecast",
            "card_condition": "POST /cards/{card_id}/condition",
            "upload_card_condition": "POST /upload/cards/{card_id}/condition",
            "dashboard_trending": "GET /dashboard",
            "currency_status": "GET /currency"
        }
    }


@app.get("/health")
def healthcheck():
    import app.cv_service as cv
    import models.chronos_forecaster as cf
    return {
        "status": "healthy",
        "app": "Regokemon Analytics API",
        "version": "3.1.0",
        "models": {
            "model_1_clip_faiss": cv._card_identifier is not None,
            "model_2_yolo_grader": cv._defect_model is not None,
            "model_3_chronos_bolt": cf._chronos_pipeline is not None
        },
        "dataset": {
            "master_cards_count": 20617,
            "total_sets_count": 172
        },
        "currency_rate_idr": get_usd_to_idr_rate()
    }


# ---------------------------------------------------------------------
# 3. ROUTE ON-CAM: IDENTIFIKASI CEPAT (MODEL 1 CLIP SAJA)
# ---------------------------------------------------------------------

@app.post("/identify", response_model=IdentifyResponse)
def identify_card_base64(data: ImageDataRequest, request: Request = None):
    """
    Endpoint pemindaian kamera langsung (On-Cam).
    Menerima Base64 gambar kartu, menjalankan Model 1 CLIP ViT-B-32 sub-milidetik,
    dan mengembalikan metadata spesifikasi kartu lengkap tanpa beban deteksi cacat fisik.
    Dieksekusi dalam threadpool FastAPI agar tidak memblokir event loop.
    Dilindungi dengan rate limiter dan pembatasan ukuran payload.
    """
    check_ai_rate_limit(request)
    if len(data.image) > MAX_BASE64_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran payload gambar Base64 melebihi batas maksimum {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    img_bgr, _ = decode_base64_to_cv2(data.image)
    if img_bgr is None:
        raise HTTPException(
            status_code=400,
            detail="Format Base64 gambar tidak valid atau gambar rusak."
        )

    result = run_identify_flow(img_bgr, top_k=4)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@app.post("/upload/identify", response_model=IdentifyResponse)
def identify_card_file(file: UploadFile = File(...), request: Request = None):
    """Versi Multipart Form-Data untuk endpoint On-Cam / Identify dengan proteksi payload maksimum."""
    check_ai_rate_limit(request)
    contents = read_upload_file_safely(file)
    img_bgr, _ = decode_bytes_to_cv2(contents)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Berkas gambar tidak dapat dibaca.")

    result = run_identify_flow(img_bgr, top_k=4)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    return result


# ---------------------------------------------------------------------
# 4. ROUTE UPLOAD: FULL ANALYSIS (MODEL 1 CLIP + MODEL 2 YOLO DEFECTS)
# ---------------------------------------------------------------------

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_card_base64(data: ImageDataRequest, request: Request = None):
    """
    Endpoint analisis komprehensif untuk halaman Upload Foto.
    Menjalankan Model 1 (CLIP) + Model 2 (YOLOv8 Condition Grader),
    menghitung persentase diskon kerusakan fisik, dan mengestimasi harga wajar akhir (P_final).
    Mendukung evaluasi satu sisi (image) atau dua sisi (image + back_image).
    Dilindungi dengan rate limiter dan pembatasan ukuran payload.
    """
    check_ai_rate_limit(request)
    if len(data.image) > MAX_BASE64_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran payload gambar Base64 melebihi batas maksimum {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )
    if data.back_image and len(data.back_image) > MAX_BASE64_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran payload gambar belakang Base64 melebihi batas maksimum {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    img_bgr, clean_b64 = decode_base64_to_cv2(data.image)
    if img_bgr is None or clean_b64 is None:
        raise HTTPException(
            status_code=400,
            detail="Format Base64 gambar tidak valid atau gambar rusak."
        )

    back_bgr, back_b64 = None, None
    if data.back_image:
        back_bgr, back_b64 = decode_base64_to_cv2(data.back_image)
        if back_bgr is None or back_b64 is None:
            raise HTTPException(
                status_code=400,
                detail="Format Base64 gambar tampak belakang tidak valid atau gambar rusak."
            )

    result = run_analyze_flow(
        img_bgr,
        clean_b64,
        back_bgr=back_bgr,
        back_b64=back_b64,
        card_id_override=data.expected_card_id,
        top_k=4
    )
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    # Menyediakan backward-compatibility field untuk UI ScannerDashboard.jsx yang sudah ada
    result["estimated_price"] = result["pricing"]["final_price_idr"]

    return result


@app.post("/upload/analyze", response_model=AnalyzeResponse)
def analyze_card_file(
    front_file: Optional[UploadFile] = File(None, description="Foto tampak depan kartu (Model 1 Identifier & Cacat Depan)"),
    back_file: Optional[UploadFile] = File(None, description="Foto tampak belakang kartu (Cacat Belakang, opsional)"),
    file: Optional[UploadFile] = File(None, description="Fallback berkas tunggal untuk upload foto depan"),
    card_id: Optional[str] = Form(None, description="ID kartu (opsional, jika ingin menentukan ID kartu langsung tanpa Model 1 CLIP)"),
    request: Request = None
):
    """
    Versi Multipart Form-Data untuk endpoint Full Analysis:
    Mendukung unggah foto tampak depan (front_file) dan tampak belakang (back_file).
    Model 1 CLIP otomatis mengenali jenis kartu dari foto depan (atau menggunakan card_id jika diisi),
    sedangkan Model 2 YOLOv8 memeriksa cacat fisik pada kedua sisi.
    Dilindungi dengan rate limiter dan pembatasan ukuran berkas 15 MB.
    """
    check_ai_rate_limit(request)
    actual_front = front_file or file
    if not actual_front:
        raise HTTPException(status_code=400, detail="Wajib mengunggah foto kartu tampak depan.")

    front_bytes = read_upload_file_safely(actual_front)
    img_bgr, clean_b64 = decode_bytes_to_cv2(front_bytes)
    if img_bgr is None or clean_b64 is None:
        raise HTTPException(status_code=400, detail="Berkas gambar tampak depan tidak dapat dibaca.")

    back_bgr, back_b64 = None, None
    if back_file:
        back_bytes = read_upload_file_safely(back_file)
        back_bgr, back_b64 = decode_bytes_to_cv2(back_bytes)

    result = run_analyze_flow(
        img_bgr,
        clean_b64,
        back_bgr=back_bgr,
        back_b64=back_b64,
        card_id_override=card_id,
        top_k=4
    )
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    result["estimated_price"] = result["pricing"]["final_price_idr"]

    return result


# ---------------------------------------------------------------------
# 5. ROUTE CATALOG: MENAMPILKAN DATASET KARTU (SEARCH, FILTER & PAGINATION)
# ---------------------------------------------------------------------

@app.get("/cards")
def get_cards(
    limit: int = 20,
    page: int = 1,
    search: Optional[str] = None,
    supertype: Optional[str] = None,
    rarity: Optional[str] = None,
    holo: Optional[str] = None,
    set_id: Optional[str] = None,
    sort_by: Optional[str] = "newest"
):
    """
    Endpoint fleksibel untuk Halaman Katalog:
    Mendukung pagination, pencarian nama kartu, filter supertype/rarity/holo/set,
    serta pengurutan harga/nama/rilis.
    """
    # Hitung batas limit & offset yang aman
    safe_limit = max(1, min(limit, 100))
    safe_page = max(1, page)
    offset = (safe_page - 1) * safe_limit

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        print("[API Offline] Supabase tidak dikonfigurasi. Menggunakan dataset CSV offline...")
        return get_offline_cards(
            limit=safe_limit,
            page=safe_page,
            search=search,
            supertype=supertype,
            rarity=rarity,
            holo=holo,
            set_id=set_id,
            sort_by=sort_by
        )

    # Susun query PostgREST Supabase
    url_parts = [
        f"{supabase_url}/rest/v1/cards",
        "?select=card_id,name,supertype,rarity,image_small,sets(set_id,name,release_date),card_prices(effective_market_price)",
        f"&limit={safe_limit}",
        f"&offset={offset}"
    ]

    # Filter Search Nama Kartu
    if search and search.strip():
        clean_search = urllib.parse.quote(search.strip(), safe="")
        url_parts.append(f"&name=ilike.*{clean_search}*")

    # Filter Supertype (misal: Pokémon, Trainer, Energy)
    if supertype and supertype.strip() and supertype.lower() != "all":
        clean_super = urllib.parse.quote(supertype.strip(), safe="")
        url_parts.append(f"&supertype=ilike.*{clean_super}*")

    # Filter Rarity
    if rarity and rarity.strip() and rarity.lower() != "all":
        r = rarity.strip()
        rl = r.lower()
        if rl == "common":
            url_parts.append("&rarity=eq.Common")
        elif rl == "rare":
            url_parts.append("&rarity=eq.Rare")
        else:
            clean_rarity = urllib.parse.quote(r, safe="")
            url_parts.append(f"&rarity=ilike.*{clean_rarity}*")

    # Filter Holo
    if holo and holo.strip() and holo.lower() != "all":
        if holo.lower() == "holo":
            url_parts.append("&rarity=ilike.*Holo*")
        elif holo.lower() == "non_holo":
            url_parts.append("&rarity=not.ilike.*Holo*")

    # Filter Set ID
    if set_id and set_id.strip() and set_id.lower() != "all":
        clean_set = urllib.parse.quote(set_id.strip(), safe="")
        url_parts.append(f"&set_id=eq.{clean_set}")

    # Pengurutan Kronologis Rilis & Harga
    if sort_by in ("newest", "release_desc"):
        url_parts.append("&order=sets(release_date).desc.nullslast,name.asc")
    elif sort_by in ("oldest", "release_asc"):
        url_parts.append("&order=sets(release_date).asc.nullslast,name.asc")
    elif sort_by == "price_desc":
        url_parts.append("&order=card_prices(effective_market_price).desc.nullslast,name.asc")
    elif sort_by == "price_asc":
        url_parts.append("&order=card_prices(effective_market_price).asc.nullslast,name.asc")
    elif sort_by == "name_asc":
        url_parts.append("&order=name.asc")
    elif sort_by == "name_desc":
        url_parts.append("&order=name.desc")
    elif sort_by == "hp_desc":
        url_parts.append("&order=hp.desc.nullslast")

    full_url = "".join(url_parts)

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Prefer": "count=exact"
    }

    try:
        res = requests.get(full_url, headers=headers, timeout=4)
        res.raise_for_status()
        data = res.json()
        
        # Jika data kosong tapi ada query search, tetap return data kosong dari Supabase
        # Namun jika respons bukan list, raise untuk fallback
        if not isinstance(data, list):
            raise ValueError("Respons Supabase tidak valid")

        # Baca total count dari header content-range (contoh: 0-19/209)
        content_range = res.headers.get("content-range", "")
        total_count = len(data)
        if "/" in content_range:
            total_part = content_range.split("/")[-1]
            if total_part.isdigit():
                total_count = int(total_part)
        
        # Mapping response ke struktur yang diharapkan frontend
        formatted_data = []
        for item in data:
            price_val = 0.0
            if isinstance(item.get("card_prices"), dict):
                price_val = item["card_prices"].get("effective_market_price") or 0.0
            elif isinstance(item.get("card_prices"), list) and len(item["card_prices"]) > 0:
                price_val = item["card_prices"][0].get("effective_market_price") or 0.0
                
            set_info = "unknown"
            if isinstance(item.get("sets"), dict):
                set_info = item["sets"].get("set_id") or "unknown"
            elif isinstance(item.get("sets"), list) and len(item["sets"]) > 0:
                set_info = item["sets"][0].get("set_id") or "unknown"
                
            rarity_str = item.get("rarity") or "Common"
            words = rarity_str.split()
            rarity_icon = "".join([w[0].upper() for w in words]) if words else "C"
            if len(rarity_icon) > 2:
                rarity_icon = rarity_icon[:2]
                
            # Penanganan kartu tanpa data harga pasar (misal set promo/baru seperti me55)
            if price_val and price_val > 0:
                price_usd_str = f"$ {price_val:.2f}"
                price_idr_val = convert_usd_to_idr(price_val)
                price_idr_str = f"Rp {price_idr_val:,}".replace(",", ".")
                is_unlisted = False
            else:
                price_usd_str = "Unlisted"
                price_idr_str = "Belum Ada Data"
                is_unlisted = True

            formatted_data.append({
                "id": item.get("card_id"),
                "name": item.get("name"),
                "supertype": item.get("supertype") or "Pokémon",
                "price": price_usd_str,
                "price_usd": price_usd_str,
                "price_idr": price_idr_str,
                "price_num": price_val if price_val else 0.0,
                "is_unlisted": is_unlisted,
                "rarityText": rarity_str,
                "rarityIcon": rarity_icon,
                "set": set_info,
                "image": item.get("image_small") or "/card-result.png"
            })
            
        # Sorting berbasis harga (jika dipilih)
        if sort_by == "price_desc":
            formatted_data.sort(key=lambda x: x["price_num"], reverse=True)
        elif sort_by == "price_asc":
            formatted_data.sort(key=lambda x: x["price_num"], reverse=False)

        total_pages = math.ceil(total_count / safe_limit) if safe_limit > 0 else 1

        return {
            "total": total_count,
            "page": safe_page,
            "limit": safe_limit,
            "total_pages": total_pages,
            "currency_rate": get_usd_to_idr_rate(),
            "cards": formatted_data
        }
    except Exception as e:
        print(f"[API Fallback] Supabase cards tidak dapat dijangkau ({e}). Mengalihkan ke CSV offline...")
        return get_offline_cards(
            limit=safe_limit,
            page=safe_page,
            search=search,
            supertype=supertype,
            rarity=rarity,
            holo=holo,
            set_id=set_id,
            sort_by=sort_by
        )


@app.get("/sets")
def get_sets(limit: int = 250):
    """
    Mengambil daftar Set Pokémon dari Supabase untuk dropdown filter katalog,
    diurutkan secara kronologis dari set rilis paling baru ke lawas.
    Otomatis beralih ke dataset CSV offline jika Supabase tidak dapat dijangkau.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return get_offline_sets(limit=limit)
    url = f"{supabase_url}/rest/v1/sets?select=set_id,name,series,release_date,release_year&limit={limit}&order=release_date.desc.nullslast"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.ok:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception as e:
        print(f"[API Fallback] Supabase sets tidak dapat dijangkau ({e}). Menggunakan CSV offline...")
    return get_offline_sets(limit=limit)


@app.get("/cards/{card_id}/history")
def get_card_history(card_id: str):
    """
    Ambil histori harga untuk grafik.
    Otomatis beralih ke dataset CSV offline jika Supabase tidak dapat dijangkau.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return get_offline_card_history(card_id)
    
    encoded_card_id = urllib.parse.quote(card_id.strip(), safe="")
    url = f"{supabase_url}/rest/v1/card_price_history?select=recorded_date,effective_market_price&card_id=eq.{encoded_card_id}&order=recorded_date.asc"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        res = requests.get(url, headers=headers, timeout=3)
        res.raise_for_status()
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            return data
    except Exception as e:
        print(f"[API Fallback] Supabase history tidak dapat dijangkau ({e}). Menggunakan CSV offline...")
    return get_offline_card_history(card_id)


# ---------------------------------------------------------------------
# 6. ROUTE MARKET ANALYTICS: FORECAST MODEL & CARD CONDITION MODEL
# ---------------------------------------------------------------------

@app.get("/cards/{card_id}/forecast", response_model=ForecastResponse)
def get_card_forecast(card_id: str, request: Request = None):
    """
    Endpoint Peramalan Harga 7 Hari & Sinyal Transaksi (Forecast Model).
    Menghasilkan multi-step recursive price forecasting untuk 7 hari ke depan
    beserta rekomendasi sinyal trading: BUY, HOLD, atau SELL.
    Dilindungi dengan rate limiter inferensi AI.
    """
    check_ai_rate_limit(request)
    try:
        result = forecast_7_days(card_id)
        return result
    except Exception as e:
        print(f"[API] Error forecasting card {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal melakukan forecasting: {str(e)}")


@app.post("/cards/{card_id}/condition", response_model=CardConditionResponse)
def evaluate_card_condition_base64(card_id: str, data: CardConditionRequest, request: Request = None):
    """
    Endpoint Penilaian Kondisi Fisik Kartu (Card Condition Model via Base64).
    Mendukung upload foto tampak depan (front_image) dan tampak belakang (back_image).
    Mendeteksi cacat fisik (scratches, corner wear, edge wear) di kedua sisi kartu,
    serta menghitung Condition Score (0-100%) dan penyesuaian harga pasar wajar.
    Dilindungi dengan rate limiter dan pembatasan ukuran payload.
    """
    check_ai_rate_limit(request)
    front_raw = data.front_image
    back_raw = data.back_image

    if not front_raw and not back_raw:
        raise HTTPException(
            status_code=400,
            detail="Wajib menyertakan minimal satu foto kartu (front_image dan/atau back_image)."
        )

    if front_raw and len(front_raw) > MAX_BASE64_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran payload front_image Base64 melebihi batas maksimum {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )
    if back_raw and len(back_raw) > MAX_BASE64_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran payload back_image Base64 melebihi batas maksimum {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    front_bgr, front_b64 = decode_base64_to_cv2(front_raw) if front_raw else (None, None)
    back_bgr, back_b64 = decode_base64_to_cv2(back_raw) if back_raw else (None, None)

    try:
        front_dets, back_dets = detect_card_defects_dual_side(
            front_bgr=front_bgr,
            back_bgr=back_bgr,
            front_b64=front_b64,
            back_b64=back_b64
        )
        result = evaluate_card_condition_standalone(
            card_id=card_id,
            front_defects=front_dets,
            back_defects=back_dets
        )
        return result
    except Exception as e:
        print(f"[API] Error evaluating card condition {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal mengevaluasi kondisi kartu: {str(e)}")


@app.post("/upload/cards/{card_id}/condition", response_model=CardConditionResponse)
def evaluate_card_condition_file(
    card_id: str,
    front_file: Optional[UploadFile] = File(None, description="Foto kartu tampak depan (Wajib / Utama)"),
    back_file: Optional[UploadFile] = File(None, description="Foto kartu tampak belakang (Opsional / Dianjurkan)"),
    request: Request = None
):
    """
    Versi Multipart Form-Data untuk endpoint Card Condition Model.
    Mendukung unggah berkas foto tampak depan (front_file) dan tampak belakang (back_file).
    Dilindungi dengan rate limiter dan pembatasan ukuran berkas 15 MB.
    """
    check_ai_rate_limit(request)
    if not front_file and not back_file:
        raise HTTPException(
            status_code=400,
            detail="Wajib mengunggah minimal satu berkas foto kartu (front_file dan/atau back_file)."
        )

    front_bgr, front_b64 = None, None
    back_bgr, back_b64 = None, None

    if front_file:
        front_bytes = read_upload_file_safely(front_file)
        front_bgr, front_b64 = decode_bytes_to_cv2(front_bytes)

    if back_file:
        back_bytes = read_upload_file_safely(back_file)
        back_bgr, back_b64 = decode_bytes_to_cv2(back_bytes)

    try:
        front_dets, back_dets = detect_card_defects_dual_side(
            front_bgr=front_bgr,
            back_bgr=back_bgr,
            front_b64=front_b64,
            back_b64=back_b64
        )
        result = evaluate_card_condition_standalone(
            card_id=card_id,
            front_defects=front_dets,
            back_defects=back_dets
        )
        return result
    except Exception as e:
        print(f"[API] Error evaluating card condition {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal mengevaluasi kondisi kartu: {str(e)}")


# ---------------------------------------------------------------------
# 7. ROUTE DASHBOARD & CURRENCY
# ---------------------------------------------------------------------

@app.get("/dashboard")
def get_dashboard_data():
    """
    Ambil data trending & analitika pasar komprehensif untuk halaman Dashboard:
    Character Leaderboard, Global Rarity Production, Top Packs Chase Cards,
    Era Trend Index, Feature Impact, dan Market Liquidity Index.
    """
    analytics = get_offline_dashboard_analytics()

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return analytics

    # Ambil 4 kartu trending live dari Supabase jika koneksi online tersedia
    url = f"{supabase_url}/rest/v1/cards?select=card_id,name,rarity,image_small,sets(set_id),card_prices(effective_market_price)&limit=4"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.ok:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                trendingCards = []
                for i, item in enumerate(data):
                    price_val = 0.0
                    if isinstance(item.get("card_prices"), dict):
                        price_val = item["card_prices"].get("effective_market_price") or 0.0
                    elif isinstance(item.get("card_prices"), list) and len(item["card_prices"]) > 0:
                        price_val = item["card_prices"][0].get("effective_market_price") or 0.0

                    set_id = "unknown"
                    if isinstance(item.get("sets"), dict):
                        set_id = item["sets"].get("set_id") or "unknown"
                    elif isinstance(item.get("sets"), list) and len(item["sets"]) > 0:
                        set_id = item["sets"][0].get("set_id") or "unknown"

                    trendingCards.append({
                        "id": i + 1,
                        "card_id": item.get("card_id"),
                        "name": item.get("name"),
                        "rarity": item.get("rarity") or "Common",
                        "holo": "Normal Print",
                        "price": f"$ {price_val:.2f}",
                        "image": item.get("image_small") or "/card-result.png",
                        "setIcon": f"/{set_id}-logo.png",
                        "flagIcon": "US"
                    })
                analytics_copy = dict(analytics)
                analytics_copy["trending"] = trendingCards
                analytics_copy["is_offline_fallback"] = False
                return analytics_copy
    except Exception as e:
        print(f"[API Fallback] Supabase dashboard tidak dapat dijangkau ({e}). Menggunakan analitika dataset lokal...")

    return analytics


@app.get("/currency")
def get_current_currency():
    """Mengembalikan informasi kurs live USD ke IDR yang digunakan oleh sistem."""
    return get_currency_status()


# ---------------------------------------------------------------------
# 8. RUNNER LOKAL
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("\n[INFO] Menjalankan Server Regokemon API di http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)