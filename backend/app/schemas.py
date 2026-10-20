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
        description="String Base64 foto tampak depan kartu (mendukung prefix 'data:image/...;base64,' maupun raw base64)."
    )
    back_image: Optional[str] = Field(
        None,
        description="String Base64 foto tampak belakang kartu untuk evaluasi cacat fisik 2 sisi (opsional)."
    )
    expected_card_id: Optional[str] = Field(
        None,
        description="ID kartu acuan jika dalam mode validasi atau benchmarking (opsional)."
    )


class CardConditionRequest(BaseModel):
    """Payload penerimaan foto tampak depan & belakang kartu untuk Condition Grading."""
    front_image: Optional[str] = Field(
        None,
        description="String Base64 foto tampak depan kartu."
    )
    back_image: Optional[str] = Field(
        None,
        description="String Base64 foto tampak belakang kartu."
    )


# =====================================================================
# 2. COMPONENT SCHEMAS
# =====================================================================

class PricingDetails(BaseModel):
    """Rincian valuasi harga pasar kartu dalam USD dan Rupiah (IDR)."""
    base_price_usd: float = Field(0.0, description="Harga dasar pasar (effective_market_price) dalam USD.")
    base_price_idr: int = Field(0, description="Estimasi harga dasar dalam Rupiah (kurs acuan live).")
    condition_multiplier: float = Field(1.0, description="Faktor pengali kondisi fisik (F_condition, misal: 1.0, 0.85, 0.65).")
    condition_discount_pct: float = Field(0.0, description="Persentase potongan harga akibat cacat fisik (misal: 15.0%).")
    final_price_usd: float = Field(0.0, description="Harga pasar wajar akhir (P_final) dalam USD.")
    final_price_idr: int = Field(0, description="Harga pasar wajar akhir (P_final) dalam Rupiah.")
    currency_rate: float = Field(16500.0, description="Kurs acuan USD ke IDR real-time.")


class DefectItem(BaseModel):
    """Detail satu cacat fisik yang terdeteksi oleh Model 2 YOLOv8."""
    label: str = Field(..., description="Jenis cacat fisik (Corner Wear, Edge Wear, Scratch, dll).")
    confidence: float = Field(..., description="Skor keyakinan deteksi cacat (0.0 - 1.0).")
    bbox: Optional[Dict[str, float]] = Field(None, description="Koordinat bounding box cacat {x, y, width, height}.")


class ConditionReport(BaseModel):
    """Laporan penilaian kondisi fisik kartu dari Model 2."""
    condition_tier: str = Field("Near Mint / Mint", description="Kategori kondisi (Mint, Lightly Played, Heavily Played, Damaged).")
    has_defects: bool = Field(False, description="Apakah terdeteksi cacat fisik pada kartu.")
    defect_count: int = Field(0, description="Jumlah total cacat fisik yang terdeteksi.")
    front_defects: List[DefectItem] = Field(default_factory=list, description="Daftar cacat fisik pada tampak depan kartu.")
    back_defects: List[DefectItem] = Field(default_factory=list, description="Daftar cacat fisik pada tampak belakang kartu.")
    defects: List[DefectItem] = Field(default_factory=list, description="Daftar gabungan seluruh cacat fisik terperinci.")
    evaluation_status: str = Field("evaluated", description="Status evaluasi: evaluated, bypassed_oncam, atau error.")


class MarketAnalytics(BaseModel):
    """Analisis peramalan harga menggunakan model Machine Learning."""
    predicted_fair_value_usd: float = Field(0.0, description="Harga wajar yang diprediksi oleh Machine Learning dalam USD.")
    predicted_fair_value_idr: int = Field(0, description="Harga wajar prediksi dalam Rupiah.")
    mispricing_gap_pct: float = Field(0.0, description="Persentase selisih harga pasar aktual dengan harga wajar prediksi.")


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


class ForecastPoint(BaseModel):
    """Satu titik data prediksi harga pada hari tertentu."""
    day: int = Field(..., description="Hari ke-N dari sekarang (1-7).")
    date: str = Field(..., description="Tanggal prediksi (YYYY-MM-DD).")
    predicted_price_usd: float = Field(0.0, description="Harga prediksi dalam USD.")


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
    market_analytics: Optional[MarketAnalytics] = None
    candidates: List[CardCandidate] = Field(default_factory=list)
    recommendation_signal: str = Field("HOLD", description="Sinyal transaksi: BUY, HOLD, atau SELL.")
    execution_time_ms: float = 0.0


class ForecastResponse(BaseModel):
    """Respon forecast harga 7 hari beserta sinyal transaksi."""
    status: str = Field("success", description="Status respon: success atau error.")
    message: str = Field("", description="Pesan deskriptif hasil forecast.")
    card_id: str = Field(..., description="ID kartu yang di-forecast.")
    card_name: Optional[str] = Field(None, description="Nama kartu.")
    current_price_usd: float = Field(0.0, description="Harga pasar saat ini dalam USD.")
    current_price_idr: int = Field(0, description="Harga pasar saat ini dalam Rupiah.")
    forecast: List[ForecastPoint] = Field(default_factory=list, description="Daftar prediksi harga 7 hari ke depan.")
    predicted_price_day7_usd: float = Field(0.0, description="Harga prediksi pada hari ke-7 dalam USD.")
    predicted_price_day7_idr: int = Field(0, description="Harga prediksi pada hari ke-7 dalam Rupiah.")
    change_pct: float = Field(0.0, description="Persentase perubahan harga dari hari ini ke hari ke-7.")
    signal: str = Field("HOLD", description="Sinyal transaksi: BUY, HOLD, atau SELL.")
    mispricing_gap_pct: float = Field(0.0, description="Persentase selisih harga pasar aktual vs harga wajar prediksi.")
    ai_confidence_pct: float = Field(95.8, description="Persentase kepercayaan model ML.")
    currency_rate: float = Field(16500.0, description="Kurs acuan USD ke IDR.")


class CardConditionResponse(BaseModel):
    """Respon standalone penilaian kondisi fisik kartu (tampak depan & tampak belakang)."""
    status: str = Field("success", description="Status respon: success atau error.")
    message: str = Field("", description="Pesan deskriptif hasil penilaian.")
    card_id: str = Field(..., description="ID kartu yang dinilai.")
    card_name: Optional[str] = Field(None, description="Nama kartu.")
    condition_report: Optional[ConditionReport] = Field(None, description="Laporan kondisi fisik lengkap (depan + belakang).")
    pricing: Optional[PricingDetails] = Field(None, description="Rincian valuasi harga setelah penyesuaian kondisi.")
    condition_score_pct: float = Field(100.0, description="Skor kondisi kartu dalam persen (100% = Mint).")
