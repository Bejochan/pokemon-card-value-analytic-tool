import React, { useState, useEffect } from 'react';
import './ScannerDashboard.css';

function ScannerDashboard({ scanResult }) {
  // State untuk mengontrol halaman mana yang sedang aktif di dalam Dasbor
  const [dashboardView, setDashboardView] = useState('price');
  const [priceHistory, setPriceHistory] = useState([]);
  
  useEffect(() => {
    if (!scanResult?.card_id) return;
    const fetchHistory = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/cards/${scanResult.card_id}/history`);
        if (res.ok) {
          const data = await res.json();
          setPriceHistory(data.filter(d => d.effective_market_price !== null));
        }
      } catch (err) {
        console.error("Failed to fetch history:", err);
      }
    };
    fetchHistory();
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

  return (
    <div className="dashboard-container">

      {/* TAMPILAN 1: HALAMAN HARGA */}
      {dashboardView === 'price' && (
        <div className="price-view fade-in">

          {/* Efek Cahaya / Glow di belakang kartu */}
          <div className="glow-effect"></div>

          {/* Badge Confidence AI */}
          <div className={`confidence-badge ${confidenceLabel === 'Tinggi' ? 'badge-high' : confidenceLabel === 'Sedang' ? 'badge-mid' : 'badge-low'}`}>
            🤖 AI Confidence: <strong>{confidencePct.toFixed(1)}%</strong> ({confidenceLabel})
          </div>

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
                <img src={officialImage} alt="Card Detail" className="detail-card-img" />
                <div className="celebration-logo">{setSeries || setName}</div>
              </div>

              <div className="card-specs">
                {/* Tabel Spesifikasi Kartu — dari dataset pokemon_cards_dataset_cleaned.csv */}
                <table className="specs-table">
                  <tbody>
                    <tr><td>Name</td><td>{cardName}</td></tr>
                    <tr><td>Set</td><td>{setName}</td></tr>
                    <tr><td>Set ID</td><td>{setId}</td></tr>
                    <tr><td>Series</td><td>{setSeries}</td></tr>
                    <tr><td>Year</td><td>{releaseYear}</td></tr>
                    <tr><td>Rarity</td><td>{rarity}</td></tr>
                    <tr><td>Supertype</td><td>{supertype}</td></tr>
                    <tr><td>Subtypes</td><td>{subtypes}</td></tr>
                    <tr><td>Types</td><td>{types}</td></tr>
                    <tr><td>HP</td><td>{hp !== '-' ? `${hp} HP` : '-'}</td></tr>
                    <tr><td>Condition</td><td>{conditionTier}</td></tr>
                  </tbody>
                </table>

                {/* ============================================ */}
                {/* SEKSI KONDISI FISIK — dari YOLO Condition Grader */}
                {/* ============================================ */}
                <div className="defect-section">

                  {evalStatus === 'bypassed_oncam' ? (
                    <>
                      <h4 className="defect-title">🔍 Condition Not Evaluated</h4>
                      <p className="defect-clear-msg">Scan via camera (fast mode). Upload a photo for full condition grading.</p>
                    </>
                  ) : hasDefects ? (
                    <>
                      <h4 className="defect-title warning">⚠️ {defectCount} Defect{defectCount > 1 ? 's' : ''} Detected ⚠️</h4>
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
                      <h4 className="defect-title success">✅ No Defect Detected ✅</h4>
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
                      <tr>
                        <td>Condition Multiplier</td>
                        <td>×{conditionMultiplier.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>Exchange Rate</td>
                        <td>Rp{currencyRate.toLocaleString('id-ID')}/USD</td>
                      </tr>
                      <tr>
                        <td><strong>Final Value (USD)</strong></td>
                        <td><strong>${finalPriceUsd.toFixed(2)}</strong></td>
                      </tr>
                      <tr>
                        <td><strong>Final Value (IDR)</strong></td>
                        <td className="text-success"><strong>{formatIDR(finalPriceIdr)}</strong></td>
                      </tr>
                      <tr>
                        <td>Condition Tier</td>
                        <td>{conditionTier}</td>
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
                    <span className="stat-value">{formatIDR(predictedPriceIdr)}</span>
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
                    <h4 className="candidates-title">🃏 Alternative Matches</h4>
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

              {/* Grafik Tren Harga (statis – representasi visual) */}
              <div className="chart-container">
                <p className="chart-subtitle">Price History & Forecasting</p>
                {priceHistory.length === 0 ? (
                  <div style={{padding: '50px 0', textAlign: 'center', color: '#888'}}>Belum ada data harga</div>
                ) : (
                  <>
                    <div className="svg-wrapper">
                      <svg viewBox="0 0 500 200" className="market-chart" preserveAspectRatio="none">
                        <line x1="0" y1="50"  x2="500" y2="50"  stroke="#f0f0f0" strokeWidth="2" />
                        <line x1="0" y1="100" x2="500" y2="100" stroke="#f0f0f0" strokeWidth="2" />
                        <line x1="0" y1="150" x2="500" y2="150" stroke="#f0f0f0" strokeWidth="2" />
                        <polyline
                          fill="none"
                          stroke="#c2185b"
                          strokeWidth="5"
                          points={priceHistory.slice(-6).map((d, i, arr) => `${i * (arr.length > 1 ? 500 / (arr.length - 1) : 250)},${Math.min(...arr.map(x=>x.effective_market_price))===Math.max(...arr.map(x=>x.effective_market_price)) ? 100 : 150 - ((d.effective_market_price - Math.min(...arr.map(x=>x.effective_market_price))*0.9) / (Math.max(...arr.map(x=>x.effective_market_price))*1.1 - Math.min(...arr.map(x=>x.effective_market_price))*0.9)) * 100}`).join(" ")}
                        />
                        {priceHistory.slice(-6).map((d, i, arr) => (
                          <circle key={i} cx={i * (arr.length > 1 ? 500 / (arr.length - 1) : 250)} cy={Math.min(...arr.map(x=>x.effective_market_price))===Math.max(...arr.map(x=>x.effective_market_price)) ? 100 : 150 - ((d.effective_market_price - Math.min(...arr.map(x=>x.effective_market_price))*0.9) / (Math.max(...arr.map(x=>x.effective_market_price))*1.1 - Math.min(...arr.map(x=>x.effective_market_price))*0.9)) * 100} r="7" fill="#c2185b" />
                        ))}
                      </svg>
                    </div>
                    <div className="chart-labels">
                      {priceHistory.slice(-6).map((d, i) => <span key={i}>{new Date(d.recorded_date).toLocaleDateString('id-ID', { month: 'short' })}</span>)}
                    </div>
                  </>
                )}
              </div>

              <button className="marketplace-btn">SCAN OTHER CARDS</button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

export default ScannerDashboard;