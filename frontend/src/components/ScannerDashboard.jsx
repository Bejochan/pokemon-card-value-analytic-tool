import React, { useState } from 'react';
import './ScannerDashboard.css';

function ScannerDashboard() {
  // State untuk mengontrol halaman mana yang sedang aktif di dalam Dasbor
  const [dashboardView, setDashboardView] = useState('price');
  // Data simulasi hasil deteksi (Nanti akan didapat dari backend)
  // Coba ubah menjadi array kosong [] untuk melihat tampilan "No defect detected"
  const detectedDefects = ['Surface scratches', 'Dents']; /* --- UBAH SESUAI FISIK --- */ 
  const originalPrice = 920.00;
  // Jika ada cacat, diskon 2.28%. Jika tidak ada, diskon 0%
  const conditionDiscount = detectedDefects.length > 0 ? 0.0228 : 0; 
  const finalPrice = originalPrice - (originalPrice * conditionDiscount);
  const conditionTier = detectedDefects.length > 0 ? "Lightly used" : "Mint / Near Mint";

  return (
    <div className="dashboard-container">
      
      {/* TAMPILAN 1: HALAMAN HARGA (Sesuai Mockup) */}
      {dashboardView === 'price' && (
        <div className="price-view fade-in">
          
          {/* Efek Cahaya / Glow di belakang kartu */}
          <div className="glow-effect"></div>
          
          {/* Gambar Kartu Hasil Scan */}
          <img src="/card-result.png" alt="Scanned Card" className="scanned-card" />
          
          {/* Label Harga Hijau (Dipisah antara background dan teks) */}
          <div className="price-tag-container">
            <img src="/price-shape.png" alt="Background Harga" className="price-shape" />
            <div className="price-text">$&nbsp;899.00</div>
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
            
            {/* KOTAK KIRI: Detail Kartu & Tabel */}
            <div className="info-box card-info-box">
              <div className="card-visuals">
                <img src="/card-result.png" alt="Card Detail" className="detail-card-img" />
                <div className="celebration-logo">30th Celebration</div>
              </div>
              
              <div className="card-specs">
                {/* Jadual Spesifikasi Kad (Dipadatkan) */}
                <table className="specs-table">
                  <tbody>
                    <tr><td>Name</td><td>Fuecoco</td></tr>
                    <tr><td>Rarity</td><td>Common</td></tr>
                    <tr><td>Holofoil type</td><td>Reverse holofoil</td></tr>
                    <tr><td>Language</td><td>English 🇬🇧</td></tr>
                    <tr><td>Set number</td><td>036 / 084</td></tr>
                    <tr><td>Year</td><td>2017</td></tr>
                    <tr><td>Set code</td><td>M2a</td></tr>
                    <tr><td>Regulation mark</td><td>H</td></tr>
                    <tr><td>Stage</td><td>Basic</td></tr>
                  </tbody>
                </table>

                {/* Bahagian Penilaian Keadaan Fizikal (Baharu) */}
                <div className="defect-section">
                  
                  {/* Pengecekan Kondisi dengan Ternary Operator */}
                  {detectedDefects.length > 0 ? (
                    <>
                      <h4 className="defect-title warning">⚠️ Defect detected ⚠️</h4>
                      <ul className="defect-list">
                        {detectedDefects.map((defect, index) => (
                          <li key={index}>{defect}</li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <>
                      <h4 className="defect-title success">✅ No defect detected ✅</h4>
                      <p className="defect-clear-msg">Card is in pristine physical condition.</p>
                    </>
                  )}

                  {/* Jadual Pecahan Harga Berdasarkan Keadaan */}
                  <table className="specs-table">
                    <tbody>
                      <tr>
                        <td><strong>Original value</strong></td>
                        <td><strong>$ {originalPrice.toFixed(2)}</strong></td>
                      </tr>
                      <tr>
                        <td><strong>Physical condition</strong></td>
                        <td className={detectedDefects.length > 0 ? "text-danger" : "text-success"}>
                          {detectedDefects.length > 0 ? "- 2.28%" : "0.00%"}
                        </td>
                      </tr>
                      <tr>
                        <td><strong>Final value</strong></td>
                        <td className="text-success"><strong>$ {finalPrice.toFixed(2)}</strong></td>
                      </tr>
                      <tr>
                        <td>Condition tier</td>
                        <td>{conditionTier}</td>
                      </tr>
                      <tr>
                        <td>Est. value</td>
                        <td>{detectedDefects.length > 0 ? "97.72%" : "100.00%"}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* KOTAK KANAN: Analitik Pasar */}
            <div className="info-box analytics-box">
              <h2 className="analytics-title">Market Trend</h2>
              
              <div className="stats-container">
                {/* Baris 1: Data Finansial Dasar */}
                <div className="stats-row">
                  <div className="stat-card">
                    <span className="stat-label">All-Time High</span>
                    <span className="stat-value text-green">$1,250.00</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Market Avg</span>
                    <span className="stat-value">$850.50</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">30-Day Trend</span>
                    <span className="stat-value text-pink">↑ +15.2%</span>
                  </div>
                </div>

                {/* Baris 2: Analitik Lanjutan */}
                <div className="stats-row">
                  <div className="stat-card">
                    <span className="stat-label">Popularity Index</span>
                    <span className="stat-value">94<span className="stat-sub">/100</span></span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Age vs Market</span>
                    <span className="stat-value">9 Yrs <span className="stat-sub text-green">(+12%)</span></span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Price Valuation</span>
                    <span className="stat-value text-green">Underpriced</span>
                  </div>
                  <div className="stat-card signal-buy">
                    <span className="stat-label">Trading Signal</span>
                    <span className="stat-value">STRONG BUY</span>
                  </div>
                </div>
              </div>

              {/* Grafik Garis (Line Chart) */}
              <div className="chart-container">
                <p className="chart-subtitle">Price History & Forecasting</p>
                <div className="svg-wrapper">
                  {/* Hapus preserveAspectRatio="none" agar lingkaran tetap bulat sempurna */}
                  <svg viewBox="0 0 500 200" className="market-chart" preserveAspectRatio="none">
                    <line x1="0" y1="50" x2="500" y2="50" stroke="#f0f0f0" strokeWidth="2" />
                    <line x1="0" y1="100" x2="500" y2="100" stroke="#f0f0f0" strokeWidth="2" />
                    <line x1="0" y1="150" x2="500" y2="150" stroke="#f0f0f0" strokeWidth="2" />
                    
                    {/* Garis Tren Harga (Warna Crimson Gelap) */}
                    <polyline 
                      fill="none" 
                      stroke="#c2185b" 
                      strokeWidth="5" 
                      points="0,150 100,120 200,110 300,100 400,70 500,60" 
                    />
                    
                    {/* Titik Data (Solid, tanpa border putih) */}
                    <circle cx="0" cy="150" r="7" fill="#c2185b" />
                    <circle cx="100" cy="120" r="7" fill="#c2185b" />
                    <circle cx="200" cy="110" r="7" fill="#c2185b" />
                    <circle cx="300" cy="100" r="7" fill="#c2185b" />
                    <circle cx="400" cy="70" r="7" fill="#c2185b" />
                    <circle cx="500" cy="60" r="7" fill="#c2185b" />
                  </svg>
                </div>
                
                <div className="chart-labels">
                  <span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Okt</span><span>Nov</span>
                </div>
              </div>
              
              {/* Teks tombol diperbarui */}
              <button className="marketplace-btn">SCAN OTHER CARDS</button>
            </div>
            
          </div>
        </div>
      )}

    </div>
  );
}

export default ScannerDashboard;