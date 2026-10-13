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
"""

import os
import sys
import math
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
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

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.schemas import ImageDataRequest, IdentifyResponse, AnalyzeResponse
from app.cv_service import (
    decode_base64_to_cv2,
    decode_bytes_to_cv2,
    run_identify_flow,
    run_analyze_flow
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
async def analyze_card_base64(data: ImageDataRequest):
    """
    Endpoint analisis komprehensif untuk halaman Upload Foto.
    Menjalankan Model 1 (CLIP) + Model 2 (Roboflow YOLOv8 Condition Grader),
    menghitung persentase diskon kerusakan fisik, dan mengestimasi harga wajar akhir (P_final).
    """
    img_bgr, clean_b64 = decode_base64_to_cv2(data.image)
    if img_bgr is None or clean_b64 is None:
        raise HTTPException(
            status_code=400,
            detail="Format Base64 gambar tidak valid atau gambar rusak."
        )

    result = run_analyze_flow(img_bgr, clean_b64, top_k=4)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    # Menyediakan backward-compatibility field untuk UI ScannerDashboard.jsx yang sudah ada
    # scanResult.estimated_price & scanResult.official_image_url
    result["estimated_price"] = result["pricing"]["final_price_idr"]

    return result


@app.post("/upload/analyze", response_model=AnalyzeResponse)
async def analyze_card_file(file: UploadFile = File(...)):
    """Versi Multipart Form-Data untuk endpoint Full Analysis."""
    contents = await file.read()
    img_bgr, clean_b64 = decode_bytes_to_cv2(contents)
    if img_bgr is None or clean_b64 is None:
        raise HTTPException(status_code=400, detail="Berkas gambar tidak dapat dibaca.")

    result = run_analyze_flow(img_bgr, clean_b64, top_k=4)
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
    set_id: Optional[str] = None,
    sort_by: Optional[str] = "newest"
):
    """
    Endpoint fleksibel untuk Halaman Katalog:
    Mendukung pagination, pencarian nama kartu, filter supertype/rarity/set,
    serta pengurutan harga/nama.
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
        "?select=card_id,name,supertype,rarity,image_small,sets(set_id,name),card_prices(effective_market_price)",
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

    # Filter Set ID
    if set_id and set_id.strip() and set_id.lower() != "all":
        clean_set = set_id.strip()
        url_parts.append(f"&set_id=eq.{clean_set}")

    # Pengurutan
    if sort_by == "name_asc":
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
def get_sets(limit: int = 50):
    """
    Mengambil daftar Set Pokémon dari Supabase untuk dropdown filter katalog.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return []
    url = f"{supabase_url}/rest/v1/sets?select=set_id,name,series&limit={limit}&order=name.asc"
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
# 6. RUNNER LOKAL
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("\n[INFO] Menjalankan Server Regokemon API di http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)