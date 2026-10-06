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
  const [trendingCards, setTrendingCards] = useState([]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/dashboard');
        if (response.ok) {
          const data = await response.json();
          setTrendingCards(data.trending || []);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      }
    };
    fetchDashboardData();
  }, []);

  const topGainers = [
    { id: 1, name: "Umbreon VMAX (Alt Art)", oldPrice: "$400", newPrice: "$450", up: "+12.5%" },
    { id: 2, name: "Gengar VMAX (Alt Art)", oldPrice: "$180", newPrice: "$210", up: "+16.6%" },
    { id: 3, name: "Giratina V (Alt Art)", oldPrice: "$250", newPrice: "$275", up: "+10.0%" },
  ];

  const mostSearched = [
    { id: 1, name: "Mega Obstagoon VMAX", searches: "12,450x" },
    { id: 2, name: "Sylveon EX", searches: "9,230x" },
    { id: 3, name: "Lapras Illustration Rare", searches: "8,100x" },
  ];

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
            <h2 className="section-title">Top Price Gainers (7 Days)</h2>
            <div className="list-container">
              {topGainers.map((item, index) => (
                <div key={item.id} className="list-row">
                  <span className="rank-number">{index + 1}</span>
                  <div className="list-info-main">
                    <span className="item-name">{item.name}</span>
                    <span className="item-prices">{item.oldPrice} ➔ <strong>{item.newPrice}</strong></span>
                  </div>
                  <span className="up-badge">{item.up}</span>
                </div>
              ))}
            </div>
          </section>

          {/* KOLOM KANAN */}
          <section className="widget-box right-box">
            <h2 className="section-title">Most Searched Cards</h2>
            <div className="list-container">
              {mostSearched.map((item, index) => (
                <div key={item.id} className="list-row">
                  <span className="rank-number">{index + 1}</span>
                  <div className="list-info-main">
                    <span className="item-name">{item.name}</span>
                    <span className="item-sub">Searched {item.searches} this week</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>

    </div>
  );
}

export default DashboardPage;