"""
backend/app/analytics_engine.py
===============================
Mesin Analitika & Valuasi Harga Wajar Kartu Pokémon (Regokemon Engine).
Mengimplementasikan formula valuasi resmi dari Laporan Akademik Bab II:

    P_final = P_base * M_variant * F_condition * F_market

Fungsi utama:
1. Menghitung pengali kondisi fisik (F_condition) berdasarkan deteksi cacat fisik Model 2.
2. Menghitung pengali kelangkaan & vintage (M_variant).
3. Mengonversi mata uang (USD -> IDR).
4. Menghasilkan sinyal transaksi wajar (BUY / HOLD / SELL).
"""

from typing import Dict, List, Any, Tuple


DEFAULT_USD_TO_IDR = 15500


def calculate_condition_factor(defects: List[Dict[str, Any]]) -> Tuple[float, str, float]:
    """
    Menghitung pengali kondisi fisik (F_condition), kategori tier, dan persentase diskon.
    
    Aturan Diskon Cacat Fisik:
    - Tidak ada cacat    : Multiplier = 1.00 (Diskon 0%)  -> "Mint / Near Mint"
    - Scratched (Lecet)  : Multiplier = 0.85 (Diskon 15%) -> "Lightly Played (LP)"
    - Edge Wear (Aus)    : Multiplier = 0.80 (Diskon 20%) -> "Moderately Played (MP)"
    - Bent / Crease      : Multiplier = 0.65 (Diskon 35%) -> "Heavily Played (HP)"
    - Akumulasi cacat berat: Dibatasi minimal 0.40        -> "Damaged"
    """
    if not defects:
        return 1.00, "Near Mint / Mint", 0.0

    multiplier = 1.00
    defect_names = [d.get("label", "").lower() for d in defects]

    # Evaluasi potongan berdasarkan cacat terparah
    has_crease = any("crease" in name or "bent" in name for name in defect_names)
    has_edge = any("edge" in name or "wear" in name for name in defect_names)
    has_scratch = any("scratch" in name for name in defect_names)

    if has_crease:
        multiplier *= 0.65
    if has_edge:
        multiplier *= 0.80
    if has_scratch:
        multiplier *= 0.85

    # Batas minimum multiplier agar tidak negatif / nol
    multiplier = max(0.40, round(multiplier, 2))
    discount_pct = round((1.0 - multiplier) * 100, 2)

    # Klasifikasi Tingkat Kondisi
    if multiplier >= 0.95:
        tier = "Near Mint / Mint"
    elif multiplier >= 0.80:
        tier = "Lightly Played (LP)"
    elif multiplier >= 0.65:
        tier = "Moderately Played (MP)"
    elif multiplier >= 0.50:
        tier = "Heavily Played (HP)"
    else:
        tier = "Damaged"

    return multiplier, tier, discount_pct


def calculate_variant_multiplier(release_year: Any, rarity: str = "") -> float:
    """
    Menghitung pengali vintage dan kelangkaan (M_variant).
    - Vintage Factor: Kartu dengan tahun rilis < 2005 diberi apresiasi nilai kelangkaan kolektor (+20%).
    """
    multiplier = 1.00
    try:
        if release_year is not None and int(release_year) < 2005:
            multiplier += 0.20  # +20% apresiasi vintage era WotC/EX awal
    except (ValueError, TypeError):
        pass

    return round(multiplier, 2)


def evaluate_card_valuation(
    base_price_usd: float,
    release_year: Any = None,
    rarity: str = "",
    defects: List[Dict[str, Any]] = None,
    usd_rate: int = DEFAULT_USD_TO_IDR
) -> Dict[str, Any]:
    """
    Menghitung valuasi menyeluruh untuk satu kartu.
    Mengembalikan dictionary rincian harga dasar, pengali, harga akhir, dan sinyal.
    """
    defects = defects or []
    base_price = max(0.0, float(base_price_usd or 0.0))
    base_price_idr = int(base_price * usd_rate)

    # 1. Hitung Pengali Kondisi Fisik
    f_condition, condition_tier, discount_pct = calculate_condition_factor(defects)

    # 2. Hitung Pengali Varian/Vintage
    m_variant = calculate_variant_multiplier(release_year, rarity)

    # 3. Hitung Harga Wajar Akhir (P_final)
    final_price_usd = round(base_price * m_variant * f_condition, 2)
    final_price_idr = int(final_price_usd * usd_rate)

    # 4. Tentukan Sinyal Transaksi
    if discount_pct >= 30.0:
        signal = "HOLD"  # Cacat fisik berat, perlu kehati-hatian negosiasi
    elif f_condition >= 0.95 and base_price > 0:
        signal = "BUY"   # Kondisi mulus di harga pasar wajar
    else:
        signal = "HOLD"

    return {
        "pricing": {
            "base_price_usd": base_price,
            "base_price_idr": base_price_idr,
            "condition_multiplier": f_condition,
            "condition_discount_pct": discount_pct,
            "final_price_usd": final_price_usd,
            "final_price_idr": final_price_idr,
            "currency_rate": usd_rate
        },
        "condition_report": {
            "condition_tier": condition_tier,
            "has_defects": len(defects) > 0,
            "defect_count": len(defects),
            "defects": defects,
            "evaluation_status": "evaluated"
        },
        "recommendation_signal": signal
    }
