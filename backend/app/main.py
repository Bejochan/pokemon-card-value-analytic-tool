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
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests

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

# ---------------------------------------------------------------------
# 1. INISIALISASI FASTAPI APP & CORS
# ---------------------------------------------------------------------

app = FastAPI(
    title="Regokemon Analytics & Valuation API",
    description="Dual-Model Computer Vision & Fair Value Estimator for Pokémon TCG Marketplace.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# 2. HEALTHCHECK & INFO ENDPOINTS
# ---------------------------------------------------------------------

@app.get("/")
def read_root():
    return {
        "app": "Regokemon Analytics API",
        "version": "3.0.0",
        "status": "online",
        "docs_url": "/docs",
        "endpoints": {
            "oncam_identify": "POST /identify",
            "upload_analyze": "POST /analyze",
            "card_forecast": "GET /cards/{card_id}/forecast",
            "card_condition": "POST /cards/{card_id}/condition",
            "upload_card_condition": "POST /upload/cards/{card_id}/condition",
            "card_history": "GET /cards/{card_id}/history",
            "cards_catalog": "GET /cards",
            "sets_catalog": "GET /sets",
            "dashboard_trending": "GET /dashboard",
            "currency_status": "GET /currency",
            "healthcheck": "GET /health"
        }
    }


@app.get("/health")
def healthcheck():
    return {"status": "healthy", "service": "regokemon-backend"}


# ---------------------------------------------------------------------
# 3. ROUTE ON-CAM: IDENTIFIKASI CEPAT (MODEL 1 CLIP SAJA)
# ---------------------------------------------------------------------

@app.post("/identify", response_model=IdentifyResponse)
async def identify_card_base64(data: ImageDataRequest):
    """
    Endpoint pemindaian kamera langsung (On-Cam).
    Menerima Base64 gambar kartu, menjalankan Model 1 CLIP ViT-B-32 sub-milidetik,
    dan mengembalikan metadata spesifikasi kartu lengkap tanpa beban deteksi cacat fisik.
    """
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
async def identify_card_file(file: UploadFile = File(...)):
    """Versi Multipart Form-Data untuk endpoint On-Cam / Identify."""
    contents = await file.read()
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
def analyze_card_base64(data: ImageDataRequest):
    """
    Endpoint analisis komprehensif untuk halaman Upload Foto.
    Menjalankan Model 1 (CLIP) + Model 2 (YOLOv8 Condition Grader),
    menghitung persentase diskon kerusakan fisik, dan mengestimasi harga wajar akhir (P_final).
    Mendukung evaluasi satu sisi (image) atau dua sisi (image + back_image).
    """
    img_bgr, clean_b64 = decode_base64_to_cv2(data.image)
    if img_bgr is None or clean_b64 is None:
        raise HTTPException(
            status_code=400,
            detail="Format Base64 gambar tidak valid atau gambar rusak."
        )

    back_bgr, back_b64 = decode_base64_to_cv2(data.back_image) if data.back_image else (None, None)

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
    card_id: Optional[str] = Form(None, description="ID kartu (opsional, jika ingin menentukan ID kartu langsung tanpa Model 1 CLIP)")
):
    """
    Versi Multipart Form-Data untuk endpoint Full Analysis:
    Mendukung unggah foto tampak depan (front_file) dan tampak belakang (back_file).
    Model 1 CLIP otomatis mengenali jenis kartu dari foto depan (atau menggunakan card_id jika diisi),
    sedangkan Model 2 YOLOv8 memeriksa cacat fisik pada kedua sisi.
    """
    actual_front = front_file or file
    if not actual_front:
        raise HTTPException(status_code=400, detail="Wajib mengunggah foto kartu tampak depan.")

    front_bytes = actual_front.file.read()
    img_bgr, clean_b64 = decode_bytes_to_cv2(front_bytes)
    if img_bgr is None or clean_b64 is None:
        raise HTTPException(status_code=400, detail="Berkas gambar tampak depan tidak dapat dibaca.")

    back_bgr, back_b64 = None, None
    if back_file:
        back_bytes = back_file.file.read()
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
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Konfigurasi Supabase tidak ditemukan di .env")

    # Hitung batas limit & offset yang aman
    safe_limit = max(1, min(limit, 100))
    safe_page = max(1, page)
    offset = (safe_page - 1) * safe_limit

    # Susun query PostgREST Supabase
    url_parts = [
        f"{supabase_url}/rest/v1/cards",
        "?select=card_id,name,supertype,rarity,image_small,sets(set_id,name,release_date),card_prices(effective_market_price)",
        f"&limit={safe_limit}",
        f"&offset={offset}"
    ]

    # Filter Search Nama Kartu
    if search and search.strip():
        clean_search = search.strip()
        url_parts.append(f"&name=ilike.*{clean_search}*")

    # Filter Supertype (misal: Pokémon, Trainer, Energy)
    if supertype and supertype.strip() and supertype.lower() != "all":
        clean_super = supertype.strip()
        url_parts.append(f"&supertype=ilike.*{clean_super}*")

    # Filter Rarity
    if rarity and rarity.strip() and rarity.lower() != "all":
        clean_rarity = rarity.strip()
        url_parts.append(f"&rarity=ilike.*{clean_rarity}*")

    # Filter Holo
    if holo and holo.strip() and holo.lower() != "all":
        if holo.lower() == "holo":
            url_parts.append("&rarity=ilike.*Holo*")
        elif holo.lower() == "non_holo":
            url_parts.append("&rarity=not.ilike.*Holo*")

    # Filter Set ID
    if set_id and set_id.strip() and set_id.lower() != "all":
        clean_set = set_id.strip()
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
        res = requests.get(full_url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()

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
        print(f"[API] Error fetching cards from Supabase: {e}")
        raise HTTPException(status_code=500, detail="Gagal mengambil data dari database.")


@app.get("/sets")
def get_sets(limit: int = 150):
    """
    Mengambil daftar Set Pokémon dari Supabase untuk dropdown filter katalog,
    diurutkan secara kronologis dari set rilis paling baru ke lawas.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return []
    url = f"{supabase_url}/rest/v1/sets?select=set_id,name,series,release_date,release_year&limit={limit}&order=release_date.desc.nullslast"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.ok:
            return res.json()
    except Exception as e:
        print(f"[API] Error fetching sets: {e}")
    return []


@app.get("/cards/{card_id}/history")
def get_card_history(card_id: str):
    """Ambil histori harga untuk grafik"""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return []
    
    url = f"{supabase_url}/rest/v1/card_price_history?select=recorded_date,effective_market_price&card_id=eq.{card_id}&order=recorded_date.asc"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[API] Error fetching history: {e}")
        return []


# ---------------------------------------------------------------------
# 6. ROUTE MARKET ANALYTICS: FORECAST MODEL & CARD CONDITION MODEL
# ---------------------------------------------------------------------

@app.get("/cards/{card_id}/forecast", response_model=ForecastResponse)
def get_card_forecast(card_id: str):
    """
    Endpoint Peramalan Harga 7 Hari & Sinyal Transaksi (Forecast Model).
    Menghasilkan multi-step recursive price forecasting untuk 7 hari ke depan
    beserta rekomendasi sinyal trading: BUY, HOLD, atau SELL.
    """
    try:
        result = forecast_7_days(card_id)
        return result
    except Exception as e:
        print(f"[API] Error forecasting card {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal melakukan forecasting: {str(e)}")


@app.post("/cards/{card_id}/condition", response_model=CardConditionResponse)
def evaluate_card_condition_base64(card_id: str, data: CardConditionRequest):
    """
    Endpoint Penilaian Kondisi Fisik Kartu (Card Condition Model via Base64).
    Mendukung upload foto tampak depan (front_image) dan tampak belakang (back_image).
    Mendeteksi cacat fisik (scratches, corner wear, edge wear) di kedua sisi kartu,
    serta menghitung Condition Score (0-100%) dan penyesuaian harga pasar wajar.
    """
    front_raw = data.front_image
    back_raw = data.back_image

    if not front_raw and not back_raw:
        raise HTTPException(
            status_code=400,
            detail="Wajib menyertakan minimal satu foto kartu (front_image dan/atau back_image)."
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
    back_file: Optional[UploadFile] = File(None, description="Foto kartu tampak belakang (Opsional / Dianjurkan)")
):
    """
    Versi Multipart Form-Data untuk endpoint Card Condition Model.
    Mendukung unggah berkas foto tampak depan (front_file) dan tampak belakang (back_file).
    """
    if not front_file and not back_file:
        raise HTTPException(
            status_code=400,
            detail="Wajib mengunggah minimal satu berkas foto kartu (front_file dan/atau back_file)."
        )

    front_bgr, front_b64 = None, None
    back_bgr, back_b64 = None, None

    if front_file:
        front_bytes = front_file.file.read()
        front_bgr, front_b64 = decode_bytes_to_cv2(front_bytes)

    if back_file:
        back_bytes = back_file.file.read()
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
    """Ambil data trending/top cards untuk dashboard"""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return {"trending": []}
    
    # Ambil 4 kartu dengan limit
    url = f"{supabase_url}/rest/v1/cards?select=card_id,name,rarity,image_small,sets(set_id),card_prices(effective_market_price)&limit=4"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
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
                "flagIcon": "🇺🇸"
            })
            
        return {"trending": trendingCards}
    except Exception as e:
        print(f"[API] Error fetching dashboard: {e}")
        return {"trending": []}


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