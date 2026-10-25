import React, { useState, useEffect } from 'react';
import './ScannerDashboard.css';

function ScannerDashboard({ scanResult, onScanOther }) {
  // State untuk mengontrol halaman mana yang sedang aktif di dalam Dasbor
  const [dashboardView, setDashboardView] = useState('price');
  const [priceHistory, setPriceHistory] = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  
  useEffect(() => {
    if (!scanResult?.card_id) return;
    
    // 1. Ambil riwayat harga masa lalu
    const fetchHistory = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/cards/${scanResult.card_id}/history`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setPriceHistory(data.filter(d => d.effective_market_price !== null));
          }
        }
      } catch (err) {
        console.error("Gagal memuat riwayat harga:", err);
      }
    };

    // 2. Ambil data peramalan 7 hari dari endpoint Forecast Model
    const fetchForecast = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/cards/${scanResult.card_id}/forecast`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.status === 'success') {
            setForecastData(data);
          }
        }
      } catch (err) {
        console.error("Gagal memuat peramalan harga:", err);
      }
    };

    fetchHistory();
    fetchForecast();
  }, [scanResult?.card_id]);

  // =====================================================================
  // DATA DARI BACKEND (Model 1 CLIP + Model 2 YOLO + Analytics Engine)
  // Semua field diambil langsung dari response JSON backend FastAPI.
  // =====================================================================

  // --- Identitas Kartu (dari card_identifier.py + dataset CSV) ---
  const cardName   = scanResult?.name         ?? 'Unknown Card';
  const setName    = scanResult?.set_name      ?? '-';
  const setId      = scanResult?.set_id        ?? '-';
  const setSeries  = scanResult?.set_series    ?? '-';
  const releaseYear = scanResult?.release_year  ?? '-';
  const rarity     = scanResult?.rarity        ?? '-';
  const supertype  = scanResult?.supertype     ?? '-';
  const subtypes   = scanResult?.subtypes      ?? '-';
  const types      = scanResult?.types         ?? '-';
  const hp         = scanResult?.hp            ?? '-';
  const officialImage = (scanResult?.official_image_url) || '/card-result.png';
  const userScannedImage = scanResult?.user_scanned_image || scanResult?.scanned_image || null;

  // --- Confidence AI ---
  const confidencePct   = scanResult?.confidence_percentage ?? 0;
  const confidenceLabel = scanResult?.confidence_label      ?? 'Uncertain';

  // --- Harga (dari analytics_engine.py) ---
  const pricing              = scanResult?.pricing             ?? {};
  const basePriceUsd         = pricing?.base_price_usd        ?? 0;
  const basePriceIdr         = pricing?.base_price_idr        ?? 0;
  const conditionMultiplier  = pricing?.condition_multiplier  ?? 1.0;
  const conditionDiscountPct = pricing?.condition_discount_pct ?? 0;
  const finalPriceIdr        = pricing?.final_price_idr       ?? (scanResult?.estimated_price ?? 0);
  const finalPriceUsd        = pricing?.final_price_usd       ?? 0;
  const currencyRate         = pricing?.currency_rate         ?? 15500;

  // --- Kondisi & Cacat Fisik (dari card_condition_grader.py via YOLO) ---
  const conditionReport = scanResult?.condition_report ?? null;
  const conditionTier   = conditionReport?.condition_tier  ?? (scanResult?.card_condition ?? 'Near Mint / Mint');
  const hasDefects      = conditionReport?.has_defects     ?? false;
  const defectCount     = conditionReport?.defect_count    ?? 0;
  const defects         = conditionReport?.defects         ?? [];
  const evalStatus      = conditionReport?.evaluation_status ?? 'evaluated';

  // --- Analitik Pasar (ML Forecasting) ---
  const marketAnalytics   = scanResult?.market_analytics ?? {};
  const predictedPriceIdr = marketAnalytics?.predicted_fair_value_idr ?? 0;
  const mispricingGap     = marketAnalytics?.mispricing_gap_pct ?? 0;

  // --- Sinyal Transaksi (dari analytics_engine.py) ---
  const recommendationSignal = scanResult?.recommendation_signal ?? 'HOLD';

  // --- Kandidat Alternatif (dari FAISS top-k) ---
  const candidates = scanResult?.candidates ?? [];

  // --- Format harga IDR ---
  const formatIDR = (amount) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(amount);

  // --- Warna sinyal transaksi ---
  let signalColor = 'text-yellow';
  if (recommendationSignal === 'BUY' || recommendationSignal === 'STRONG BUY') signalColor = 'text-green';
  if (recommendationSignal === 'SELL') signalColor = 'text-pink';

  // =====================================================================
  // PERHITUNGAN GRAFIK TREN HARGA & FORECAST 7 HARI
  // =====================================================================
  const currentRateVal = currencyRate || 18000;
  // Menyelaraskan basis ke harga pasar acuan (Base Market Price) agar kurva tidak melonjak
  const currentPriceVal = (forecastData?.current_price_usd > 0)
    ? forecastData.current_price_usd
    : (basePriceUsd > 0 ? basePriceUsd : (finalPriceUsd || 1.0));
  const currentPriceIdrVal = (forecastData?.current_price_idr > 0)
    ? forecastData.current_price_idr
    : Math.round(currentPriceVal * currentRateVal);

  // 1. Titik Riwayat (ambil maksimal 4 data terakhir agar proporsional)
  const historySlice = priceHistory.slice(-4);
  const historyItems = historySlice.map((d) => {
    const pUsd = Number(d.effective_market_price);
    const pIdr = Math.round(pUsd * currentRateVal);
    const dateObj = new Date(d.recorded_date);
    const label = !isNaN(dateObj) 
      ? dateObj.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })
      : 'Riwayat';
    return {
      type: 'history',
      date: d.recorded_date,
      label,
      priceUsd: pUsd,
      priceIdr: pIdr
    };
  });

  // 2. Titik Hari Ini (Jangkar penghubung masa lalu dan proyeksi masa depan yang mulus)
  const todayItem = {
    type: 'anchor',
    date: new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }),
    label: 'Hari ini',
    priceUsd: currentPriceVal,
    priceIdr: currentPriceIdrVal
  };

  // 3. Titik Prediksi 7 Hari (dari endpoint forecast backend)
  const forecastItems = (forecastData?.forecast || []).map((f) => {
    const pUsd = Number(f.predicted_price_usd);
    const pIdr = Math.round(pUsd * currentRateVal);
    const p10Usd = f.p10_usd !== undefined ? Number(f.p10_usd) : (pUsd * 0.90);
    const p90Usd = f.p90_usd !== undefined ? Number(f.p90_usd) : (pUsd * 1.10);
    const p10Idr = Math.round(p10Usd * currentRateVal);
    const p90Idr = Math.round(p90Usd * currentRateVal);
    const dateObj = new Date(f.date);
    const formattedDate = !isNaN(dateObj) 
      ? dateObj.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })
      : f.date;
    return {
      type: 'forecast',
      date: formattedDate,
      label: `H+${f.day}`,
      dayNum: f.day,
      priceUsd: pUsd,
      priceIdr: pIdr,
      p10Usd,
      p90Usd,
      p10Idr,
      p90Idr
    };
  });

  // Gabungan seluruh titik untuk rendering garis kontinu
  const combinedPoints = [...historyItems, todayItem, ...forecastItems];

  // Hitung skala koordinat SVG (viewBox 560 x 165) dengan ruang Sumbu Y di kiri
  const svgWidth = 560;
  const svgHeight = 165;
  const padLeft = 76; // Ruang teks label harga Sumbu Y
  const padRight = 20;
  const padTop = 18;
  const padBottom = 25;
  const usableW = svgWidth - padLeft - padRight;
  const usableH = svgHeight - padTop - padBottom;

  const allPrices = [
    ...combinedPoints.map(p => p.priceUsd),
    ...forecastItems.map(p => p.p90Usd),
    ...forecastItems.map(p => p.p10Usd)
  ].filter(p => !isNaN(p) && p > 0);
  const minPrice = allPrices.length > 0 ? Math.min(...allPrices) : 1;
  const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : 2;
  const priceRange = maxPrice === minPrice ? (maxPrice * 0.25 || 0.25) : (maxPrice - minPrice);
  const plotMin = Math.max(0, minPrice - (priceRange * 0.15));
  const plotMax = maxPrice + (priceRange * 0.15);
  const plotRange = plotMax - plotMin;

  // 3 Titik Garis Panduan & Label Harga Sumbu Y (Atas, Tengah, Bawah)
  const yTicks = [
    { y: padTop, valIdr: Math.round(plotMax * currentRateVal) },
    { y: padTop + (usableH / 2), valIdr: Math.round(((plotMax + plotMin) / 2) * currentRateVal) },
    { y: padTop + usableH, valIdr: Math.round(plotMin * currentRateVal) }
  ];

  const pointsWithCoords = combinedPoints.map((pt, idx) => {
    const total = combinedPoints.length;
    const x = total > 1 ? padLeft + (idx * (usableW / (total - 1))) : padLeft + (usableW / 2);
    const norm = (pt.priceUsd - plotMin) / plotRange;
    const y = padTop + usableH - (norm * usableH);
    
    let yP10 = y;
    let yP90 = y;
    if (pt.type === 'forecast' && pt.p10Usd && pt.p90Usd) {
      const normP10 = (pt.p10Usd - plotMin) / plotRange;
      const normP90 = (pt.p90Usd - plotMin) / plotRange;
      yP10 = padTop + usableH - (normP10 * usableH);
      yP90 = padTop + usableH - (normP90 * usableH);
    }
    return { ...pt, x, y, yP10, yP90 };
  });

  // Polyline koordinat Riwayat Pasar (history s/d anchor hari ini)
  const historyCoords = pointsWithCoords.slice(0, historyItems.length + 1).map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // Polyline koordinat Prediksi AI (anchor hari ini s/d H+7)
  const forecastCoords = pointsWithCoords.slice(historyItems.length).map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // Poligon Pita Kuantil (Quantile Ribbon P10 - P90)
  const todayPoint = pointsWithCoords[historyItems.length];
  const forecastPtsWithCoords = pointsWithCoords.slice(historyItems.length + 1);
  let ribbonPolygonPoints = '';
  if (todayPoint && forecastPtsWithCoords.length > 0) {
    const upperLine = forecastPtsWithCoords.map(p => `${p.x.toFixed(1)},${p.yP90.toFixed(1)}`);
    const lowerLine = [...forecastPtsWithCoords].reverse().map(p => `${p.x.toFixed(1)},${p.yP10.toFixed(1)}`);
    ribbonPolygonPoints = [
      `${todayPoint.x.toFixed(1)},${todayPoint.y.toFixed(1)}`,
      ...upperLine,
      ...lowerLine,
      `${todayPoint.x.toFixed(1)},${todayPoint.y.toFixed(1)}`
    ].join(' ');
  }


  return (
    <div className={`dashboard-container ${dashboardView === 'details' ? 'details-mode' : 'price-mode'}`}>

      {/* TAMPILAN 1: HALAMAN HARGA */}
      {dashboardView === 'price' && (
        <div className="price-view fade-in">

          {/* Efek Cahaya / Glow di belakang kartu */}
          <div className="glow-effect"></div>

          {/* Gambar Kartu Hasil Scan */}
          <img src={officialImage} alt="Scanned Card" className="scanned-card" />

          {/* Label Harga */}
          <div className="price-tag-container">
            <img src="/price-shape.png" alt="Background Harga" className="price-shape" />
            <div className="price-text">{formatIDR(finalPriceIdr)}</div>
          </div>

          {/* Tombol Panah Bawah */}
          <button
            className="down-arrow-btn"
            onClick={() => setDashboardView('details')}
          >
            <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

        </div>
      )}

      {/* TAMPILAN 2: HALAMAN DETAIL */}
      {dashboardView === 'details' && (
        <div className="details-view slide-up">

          {/* Tombol kembali ke atas */}
          <button className="up-arrow-btn" onClick={() => setDashboardView('price')}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
          </button>

          <div className="details-grid">

            {/* ============================================ */}
            {/* KOTAK KIRI: Detail Kartu & Kondisi Fisik     */}
            {/* ============================================ */}
            <div className="info-box card-info-box">
              <div className="card-visuals">
                {/* 1. OUTPUT ATAS: Foto Hasil Scan User */}
                <div className="card-thumb-wrapper">
                  <div className="card-thumb-label scan-label">Foto Pemindaian User</div>
                  <img 
                    src={userScannedImage || officialImage} 
                    alt="Foto Pemindaian User" 
                    className="detail-card-img user-scan-img" 
                  />
                </div>

                {/* 2. OUTPUT BAWAH: Kartu Resmi Sistem */}
                <div className="card-thumb-wrapper">
                  <div className="card-thumb-label master-label">Referensi Resmi Master</div>
                  <img 
                    src={officialImage} 
                    alt="Referensi Resmi Master" 
                    className="detail-card-img master-official-img" 
                  />
                </div>

                <div className="celebration-logo">{setSeries || setName}</div>
              </div>

              <div className="card-specs">
                {/* Tabel Spesifikasi Kartu — dari dataset pokemon_cards_dataset_cleaned.csv */}
                <table className="specs-table">
                  <tbody>
                    <tr><td>Name</td><td>{cardName}</td></tr>
                    <tr><td>Set</td><td>{setName}</td></tr>
                    <tr><td>Set Code</td><td>{setId}</td></tr>
                    <tr><td>Series</td><td>{setSeries}</td></tr>
                    <tr><td>Year</td><td>{releaseYear}</td></tr>
                    <tr><td>Rarity</td><td>{rarity}</td></tr>
                    <tr><td>Subtypes</td><td>{subtypes}</td></tr>
                  </tbody>
                </table>

                {/* ============================================ */}
                {/* SEKSI KONDISI FISIK — dari YOLO Condition Grader */}
                {/* ============================================ */}
                <div className="defect-section">

                  {evalStatus === 'bypassed_oncam' ? (
                    <>
                      <h4 className="defect-title">Condition Not Evaluated</h4>
                      <p className="defect-clear-msg">Scan via camera (fast mode). Upload a photo for full condition grading.</p>
                    </>
                  ) : hasDefects ? (
                    <>
                      <h4 className="defect-title warning">{defectCount} Defect{defectCount > 1 ? 's' : ''} Detected</h4>
                      <ul className="defect-list">
                        {defects.map((defect, index) => (
                          <li key={index}>
                            <span className="defect-label">{defect.label}</span>
                            <span className="defect-conf">{(defect.confidence * 100).toFixed(0)}% conf.</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <>
                      <h4 className="defect-title success">No Defect Detected</h4>
                      <p className="defect-clear-msg">Card is in pristine physical condition.</p>
                    </>
                  )}

                  {/* Tabel Pecahan Harga — dari analytics_engine.py */}
                  <table className="specs-table">
                    <tbody>
                      <tr>
                        <td><strong>Base Price (USD)</strong></td>
                        <td><strong>${basePriceUsd.toFixed(2)}</strong></td>
                      </tr>
                      <tr>
                        <td><strong>Base Price (IDR)</strong></td>
                        <td><strong>{formatIDR(basePriceIdr)}</strong></td>
                      </tr>
                      <tr>
                        <td>Condition Discount</td>
                        <td className={conditionDiscountPct > 0 ? 'text-danger' : 'text-success'}>
                          {conditionDiscountPct > 0 ? `- ${conditionDiscountPct.toFixed(2)}%` : '0.00%'}
                        </td>
                      </tr>
                      <tr className="highlight-price-row">
                        <td><strong>Final Value (USD)</strong></td>
                        <td className="text-green"><strong>${finalPriceUsd.toFixed(2)}</strong></td>
                      </tr>
                      <tr className="highlight-price-row">
                        <td><strong>Final Value (IDR)</strong></td>
                        <td className="text-green final-idr-value"><strong>{formatIDR(finalPriceIdr)}</strong></td>
                      </tr>
                      <tr>
                        <td>Condition Tier</td>
                        <td>{conditionTier}</td>
                      </tr>
                      <tr>
                        <td>Est. value</td>
                        <td className="text-green"><strong>{Math.max(0, 100 - conditionDiscountPct).toFixed(2)}%</strong></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* ============================================ */}
            {/* KOTAK KANAN: Analitik Pasar & Signal         */}
            {/* ============================================ */}
            <div className="info-box analytics-box">
              <h2 className="analytics-title">Market Analytics</h2>

              <div className="stats-container">
                {/* Baris 1: Sinyal Transaksi dari Analytics Engine */}
                <div className="stats-row">
                  <div className={`stat-card signal-${recommendationSignal.toLowerCase()}`}>
                    <span className="stat-label">Trading Signal</span>
                    <span className={`stat-value ${signalColor}`}>{recommendationSignal}</span>
                    {forecastData?.signal_reason && (
                      <span className="stat-signal-desc" title={forecastData.signal_reason}>
                        {forecastData.signal_reason}
                      </span>
                    )}
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">AI Confidence</span>
                    <span className={`stat-value ${confidencePct >= 70 ? 'text-green' : confidencePct >= 40 ? 'text-yellow' : 'text-pink'}`}>
                      {confidencePct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Condition Score</span>
                    <span className={`stat-value ${conditionMultiplier >= 0.95 ? 'text-green' : conditionMultiplier >= 0.80 ? 'text-yellow' : 'text-pink'}`}>
                      {(conditionMultiplier * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Baris 2: Data Detail Valuasi */}
                <div className="stats-row">
                  <div className="stat-card">
                    <span className="stat-label">Rarity</span>
                    <span className="stat-value" style={{fontSize: '0.75rem'}}>{rarity !== '-' ? rarity : 'N/A'}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Release Year</span>
                    <span className="stat-value">{releaseYear !== '-' ? releaseYear : 'N/A'}
                      {releaseYear !== '-' && releaseYear < 2005 && <span className="stat-sub text-green"> (Vintage +20%)</span>}
                    </span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Market Price</span>
                    <span className="stat-value text-green">{formatIDR(basePriceIdr)}</span>
                  </div>
                </div>

                {/* Baris 3: Machine Learning Valuation */}
                <div className="stats-row">
                  <div className="stat-card" style={{ background: 'rgba(255, 255, 255, 0.1)', border: '1px solid rgba(255,255,255,0.3)' }}>
                    <span className="stat-label text-yellow">Predicted Fair Value (ML)</span>
                    <span className="stat-value text-green">{formatIDR(predictedPriceIdr)}</span>
                  </div>
                  <div className="stat-card" style={{ background: 'rgba(255, 255, 255, 0.1)', border: '1px solid rgba(255,255,255,0.3)' }}>
                    <span className="stat-label text-yellow">Mispricing Gap</span>
                    <span className={`stat-value ${mispricingGap < 0 ? 'text-green' : mispricingGap > 0 ? 'text-pink' : 'text-yellow'}`}>
                      {mispricingGap > 0 ? '+' : ''}{mispricingGap.toFixed(2)}%
                    </span>
                  </div>
                </div>

                {/* Kandidat Alternatif AI */}
                {candidates.length > 0 && (
                  <div className="candidates-section">
                    <h4 className="candidates-title">Alternative Matches</h4>
                    <ul className="candidates-list">
                      {candidates.map((c) => (
                        <li key={c.card_id} className="candidate-item">
                          <span className="candidate-rank">#{c.rank}</span>
                          <span className="candidate-name">{c.name}</span>
                          <span className="candidate-conf">{c.confidence_percentage?.toFixed(1)}%</span>
                          {c.rarity && <span className="candidate-rarity">{c.rarity}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Grafik Tren Harga & Peramalan AI 7 Hari */}
              <div className="chart-container">
                <div className="chart-header-row">
                  <div className="chart-title-area">
                    <p className="chart-subtitle">Price History & Forecasting</p>
                    {forecastData && (
                      <span className="forecast-trend-tag">
                        Proyeksi 7 Hari: {forecastData.change_pct >= 0 ? '+' : ''}{forecastData.change_pct}% 
                        (Target: {formatIDR(forecastData.predicted_price_day7_idr)})
                      </span>
                    )}
                  </div>
                  
                  <div className="chart-legend-box">
                    <div className="legend-entry">
                      <span className="legend-bar history-bar"></span>
                      <span className="legend-name">Riwayat Pasar</span>
                    </div>
                    <div className="legend-entry">
                      <span className="legend-bar forecast-bar"></span>
                      <span className="legend-name">Target Wajar (P50)</span>
                    </div>
                    <div className="legend-entry">
                      <span className="legend-bar ribbon-bar"></span>
                      <span className="legend-name">Rentang Wajar (P10 - P90)</span>
                    </div>
                  </div>
                </div>

                {combinedPoints.length === 0 ? (
                  <div className="chart-empty-state">Data peramalan harga sedang dimuat...</div>
                ) : (
                  <div className="svg-wrapper">
                    {/* Tooltip Mengambang Saat Hover Titik */}
                    {hoveredPoint && (
                      <div 
                        className="chart-hover-card"
                        style={{
                          left: `${Math.min(80, Math.max(10, (hoveredPoint.x / svgWidth) * 100))}%`
                        }}
                      >
                        <div className="hover-type-label">
                          {hoveredPoint.type === 'history' ? 'Riwayat Pasar' : (hoveredPoint.type === 'anchor' ? 'Harga Saat Ini' : 'Prediksi AI (P50)')}
                        </div>
                        <div className="hover-date">{hoveredPoint.date}</div>
                        <div className="hover-price-val">
                          {formatIDR(hoveredPoint.priceIdr)}
                          <span className="hover-usd-val"> (${hoveredPoint.priceUsd.toFixed(2)})</span>
                        </div>
                        {hoveredPoint.type === 'forecast' && hoveredPoint.p10Idr && hoveredPoint.p90Idr && (
                          <div className="hover-range-text" style={{ fontSize: '9px', color: '#cbd5e1', marginTop: '2px', fontWeight: 600 }}>
                            Rentang: {formatIDR(hoveredPoint.p10Idr)} – {formatIDR(hoveredPoint.p90Idr)}
                          </div>
                        )}
                      </div>
                    )}

                    <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="market-chart" preserveAspectRatio="none">
                      {/* Garis Grid Horizontal & Label Sumbu Y di Sisi Kiri */}
                      {yTicks.map((tick, idx) => (
                        <g key={idx}>
                          <line 
                            x1={padLeft} 
                            y1={tick.y} 
                            x2={svgWidth - padRight} 
                            y2={tick.y} 
                            stroke="#f1f5f9" 
                            strokeWidth="1.2" 
                            strokeDasharray="3 3" 
                          />
                          <text
                            x={padLeft - 6}
                            y={tick.y + 3.5}
                            textAnchor="end"
                            fill="#94a3b8"
                            fontSize="9"
                            fontFamily="'Montserrat', sans-serif"
                            fontWeight="600"
                          >
                            {formatIDR(tick.valIdr)}
                          </text>
                        </g>
                      ))}

                      {/* Selubung Pita Kuantil Probabilitas (Quantile Ribbon P10 - P90) */}
                      {ribbonPolygonPoints && (
                        <polygon
                          points={ribbonPolygonPoints}
                          fill="rgba(0, 210, 106, 0.22)"
                          stroke="rgba(0, 210, 106, 0.45)"
                          strokeWidth="1.2"
                          strokeDasharray="3 3"
                        />
                      )}

                      {/* Segmen 1: Garis Riwayat Pasar (Solid Line) */}
                      {historyCoords && (
                        <polyline
                          fill="none"
                          stroke="#c2185b"
                          strokeWidth="3.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={historyCoords}
                        />
                      )}

                      {/* Segmen 2: Garis Prediksi AI 7 Hari (Dashed Line) */}
                      {forecastCoords && (
                        <polyline
                          fill="none"
                          stroke="#00d26a"
                          strokeWidth="3.5"
                          strokeDasharray="6 4"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={forecastCoords}
                        />
                      )}

                      {/* Titik-Titik Lingkaran & Area Interaktif */}
                      {pointsWithCoords.map((pt, i) => {
                        const isHistory = pt.type === 'history';
                        const isAnchor = pt.type === 'anchor';
                        const fillColor = isAnchor ? '#ffffff' : (isHistory ? '#c2185b' : '#00d26a');
                        const strokeColor = isAnchor ? '#00d26a' : '#ffffff';
                        const radius = isAnchor ? 6.5 : 5;

                        return (
                          <g key={i}>
                            {/* Titik Visual */}
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r={radius}
                              fill={fillColor}
                              stroke={strokeColor}
                              strokeWidth={isAnchor ? 3 : 2}
                              className="chart-dot"
                            />
                            {/* Area Hit Sentuh Mouse Lebih Luas */}
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r={18}
                              fill="transparent"
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredPoint(pt)}
                              onMouseLeave={() => setHoveredPoint(null)}
                            />
                          </g>
                        );
                      })}
                    </svg>

                    {/* Label Sumbu X (Waktu / Tanggal) Sejajar Titik */}
                    <div className="chart-labels" style={{ paddingLeft: `${padLeft}px`, paddingRight: `${padRight}px` }}>
                      {pointsWithCoords.map((pt, i) => (
                        <span 
                          key={i} 
                          className={`chart-date-label ${pt.type}`}
                        >
                          {pt.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <button 
                className="marketplace-btn"
                onClick={() => {
                  if (onScanOther) {
                    onScanOther();
                  } else {
                    window.location.hash = '#upload';
                    window.location.reload();
                  }
                }}
              >
                SCAN OTHER CARDS
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

export default ScannerDashboard;