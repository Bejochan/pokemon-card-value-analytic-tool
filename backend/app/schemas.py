"""
backend/app/schemas.py
======================
Pydantic Data Schemas untuk Request & Response API Regokemon.
Menyediakan validasi tipe data otomatis dan dokumentasi interaktif di /docs (Swagger UI).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =====================================================================
# 1. REQUEST SCHEMAS
# =====================================================================

class ImageDataRequest(BaseModel):
    """Payload penerimaan gambar dari Frontend (React)."""
    image: str = Field(
        ...,
        description="String Base64 gambar kartu (mendukung prefix 'data:image/...;base64,' maupun raw base64)."
    )
    expected_card_id: Optional[str] = Field(
        None,
        description="ID kartu acuan jika dalam mode validasi atau benchmarking (opsional)."
    )


# =====================================================================
# 2. COMPONENT SCHEMAS
# =====================================================================

class PricingDetails(BaseModel):
    """Rincian valuasi harga pasar kartu dalam USD dan Rupiah (IDR)."""
    base_price_usd: float = Field(0.0, description="Harga dasar pasar (effective_market_price) dalam USD.")
    base_price_idr: int = Field(0, description="Estimasi harga dasar dalam Rupiah (kurs Rp15.500).")
    condition_multiplier: float = Field(1.0, description="Faktor pengali kondisi fisik (F_condition, misal: 1.0, 0.85, 0.65).")
    condition_discount_pct: float = Field(0.0, description="Persentase potongan harga akibat cacat fisik (misal: 15.0%).")
    final_price_usd: float = Field(0.0, description="Harga pasar wajar akhir (P_final) dalam USD.")
    final_price_idr: int = Field(0, description="Harga pasar wajar akhir (P_final) dalam Rupiah.")
    currency_rate: int = Field(15500, description="Kurs acuan USD ke IDR.")


class DefectItem(BaseModel):
    """Detail satu cacat fisik yang terdeteksi oleh Model 2 YOLOv8."""
    label: str = Field(..., description="Jenis cacat fisik (scratched, edge_wear, crease, dll).")
    confidence: float = Field(..., description="Skor keyakinan deteksi cacat (0.0 - 1.0).")
    bbox: Optional[Dict[str, float]] = Field(None, description="Koordinat bounding box cacat {x, y, width, height}.")


class ConditionReport(BaseModel):
    """Laporan penilaian kondisi fisik kartu dari Model 2."""
    condition_tier: str = Field("Near Mint / Mint", description="Kategori kondisi (Mint, Lightly Played, Heavily Played, Damaged).")
    has_defects: bool = Field(False, description="Apakah terdeteksi cacat fisik pada kartu.")
    defect_count: int = Field(0, description="Jumlah total cacat fisik yang terdeteksi.")
    defects: List[DefectItem] = Field(default_factory=list, description="Daftar cacat fisik terperinci.")
    evaluation_status: str = Field("evaluated", description="Status evaluasi: evaluated, bypassed_oncam, atau error.")


class CardCandidate(BaseModel):
    """Informasi kartu alternatif yang mendekati tebakan visual."""
    rank: int
    card_id: str
    name: str
    confidence_percentage: float
    raw_similarity_score: float
    set_name: Optional[str] = None
    rarity: Optional[str] = None
    official_image_url: Optional[str] = None


# =====================================================================
# 3. RESPONSE SCHEMAS
# =====================================================================

class IdentifyResponse(BaseModel):
    """Respon cepat khusus pemindaian On-Cam (Model 1 CLIP saja)."""
    status: str
    message: str
    card_id: Optional[str] = None
    name: Optional[str] = None
    set_name: Optional[str] = None
    set_id: Optional[str] = None
    set_series: Optional[str] = None
    release_year: Optional[int] = None
    rarity: Optional[str] = None
    supertype: Optional[str] = None
    subtypes: Optional[str] = None
    types: Optional[str] = None
    hp: Optional[float] = None
    confidence_percentage: float = 0.0
    confidence_label: str = "Uncertain"
    official_image_url: Optional[str] = None
    pricing: Optional[PricingDetails] = None
    estimated_price: Optional[int] = Field(None, description="Backward-compatibility untuk frontend.")
    card_condition: Optional[str] = Field(None, description="Backward-compatibility untuk frontend.")
    candidates: List[CardCandidate] = Field(default_factory=list)
    execution_time_ms: float = 0.0


class AnalyzeResponse(BaseModel):
    """Respon komprehensif untuk Upload Foto (Model 1 + Model 2 YOLO Condition)."""
    status: str
    message: str
    card_id: Optional[str] = None
    name: Optional[str] = None
    set_name: Optional[str] = None
    set_id: Optional[str] = None
    set_series: Optional[str] = None
    release_year: Optional[int] = None
    rarity: Optional[str] = None
    supertype: Optional[str] = None
    subtypes: Optional[str] = None
    types: Optional[str] = None
    hp: Optional[float] = None
    confidence_percentage: float = 0.0
    confidence_label: str = "Uncertain"
    official_image_url: Optional[str] = None
    pricing: Optional[PricingDetails] = None
    estimated_price: Optional[int] = Field(None, description="Backward-compatibility untuk frontend.")
    card_condition: Optional[str] = Field(None, description="Backward-compatibility untuk frontend.")
    condition_report: Optional[ConditionReport] = None
    candidates: List[CardCandidate] = Field(default_factory=list)
    recommendation_signal: str = Field("HOLD", description="Sinyal transaksi: BUY, HOLD, atau SELL.")
    execution_time_ms: float = 0.0
