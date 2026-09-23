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
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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
# 5. RUNNER LOKAL
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("\n[INFO] Menjalankan Server Regokemon API di http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)