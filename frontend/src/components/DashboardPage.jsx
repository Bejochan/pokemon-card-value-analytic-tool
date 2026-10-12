import React, { useState, useEffect } from 'react';
import './DashboardPage.css';

// 2. Buat komponen AnimatedCounter untuk menangani animasi angka
const AnimatedCounter = ({ endValue, duration, prefix = "", suffix = "", isDecimal = false }) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Menggunakan fungsi ease-out agar animasi melambat di akhir
      const easeOutProgress = 1 - Math.pow(1 - progress, 3);
      const currentCount = easeOutProgress * endValue;
      setCount(currentCount);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setCount(endValue); // Pastikan angka akhir presisi
      }
    };
    window.requestAnimationFrame(step);
  }, [endValue, duration]);
  // Memformat angka agar memiliki koma ribuan (contoh: 1,452)
  const formatNumber = (num) => {
    if (isDecimal) {
      return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return Math.floor(num).toLocaleString('en-US');
  };
  return <span>{prefix}{formatNumber(count)}{suffix}</span>;
};

// Komponen baru untuk mengacak teks tren pasar
const AnimatedTextScramble = ({ targetText, duration }) => {
  const [displayText, setDisplayText] = useState("");
  
  const marketTerms = [
    "volatile", "bearish", "stagnant", "fluctuating", 
    "recovering", "correction", "rallying", "stable"
  ];

  useEffect(() => {
    let startTimestamp = null;
    let lastUpdate = 0;
    let lastRandomIndex = -1; // Menyimpan memori kata terakhir
    
    // PERBAIKAN 1: Turunkan interval dari 80 ke 30 agar secepat animasi angka
    const updateInterval = 30; 

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      
      const elapsed = timestamp - startTimestamp;
      const progress = Math.min(elapsed / duration, 1);

      if (progress < 1) {
        if (elapsed - lastUpdate > updateInterval) {
          
          let randomIndex;
          // PERBAIKAN 2: Mencegah sistem memilih kata yang sama 2x berturut-turut (mencegah lag visual)
          do {
            randomIndex = Math.floor(Math.random() * marketTerms.length);
          } while (randomIndex === lastRandomIndex);
          
          lastRandomIndex = randomIndex;
          setDisplayText(marketTerms[randomIndex]);
          lastUpdate = elapsed;
        }
        window.requestAnimationFrame(step);
      } else {
        setDisplayText(targetText);
      }
    };
    
    window.requestAnimationFrame(step);
  }, [targetText, duration]);

  return (
    <span className={displayText.includes("Bullish") ? "text-bullish" : "text-scramble"}>
      {displayText}
    </span>
  );
};

function DashboardPage() {
  // Dummy Data untuk Simulasi Backend
  const trendingCards = [
    { 
      id: 1, 
      name: "Pikachu EX", 
      rarity: "Shiny rare", 
      holo: "Reverse Holofoil",
      price: "$ 30.00", 
      image: "/card-result.png", // Ganti dengan path gambarmu
      setIcon: "/30th-celebration-logo.png", // Ganti dengan path logo set 30th celebration
      flagIcon: "🇬🇧" // Menggunakan emoji bendera untuk contoh (bisa diganti gambar bendera nanti)
    },
    { 
      id: 2, 
      name: "Mewtwo EX", 
      rarity: "Illustration rare", 
      holo: "Radiant Holofoil",
      price: "$ 45.00", 
      image: "/card-result.png", // Ganti dengan path gambarmu
      setIcon: "/ascended-heroes-logo.png", // Ganti dengan path logo set ascended
      flagIcon: "🇯🇵"
    },
    // ... Tambahkan 3 kartu lainnya dengan struktur yang sama ...
    { 
      id: 3, 
      name: "Umbreon EX", 
      rarity: "Shiny rare", 
      holo: "Normal Print",
      price: "$ 21.00", 
      image: "/card-result.png", // Ganti dengan path gambarmu
      setIcon: "/ascended-heroes-logo.png", // Ganti dengan path logo set ascended
      flagIcon: "🇬🇧"
    },
    { 
      id: 4, 
      name: "Sylveon EX", 
      rarity: "Promo", 
      holo: "Rare Holofoil",
      price: "$ 49.00", 
      image: "/card-result.png", // Ganti dengan path gambarmu
      setIcon: "/30th-celebration-logo.png", // Ganti dengan path logo set ascended
      flagIcon: "🇯🇵"
    },
  ];

  const rarityPriceData = [
    { rarity: "Shiny Ultra Rare", low: 25, mid: 30, high: 45 },
    { rarity: "Shiny Rare", low: 55, mid: 15, high: 30 },
    { rarity: "Mega Hyper Rare", low: 55, mid: 25, high: 20 },
    { rarity: "Hyper Rare", low: 65, mid: 25, high: 10 },
    { rarity: ". . .", low: 70, mid: 25, high: 5 },
  ];
  
  // Matriks nilai korelasi (rentang ~1000 hingga ~6000)
  const featureImpactData = [
    { feature: "Illustrator", impact: 78 },
    { feature: "Rarity", impact: 60 },
    { feature: "Release Year", impact: 45 },
    { feature: "HP", impact: 30 },
    { feature: "Card Type", impact: 25 },
    { feature: "Language", impact: 19 },
    { feature: "Condition", impact: 17 },
    { feature: "Set Number", impact: 16 },
    { feature: "Promo", impact: 13 },
    { feature: "Holo", impact: 9 },
    { feature: "Edition", impact: 2 }
  ];

  const rarityProduction = [
    { name: "Common", percent: 55, color: "#4b5e94" },   // Biru
    { name: "Uncommon", percent: 25, color: "#a0426b" }, // Ungu Tua
    { name: "Rare", percent: 15, color: "#e54c8c" },     // Pink
    { name: "Ultra rare", percent: 5, color: "#f2cf66" } // Kuning
  ];

  // DATA DUMMY: Line Chart (Tren Penjualan dari Jan 2021 - Jan 2025)
  const salesTrend = [
    { month: "Jan 2021", online: 12, retail: 10, event: 8 },
    { month: "Jul 2021", online: 13, retail: 11, event: 8.5 },
    { month: "Jan 2022", online: 14, retail: 12, event: 9 },
    { month: "Jul 2022", online: 14.5, retail: 14, event: 11 },
    { month: "Jan 2023", online: 15, retail: 16, event: 13 },
    { month: "Jul 2023", online: 16.5, retail: 16.5, event: 14 },
    { month: "Jan 2024", online: 18, retail: 17, event: 15 },
    { month: "Jul 2024", online: 21, retail: 18.5, event: 15.5 },
    { month: "Jan 2025", online: 24, retail: 20, event: 16 }
  ];

  // Fungsi Helper untuk menggambar titik koordinat pada SVG Line Chart
  const getSvgPath = (key) => {
    return salesTrend.map((d, i) => {
      const x = 40 + i * (660 / (salesTrend.length - 1)); // Menyebar X sepanjang 660px
      const y = 200 - (d[key] / 30) * 200; // Skala Y maksimum adalah 30
      return `${x},${y}`;
    }).join(" ");
  };

  return (
    <div className="market-dashboard-container">
      
      {/* 1. HEADER (KUNING) */}
      <div className="dashboard-hero-title">
        <h1 className="dashboard-title">Market Dashboard</h1>
        <p className="dashboard-subtitle">Real-time TCG market insights & trending values</p>
      </div>

      {/* 2. STATS BANNER (PITA PINK PENUH) */}
      <div className="dashboard-stats-banner">
        <div className="stat-banner-item">
          <span className="stat-banner-label">Total Scans Today</span>
          <span className="stat-banner-value">
            {/* 3. Ganti teks statis dengan AnimatedCounter */}
            <AnimatedCounter endValue={1452} duration={2000} />
          </span>
        </div>
        <div className="stat-banner-divider"></div>
        <div className="stat-banner-item">
          <span className="stat-banner-label">Highest Value Found</span>
          <span className="stat-banner-value">
            {/* 4. Gunakan prop isDecimal dan prefix untuk format uang */}
            <AnimatedCounter endValue={850.00} duration={2000} prefix="$ " isDecimal={true} />
          </span>
        </div>
        <div className="stat-banner-divider"></div>
        <div className="stat-banner-item">
          <span className="stat-banner-label">Active Market Trend</span>
          <span className="stat-banner-value">
            {/* Terapkan AnimatedTextScramble di sini */}
            <AnimatedTextScramble targetText="bullish ↗" duration={2000} />
          </span>
        </div>
      </div>

      {/* 3. TRENDING BANNER (PITA PUTIH PENUH) */}
      <div className="dashboard-trending-banner">
        <div className="trending-banner-content">
          <div className="trending-banner-title">
            Trending Cards<br />This Week :
          </div>
          <div className="trending-banner-cards">
            {trendingCards.map(card => (
              <div key={card.id} className="trending-card-row-item">
                <img src={card.image} alt={card.name} className="t-row-img" />
                
                {/* 2. STRUKTUR INFORMASI KARTU YANG BARU */}
                <div className="t-row-info">
                  <span className="t-row-name">{card.name}</span>
                  
                  <div className="t-row-rarity-group">
                    <span className="t-row-rarity">{card.rarity}</span>
                    <span className="t-row-holo">{card.holo}</span>
                  </div>
                  
                  <img src={card.setIcon} alt="Set Icon" className="t-row-set-icon" />
                  
                  <div className="t-row-flag-price">
                    <span className="t-row-flag">{card.flagIcon}</span>
                  </div>
                  
                  <span className="t-row-price">{card.price}</span>
                </div>

              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. KOTAK BAWAH (KEMBALI KE BACKGROUND KUNING) */}
      <div className="dashboard-bottom-area">
        <div className="dashboard-split-grid">
          
          {/* KOLOM KIRI */}
          <section className="widget-box left-box">
            {/* Legend (Keterangan Warna) */}
            <div className="chart-legend-header">
              <div className="legend-item">
                <span className="legend-dot color-low"></span> 
                <span className="legend-text">$ 0 - 10</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot color-mid"></span> 
                <span className="legend-text">$ 11 - 50</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot color-high"></span> 
                <span className="legend-text">$ &gt;50</span>
              </div>
            </div>

            {/* Area Grafik Batang */}
            <div className="bar-chart-container">
              {rarityPriceData.map((data, index) => (
                <div key={index} className="bar-row">
                  <span className="bar-label">{data.rarity}</span>
                  
                  {/* Track Batang */}
                  <div className="bar-track">
                    <div 
                      className="bar-segment color-low" 
                      style={{ width: `${data.low}%` }}
                    ></div>
                    <div 
                      className="bar-segment color-mid" 
                      style={{ width: `${data.mid}%` }}
                    ></div>
                    <div 
                      className="bar-segment color-high" 
                      style={{ width: `${data.high}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* KOLOM KANAN: HEATMAP */}
          <section className="widget-box right-box">
            <div className="feature-chart-wrapper">
              
              {/* Area Grafik Batang */}
              <div className="feature-bars-container">
                {featureImpactData.map((data, index) => (
                  <div key={index} className="f-bar-row">
                    <span className="f-bar-label">{data.feature}</span>
                    <div className="f-bar-track">
                      <div 
                        className="f-bar-fill" 
                        /* Menghitung persentase lebar berdasarkan nilai maksimum skala (80) */
                        style={{ width: `${(data.impact / 80) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Sumbu X (Angka di Bawah) */}
              <div className="f-x-axis">
                <div className="f-x-spacer"></div> {/* Ruang kosong sejajar dengan label kiri */}
                <div className="f-x-labels">
                  <span>0</span>
                  <span>20</span>
                  <span>40</span>
                  <span>60</span>
                  <span>80</span>
                </div>
              </div>

            </div>
          </section>

        </div>
        {/* BARIS KEDUA: GRID ASIMETRIS (Donut & Line Chart) */}
        <div className="dashboard-asymmetric-grid">
          
          {/* KOTAK KIRI K BAWAH: DONUT CHART */}
          <section className="widget-box left-box donut-box">
            <h2 className="section-title">Global Rarity Production</h2>
            <div className="donut-wrapper">
              
              {/* Teks Label Custom di Sekitar Donut */}
              <div className="donut-label dl-common">Common<br/>55%</div>
              <div className="donut-label dl-uncommon">Uncommon<br/>25%</div>
              <div className="donut-label dl-rare">Rare<br/>15%</div>
              <div className="donut-label dl-ultra">Ultra rare<br/>5%</div>

              <div className="donut-chart">
                <div className="donut-hole">
                  {/* Teks di tengah lubang (opsional, bisa dibiarkan kosong) */}
                </div>
              </div>
            </div>
          </section>

          {/* KOTAK KANAN BAWAH: LINE CHART */}
          <section className="widget-box right-box line-box">
            
            {/* Legend Line Chart */}
            <div className="chart-legend-header">
              <div className="legend-item"><span className="legend-dot" style={{backgroundColor: "#4b5e94"}}></span> <span className="legend-text">Online Sales</span></div>
              <div className="legend-item"><span className="legend-dot" style={{backgroundColor: "#e54c8c"}}></span> <span className="legend-text">Retail Stores</span></div>
              <div className="legend-item"><span className="legend-dot" style={{backgroundColor: "#f2cf66"}}></span> <span className="legend-text">Tournament Events</span></div>
            </div>

            {/* SVG Line Chart Builder */}
            <div className="line-chart-container">
              <svg viewBox="0 0 720 250" className="line-chart-svg">
                
                {/* Garis Grid Horizontal (Skala 0, 5, 10, ... 30) */}
                {[0, 5, 10, 15, 20, 25].map(val => {
                  const y = 200 - (val / 30) * 200;
                  return (
                    <g key={`grid-${val}`}>
                      <line x1="40" y1={y} x2="700" y2={y} stroke="#eee" strokeWidth="1" />
                      <text x="30" y={y + 4} fontSize="12" fill="#888" textAnchor="end" fontFamily="Montserrat">{val}</text>
                    </g>
                  );
                })}

                {/* Label Sumbu X (Bulan/Tahun) */}
                {salesTrend.map((d, i) => {
                  const x = 40 + i * (660 / (salesTrend.length - 1));
                  return (
                    <text key={`x-${i}`} x={x} y="230" fontSize="11" fill="#888" textAnchor="middle" fontFamily="Montserrat">{d.month}</text>
                  );
                })}

                {/* Garis Tren */}
                <polyline points={getSvgPath('online')} fill="none" stroke="#4b5e94" strokeWidth="3" />
                <polyline points={getSvgPath('retail')} fill="none" stroke="#e54c8c" strokeWidth="3" />
                <polyline points={getSvgPath('event')} fill="none" stroke="#f2cf66" strokeWidth="3" />

                {/* Titik Lingkaran di setiap Data */}
                {salesTrend.map((d, i) => {
                  const x = 40 + i * (660 / (salesTrend.length - 1));
                  return (
                    <g key={`dots-${i}`}>
                      <circle cx={x} cy={200 - (d.online / 30) * 200} r="4" fill="#4b5e94" />
                      <circle cx={x} cy={200 - (d.retail / 30) * 200} r="4" fill="#e54c8c" />
                      <circle cx={x} cy={200 - (d.event / 30) * 200} r="4" fill="#f2cf66" />
                    </g>
                  );
                })}
              </svg>
            </div>
          </section>
        
        </div>
        {/* BARIS KETIGA: GRID ASIMETRIS (Terbalik) */}
        <div className="dashboard-asymmetric-grid-reverse">
          
          {/* KOTAK KIRI BAWAH: TREEMAP CHART */}
          <section className="widget-box left-box treemap-box">
            {/* <h2 className="section-title">📦 Top Packs & Chase Cards</h2> */}
            
            <div className="treemap-container">
              {/* Kolom 1: 30th Celebration (Kuning) */}
              <div className="tm-group tm-yellow">
                <div className="tm-group-title">30th Celebration</div>
                <div className="tm-grid-2x2">
                  <div className="tm-cell">Mewtwo Ex</div>
                  <div className="tm-cell">Pikachu EX</div>
                  <div className="tm-cell">Mew Ex</div>
                  <div className="tm-cell">Pikachu Ex</div>
                </div>
              </div>

              {/* Kolom 2: Ascended heroes (Biru) */}
              <div className="tm-group tm-blue">
                <div className="tm-group-title">Ascended heroes</div>
                <div className="tm-grid-custom-blue">
                  <div className="tm-cell">Mega Gengar...</div>
                  <div className="tm-cell">Mega Dragon...</div>
                  <div className="tm-cell tm-span-full">Mega Charrizard Y Ex</div>
                </div>
              </div>

              {/* Kolom 3: Crimson haze (Ungu) */}
              <div className="tm-group tm-purple">
                <div className="tm-group-title">Crimson haze</div>
                <div className="tm-grid-stack">
                  <div className="tm-cell">Perrin</div>
                  <div className="tm-cell">Eevee</div>
                  <div className="tm-cell">Sinistcha Ex</div>
                </div>
              </div>

              {/* Kolom 4: Stacked (Pink & Navy) */}
              <div className="tm-group-split">
                <div className="tm-subgroup tm-pink">
                  <div className="tm-group-title">Twilight ma...</div>
                  <div className="tm-grid-custom-pink">
                    <div className="tm-cell">Greninj...</div>
                    <div className="tm-cell">Carmine</div>
                    <div className="tm-cell tm-span-full">Chansey</div>
                  </div>
                </div>
                <div className="tm-subgroup tm-navy">
                  <div className="tm-group-title">Other</div>
                  <div className="tm-cell">...</div>
                </div>
              </div>
            </div>
          </section>

          {/* KOTAK KANAN BAWAH: GAUGE CHART */}
          <section className="widget-box right-box gauge-box">
            <div className="gauge-container">
              {/* Setengah Lingkaran Background (Navy) */}
              <div className="gauge-background"></div>
              {/* Setengah Lingkaran Fill (Pink) yang diputar */}
              <div className="gauge-fill" style={{ transform: 'rotate(94deg)' }}></div> 
              {/* Penutup Tengah (Putih) untuk membuat bentuk cincin */}
              <div className="gauge-center">
                <span className="gauge-value">52%</span>
              </div>
            </div>
          </section>

        </div>
      </div>

    </div>
  );
}

export default DashboardPage;