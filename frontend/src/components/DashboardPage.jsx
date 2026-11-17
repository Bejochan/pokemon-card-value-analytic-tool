import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
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

const MARKET_TERMS = [
  "volatile", "bearish", "stagnant", "fluctuating", 
  "recovering", "correction", "rallying", "stable"
];

// Komponen baru untuk mengacak teks tren pasar
const AnimatedTextScramble = ({ targetText, duration }) => {
  const [displayText, setDisplayText] = useState("");

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
            randomIndex = Math.floor(Math.random() * MARKET_TERMS.length);
          } while (randomIndex === lastRandomIndex);
          
          lastRandomIndex = randomIndex;
          setDisplayText(MARKET_TERMS[randomIndex]);
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
  const [trendingCards, setTrendingCards] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [catalogSummary, setCatalogSummary] = useState({
    totalCards: 20617,
    totalSets: 172,
    marketStatus: "Active Database"
  });

  // Data Leaderboard Karakter Paling Bernilai (Temuan Riset Ilmiah The Charizard Tax)
  const [characterLeaderboard, setCharacterLeaderboard] = useState([
    { rank: 1, pokemon: "Rayquaza", medianUsd: 108.62, medianIdr: "Rp 1.792.230", sampleCount: 59, tag: "Grail Tier" },
    { rank: 2, pokemon: "Umbreon", medianUsd: 93.09, medianIdr: "Rp 1.535.902", sampleCount: 44, tag: "Moonbreon Tax" },
    { rank: 3, pokemon: "Gengar", medianUsd: 84.25, medianIdr: "Rp 1.390.125", sampleCount: 47, tag: "Ghost Favorite" },
    { rank: 4, pokemon: "Charizard", medianUsd: 71.49, medianIdr: "Rp 1.179.502", sampleCount: 106, tag: "Apex Collector" }
  ]);

  // Matriks Korelasi Riil Fitur terhadap Valuasi Pasar (Pearson, Cramer's V, & Eta-sq)
  const [featureImpactData, setFeatureImpactData] = useState([
    { feature: "Rarity Tier", impact: 48.3, label: "0.483 (Utama)" },
    { feature: "Release Year (Vintage)", impact: 31.1, label: "0.311" },
    { feature: "Set & Series Era", impact: 25.1, label: "0.251" },
    { feature: "Hit Points (HP)", impact: 23.4, label: "0.234" },
    { feature: "Illustrator / Artist", impact: 18.6, label: "0.186" },
    { feature: "Card Subtype", impact: 15.2, label: "0.152" },
    { feature: "Supertype (Pkm/Trn)", impact: 12.8, label: "0.128" },
    { feature: "Holo Foil Finish", impact: 9.4, label: "0.094" },
    { feature: "Set Card Number", impact: 4.1, label: "0.041" }
  ]);

  // Distribusi Kelangkaan Populasi Riil dari 20.617 Kartu
  const [rarityProduction, setRarityProduction] = useState([
    { name: "Common", percent: 26.2, count: "5.398 kartu", color: "#4b5e94" },
    { name: "Uncommon", percent: 23.7, count: "4.889 kartu", color: "#a0426b" },
    { name: "Rare & Holo", percent: 29.9, count: "6.156 kartu", color: "#e54c8c" },
    { name: "Ultra / Secret", percent: 12.7, count: "2.623 kartu", color: "#f2cf66" },
    { name: "Promo & Special", percent: 7.5, count: "1.551 kartu", color: "#00bcd4" }
  ]);

  // Indeks Nilai Rata-rata Pasar Berdasarkan Era Rilis Kartu (USD)
  const [eraTrendIndex, setEraTrendIndex] = useState([
    { year: "2020", vintage: 28.5, midEra: 19.0, modern: 5.1 },
    { year: "2021", vintage: 38.4, midEra: 25.2, modern: 7.9 },
    { year: "2022", vintage: 34.8, midEra: 22.9, modern: 6.8 },
    { year: "2023", vintage: 42.0, midEra: 25.9, modern: 7.4 },
    { year: "2024", vintage: 46.2, midEra: 29.5, modern: 8.2 },
    { year: "2025", vintage: 53.5, midEra: 33.7, modern: 9.2 },
    { year: "2026", vintage: 51.9, midEra: 32.7, modern: 10.3 }
  ]);

  // Pemetaan Ekspansi Resmi & Kartu Incaran Teratas
  const [chasePacks, setChasePacks] = useState([
    {
      set_id: "sv3pt5",
      title: "Pokemon 151",
      theme: "tm-yellow",
      layout: "tm-grid-2x2",
      cards: [
        { name: "Charizard ex", price: "$ 356.74" },
        { name: "Blastoise ex", price: "$ 132.13" },
        { name: "Venusaur ex", price: "$ 113.17" },
        { name: "Charmander", price: "$ 94.05" }
      ]
    },
    {
      set_id: "sv4pt5",
      title: "Paldean Fates",
      theme: "tm-blue",
      layout: "tm-grid-custom-blue",
      cards: [
        { name: "Mew ex", price: "$ 872.13" },
        { name: "Charizard ex", price: "$ 275.37" },
        { name: "Gardevoir ex", price: "$ 171.63", spanFull: true }
      ]
    },
    {
      set_id: "swsh7",
      title: "Evolving Skies",
      theme: "tm-purple",
      layout: "tm-grid-stack",
      cards: [
        { name: "Umbreon VMAX", price: "$ 2,283.14" },
        { name: "Rayquaza VMAX", price: "$ 1,255.44" },
        { name: "Dragonite V", price: "$ 523.47" }
      ]
    },
    {
      set_id: "base1",
      title: "Base Set 1999",
      theme: "tm-pink",
      layout: "tm-grid-custom-pink",
      cards: [
        { name: "Charizard", price: "$ 919.98" },
        { name: "Blastoise", price: "$ 229.70" },
        { name: "Venusaur", price: "$ 177.74", spanFull: true }
      ]
    }
  ]);

  // Indeks Likuiditas Pasar
  const [liquidity, setLiquidity] = useState({
    activeCards: 19686,
    totalCards: 20617,
    liquidityPct: 95.5,
    status: "HIGH LIQUIDITY"
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/dashboard`);
        if (response.ok) {
          const data = await response.json();
          setTrendingCards(data.trending || []);
          if (data.total_cards) {
            setCatalogSummary(prev => ({
              ...prev,
              totalCards: data.total_cards,
              totalSets: data.total_sets || prev.totalSets,
              marketStatus: "Active Database"
            }));
          }
          if (data.character_leaderboard && data.character_leaderboard.length > 0) {
            setCharacterLeaderboard(data.character_leaderboard);
          }
          if (data.feature_impact && data.feature_impact.length > 0) {
            setFeatureImpactData(data.feature_impact);
          }
          if (data.rarity_production && data.rarity_production.length > 0) {
            setRarityProduction(data.rarity_production);
          }
          if (data.era_trend_index && data.era_trend_index.length > 0) {
            setEraTrendIndex(data.era_trend_index);
          }
          if (data.chase_packs && data.chase_packs.length > 0) {
            setChasePacks(data.chase_packs);
          }
          if (data.liquidity) {
            setLiquidity({
              activeCards: data.liquidity.active_cards || 19686,
              totalCards: data.liquidity.total_cards || 20617,
              liquidityPct: data.liquidity.liquidity_pct || 95.5,
              status: data.liquidity.status || "HIGH LIQUIDITY"
            });
          }
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  // Fungsi Helper perhitungan koordinat dan kurva halus SVG Line Chart
  const getLineX = (i) => 60 + i * (600 / Math.max(1, eraTrendIndex.length - 1));
  const maxEraVal = Math.max(60, ...eraTrendIndex.map(d => Math.max(d.vintage || 0, d.midEra || 0, d.modern || 0)));
  const getLineY = (val) => 195 - (val / maxEraVal) * 160;

  const getSplinePath = (key) => {
    const points = eraTrendIndex.map((d, i) => ({
      x: getLineX(i),
      y: getLineY(d[key] || 0)
    }));
    if (points.length === 0) return "";
    let path = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cx1 = p0.x + (p1.x - p0.x) / 2;
      const cy1 = p0.y;
      const cx2 = p0.x + (p1.x - p0.x) / 2;
      const cy2 = p1.y;
      path += ` C ${cx1} ${cy1}, ${cx2} ${cy2}, ${p1.x} ${p1.y}`;
    }
    return path;
  };

  const getAreaPath = (key) => {
    const points = eraTrendIndex.map((d, i) => ({
      x: getLineX(i),
      y: getLineY(d[key] || 0)
    }));
    if (points.length === 0) return "";
    let path = getSplinePath(key);
    const lastX = points[points.length - 1].x;
    const firstX = points[0].x;
    const baseY = getLineY(0);
    path += ` L ${lastX} ${baseY} L ${firstX} ${baseY} Z`;
    return path;
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
          <span className="stat-banner-label">Total Verified Cards</span>
          <span className="stat-banner-value">
            <AnimatedCounter endValue={catalogSummary.totalCards} duration={1800} />
          </span>
        </div>
        <div className="stat-banner-divider"></div>
        <div className="stat-banner-item">
          <span className="stat-banner-label">Official Card Sets</span>
          <span className="stat-banner-value">
            <AnimatedCounter endValue={catalogSummary.totalSets} duration={1800} />
          </span>
        </div>
        <div className="stat-banner-divider"></div>
        <div className="stat-banner-item">
          <span className="stat-banner-label">Market Tracking</span>
          <span className="stat-banner-value">
            <AnimatedTextScramble targetText={catalogSummary.marketStatus} duration={1800} />
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
            {isLoading ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontStyle: 'italic', fontSize: '13px', width: '100%' }}>
                Memuat data katalog tren pasar...
              </div>
            ) : trendingCards.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '13px', width: '100%' }}>
                Data tren pasar belum tersedia.
              </div>
            ) : (
              trendingCards.map(card => (
              <div key={card.id} className="trending-card-row-item">
                <img src={card.image} alt={card.name} className="t-row-img" />
                
                {/* 2. STRUKTUR INFORMASI KARTU YANG BARU */}
                <div className="t-row-info">
                  <span className="t-row-name">{card.name}</span>
                  
                  <div className="t-row-rarity-group">
                    <span className="t-row-rarity">{card.rarity}</span>
                    <span className="t-row-holo">{card.holo}</span>
                  </div>
                  
                  <img 
                    src={card.setIcon} 
                    alt={card.name} 
                    className="t-row-set-icon"
                    onError={(e) => {
                      // Fallback otomatis ke CDN online resmi jika berkas lokal belum tersedia
                      const setId = card.card_id ? card.card_id.split('-')[0] : '';
                      if (setId && !e.target.dataset.triedCdn) {
                        e.target.dataset.triedCdn = 'true';
                        e.target.src = `https://images.pokemontcg.io/${setId}/logo.png`;
                      } else {
                        e.target.style.display = 'none';
                      }
                    }}
                  />
                  
                  <div className="t-row-flag-price">
                    <span className="t-row-flag">{card.flagIcon}</span>
                    {card.gain_pct && (
                      <span className="t-row-gain-pill">{card.gain_pct}</span>
                    )}
                  </div>
                  
                  <span className="t-row-price">{card.price}</span>
                </div>

              </div>
            ))
            )}
          </div>
        </div>
      </div>

      {/* 4. KOTAK BAWAH (KEMBALI KE BACKGROUND KUNING) */}
      <div className="dashboard-bottom-area">
        <div className="dashboard-split-grid">
          
          {/* KOLOM KIRI: LEADERBOARD KARAKTER & THE CHARIZARD TAX */}
          <section className="widget-box left-box leaderboard-box">
            <div className="widget-header-row">
              <h2 className="section-title">Character Valuation Premium</h2>
              <span className="widget-badge-pill">The Charizard Tax</span>
            </div>
            <p className="widget-intro-desc">
              Median harga karakter pasar tertinggi dibandingkan median pasar reguler ($1.03).
            </p>

            <div className="leaderboard-list">
              {characterLeaderboard.map((item) => (
                <div key={item.rank} className={`leaderboard-item rank-${item.rank}`}>
                  <div className="lb-rank-badge">#{item.rank}</div>
                  <div className="lb-info-col">
                    <div className="lb-name-row">
                      <span className="lb-pokemon-name">{item.pokemon}</span>
                      <span className="lb-tag">{item.tag}</span>
                    </div>
                    <div className="lb-bar-track">
                      <div 
                        className="lb-bar-fill" 
                        style={{ width: `${(item.medianUsd / 140) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="lb-price-col">
                    <span className="lb-price-usd">${item.medianUsd.toFixed(2)}</span>
                    <span className="lb-price-idr">{item.medianIdr}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* KOLOM KANAN: FEATURE IMPORTANCE */}
          <section className="widget-box right-box feature-box">
            <div className="widget-header-row">
              <h2 className="section-title">Market Value Feature Correlation</h2>
              <span className="widget-badge-pill">Pearson & Eta-sq</span>
            </div>
            <p className="widget-intro-desc">
              Tingkat korelasi atribut kartu terhadap estimasi harga pasar (Analisis 20.617 kartu).
            </p>

            <div className="feature-chart-wrapper">
              {/* Area Grafik Batang */}
              <div className="feature-bars-container">
                {featureImpactData.map((data, index) => (
                  <div key={index} className="f-bar-row">
                    <span className="f-bar-label" title={data.feature}>{data.feature}</span>
                    <div className="f-bar-track">
                      <div 
                        className="f-bar-fill" 
                        style={{ width: `${(data.impact / 55) * 100}%` }}
                      ></div>
                    </div>
                    <span className="f-bar-val">{data.label}</span>
                  </div>
                ))}
              </div>
              
              {/* Sumbu X (Angka di Bawah) */}
              <div className="f-x-axis">
                <div className="f-x-spacer"></div>
                <div className="f-x-labels">
                  <span>0.00</span>
                  <span>0.10</span>
                  <span>0.20</span>
                  <span>0.30</span>
                  <span>0.40</span>
                  <span>0.50</span>
                </div>
              </div>
            </div>
          </section>

        </div>
        {/* BARIS KEDUA: GRID ASIMETRIS (Semi-Circle Rarity Arc & Spline Line Chart) */}
        <div className="dashboard-asymmetric-grid">
          
          {/* KOTAK KIRI TENGAH: SEMI-CIRCLE RARITY ARC GAUGE */}
          <section className="widget-box left-box donut-box">
            <div className="widget-header-row">
              <h2 className="section-title">Global Rarity Production</h2>
              <span className="widget-badge-pill">Supabase DB</span>
            </div>
            <p className="widget-intro-desc">
              Distribusi kelangkaan 20.617 kartu Pokémon dalam database.
            </p>

            <div className="rarity-arc-container">
              {/* Semi-circle Multi-Segment SVG Gauge dinamis */}
              <div className="rarity-arc-visual">
                <svg viewBox="0 0 220 125" className="rarity-arc-svg">
                  {/* Track Belakang Halus */}
                  <path
                    d="M 30 105 A 80 80 0 0 1 190 105"
                    fill="none"
                    stroke="#f1f5f9"
                    strokeWidth="22"
                    strokeLinecap="round"
                  />
                  {/* Multi-Segment Dinamis Berdasarkan Populasi Database */}
                  {rarityProduction.map((item, idx, arr) => {
                    const dash = (item.percent / 100) * 251.3;
                    const currentOffset = -arr.slice(0, idx).reduce((sum, prev) => sum + (prev.percent / 100) * 251.3, 0);
                    return (
                      <path
                        key={idx}
                        d="M 30 105 A 80 80 0 0 1 190 105"
                        fill="none"
                        stroke={item.color}
                        strokeWidth="22"
                        strokeDasharray={`${dash.toFixed(1)} 251.3`}
                        strokeDashoffset={currentOffset.toFixed(1)}
                      />
                    );
                  })}
                </svg>

                <div className="rarity-arc-overlay">
                  <span className="rarity-arc-total">{catalogSummary.totalCards.toLocaleString('en-US')}</span>
                  <span className="rarity-arc-sub">TOTAL CARDS</span>
                </div>
              </div>

              {/* Sisi Kanan: Mini Progress Bar Card Per Kelangkaan */}
              <div className="rarity-progress-list">
                {rarityProduction.map((item, idx) => (
                  <div key={idx} className="rarity-progress-item">
                    <div className="rarity-progress-header">
                      <div className="rarity-name-group">
                        <span className="legend-color-dot" style={{ backgroundColor: item.color }}></span>
                        <span className="rarity-title-text">{item.name}</span>
                      </div>
                      <div className="rarity-stat-group">
                        <span className="rarity-count-text">{item.count}</span>
                        <span className="rarity-pct-badge" style={{ color: item.color }}>{item.percent}%</span>
                      </div>
                    </div>
                    <div className="rarity-bar-track">
                      <div className="rarity-bar-fill" style={{ width: `${item.percent}%`, backgroundColor: item.color }}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* KOTAK KANAN TENGAH: LINE CHART */}
          <section className="widget-box right-box line-box">
            <div className="widget-header-row">
              <h2 className="section-title">Era Release Value Index</h2>
              <span className="widget-badge-pill">Trend Index (USD)</span>
            </div>
            <p className="widget-intro-desc">
              Perbandingan tren rata-rata harga pasar berdasarkan era rilis.
            </p>

            {/* Legend Line Chart Horizontal */}
            <div className="chart-legend-header">
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: "#4b5e94" }}></span>
                <span className="legend-text">Vintage (1998-2003)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: "#e54c8c" }}></span>
                <span className="legend-text">Mid-Gen (2004-2015)</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: "#f2cf66" }}></span>
                <span className="legend-text">Modern (2016-2026)</span>
              </div>
            </div>

            {/* SVG Line Chart Builder */}
            <div className="line-chart-container">
              {/* Tooltip Mengambang Saat Hover Titik */}
              {hoveredPoint && (
                <div 
                  className="dashboard-chart-tooltip"
                  style={{
                    left: `${Math.min(90, Math.max(10, hoveredPoint.pctX))}%`,
                    top: `${hoveredPoint.pctY}%`
                  }}
                >
                  <div 
                    className="tooltip-era-badge" 
                    style={{ 
                      backgroundColor: hoveredPoint.eraColor,
                      color: hoveredPoint.eraKey === 'modern' ? '#1e1b4b' : '#ffffff'
                    }}
                  >
                    {hoveredPoint.eraLabel}
                  </div>
                  <div className="tooltip-year-text">Tahun {hoveredPoint.year}</div>
                  <div className="tooltip-price-row">
                    <span className="tooltip-price-usd">${hoveredPoint.priceUsd.toFixed(2)}</span>
                    <span className="tooltip-price-idr"> (Rp {hoveredPoint.priceIdr.toLocaleString('id-ID')})</span>
                  </div>
                </div>
              )}

              <svg viewBox="0 0 720 250" className="line-chart-svg">
                <defs>
                  <linearGradient id="areaVintage" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#4b5e94" stopOpacity="0.16" />
                    <stop offset="100%" stopColor="#4b5e94" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="areaMidEra" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#e54c8c" stopOpacity="0.14" />
                    <stop offset="100%" stopColor="#e54c8c" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="areaModern" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#f2cf66" stopOpacity="0.16" />
                    <stop offset="100%" stopColor="#f2cf66" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Garis Grid Horizontal (Skala $0, $15, $30, $45, $60) */}
                {[0, 15, 30, 45, 60].map(val => {
                  const y = getLineY(val);
                  return (
                    <g key={`grid-${val}`}>
                      <line x1="45" y1={y} x2="700" y2={y} stroke="#f1f5f9" strokeWidth="1.2" />
                      <text x="36" y={y + 4} fontSize="11" fill="#94a3b8" textAnchor="end" fontFamily="Montserrat" fontWeight="500">${val}</text>
                    </g>
                  );
                })}

                {/* Garis Vertikal Indikator Saat Titik Di-hover */}
                {hoveredPoint && (
                  <line
                    x1={hoveredPoint.x}
                    y1="25"
                    x2={hoveredPoint.x}
                    y2="200"
                    stroke="#cbd5e1"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                    opacity="0.8"
                    pointerEvents="none"
                  />
                )}

                {/* Label Sumbu X (Tahun) */}
                {eraTrendIndex.map((d, i) => {
                  const x = getLineX(i);
                  return (
                    <text key={`x-${i}`} x={x} y="232" fontSize="12" fill="#64748b" textAnchor="middle" fontFamily="Montserrat" fontWeight="600">{d.year}</text>
                  );
                })}

                {/* Area Fills under Spline Curves */}
                <path d={getAreaPath('vintage')} fill="url(#areaVintage)" />
                <path d={getAreaPath('midEra')} fill="url(#areaMidEra)" />
                <path d={getAreaPath('modern')} fill="url(#areaModern)" />

                {/* Smooth Spline Lines */}
                <path d={getSplinePath('vintage')} fill="none" stroke="#4b5e94" strokeWidth="3" strokeLinecap="round" />
                <path d={getSplinePath('midEra')} fill="none" stroke="#e54c8c" strokeWidth="3" strokeLinecap="round" />
                <path d={getSplinePath('modern')} fill="none" stroke="#f2cf66" strokeWidth="3" strokeLinecap="round" />

                {/* Titik Lingkaran Tepat di Koordinat Kurva dengan Hover Interaktif */}
                {eraTrendIndex.map((d, i) => {
                  const x = getLineX(i);
                  const eras = [
                    { key: 'vintage', label: 'Vintage (1998-2003)', color: '#4b5e94', val: d.vintage },
                    { key: 'midEra', label: 'Mid-Gen (2004-2015)', color: '#e54c8c', val: d.midEra },
                    { key: 'modern', label: 'Modern (2016-2026)', color: '#f2cf66', val: d.modern }
                  ];

                  return (
                    <g key={`dots-group-${i}`}>
                      {eras.map(era => {
                        const y = getLineY(era.val || 0);
                        const isHovered = hoveredPoint && hoveredPoint.year === d.year && hoveredPoint.eraKey === era.key;
                        return (
                          <g key={`${era.key}-${i}`}>
                            {/* Halo Lingkaran Saat Titik Aktif Di-hover */}
                            {isHovered && (
                              <circle
                                cx={x}
                                cy={y}
                                r="12"
                                fill="none"
                                stroke={era.color}
                                strokeWidth="2.5"
                                opacity="0.6"
                              />
                            )}
                            {/* Lingkaran Visual Utama */}
                            <circle
                              cx={x}
                              cy={y}
                              r={isHovered ? 7.5 : 5}
                              fill={era.color}
                              stroke="#ffffff"
                              strokeWidth={isHovered ? 3 : 2.5}
                              style={{ transition: 'all 0.15s ease' }}
                            />
                            {/* Area Sentuh Lebar Transparan untuk Kemudahan Hover Cursor */}
                            <circle
                              cx={x}
                              cy={y}
                              r="15"
                              fill="transparent"
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredPoint({
                                x,
                                y,
                                pctX: (x / 720) * 100,
                                pctY: (y / 250) * 100,
                                year: d.year,
                                eraKey: era.key,
                                eraLabel: era.label,
                                eraColor: era.color,
                                priceUsd: Number(era.val || 0),
                                priceIdr: Math.round(Number(era.val || 0) * 16500)
                              })}
                              onMouseLeave={() => setHoveredPoint(null)}
                            />
                          </g>
                        );
                      })}
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
            <div className="widget-header-row">
              <h2 className="section-title">Top Packs & Official Chase Cards</h2>
              <span className="widget-badge-pill">Hot Expansions</span>
            </div>
            <p className="widget-intro-desc">
              Pemetaan ekspansi resmi dan kartu incaran bernilai tertinggi.
            </p>
            
            <div className="treemap-container">
              {chasePacks.map((pack, pIdx) => (
                <div key={pack.set_id || pIdx} className={`tm-group ${pack.theme}`}>
                  <div className="tm-group-title">{pack.title}</div>
                  <div className={pack.layout || "tm-grid-2x2"}>
                    {pack.cards.map((c, cIdx) => (
                      <div key={cIdx} className={`tm-cell ${c.spanFull ? 'tm-span-full' : ''}`}>
                        <span>{c.name}</span>
                        <span className="tm-price">{c.price}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* KOTAK KANAN BAWAH: GAUGE CHART */}
          <section className="widget-box right-box gauge-box">
            <div className="widget-header-row">
              <h2 className="section-title">Market Liquidity Index</h2>
              <span className="widget-badge-pill">Health Score</span>
            </div>
            <p className="widget-intro-desc">
              Persentase perputaran transaksi kartu dalam 30 hari terakhir.
            </p>

            <div className="gauge-visual-container">
              <svg viewBox="0 0 220 125" className="gauge-svg">
                <defs>
                  <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#4b5e94" />
                    <stop offset="50%" stopColor="#a0426b" />
                    <stop offset="100%" stopColor="#e83e8c" />
                  </linearGradient>
                </defs>
                {/* Background Arc: Center (110, 105), Radius 80 */}
                <path
                  d="M 30 105 A 80 80 0 0 1 190 105"
                  fill="none"
                  stroke="#f1f5f9"
                  strokeWidth="22"
                  strokeLinecap="round"
                />
                {/* Active Arc Dinamis (Berdasarkan Liquidity Pct) */}
                <path
                  d="M 30 105 A 80 80 0 0 1 190 105"
                  fill="none"
                  stroke="url(#gaugeGradient)"
                  strokeWidth="22"
                  strokeLinecap="round"
                  strokeDasharray="251.3"
                  strokeDashoffset={Math.max(0, 251.3 - (liquidity.liquidityPct / 100) * 251.3).toFixed(1)}
                />
              </svg>

              <div className="gauge-value-overlay">
                <span className="gauge-big-number">{liquidity.liquidityPct}%</span>
                <span className="gauge-status-badge">{liquidity.status}</span>
              </div>
            </div>

            <div className="gauge-metric-footer">
              <div className="gauge-stat-pill">
                <strong>{liquidity.activeCards.toLocaleString('id-ID')}</strong> / {liquidity.totalCards.toLocaleString('id-ID')} Kartu Aktif
              </div>
              <span className="gauge-stat-sub">Aktivitas Transaksi Pasar (Dataset Master Regokemon)</span>
            </div>
          </section>

        </div>
      </div>

    </div>
  );
}

export default DashboardPage;