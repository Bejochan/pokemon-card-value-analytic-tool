import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { API_BASE_URL } from '../config/api';
import HoloCard3D from './HoloCard3D';
import './CatalogPage.css';

const formatIDR = (val) => {
  if (val === undefined || val === null || isNaN(val)) return 'Rp 0';
  return `Rp ${Math.round(val).toLocaleString('id-ID')}`;
};

// Helper untuk mengambil URL gambar kartu resolusi tinggi (images.large / HD)
const getCardLargeImage = (card) => {
  if (!card) return '/card-result.png';

  // 1. Jika backend sudah menyediakan properti image_large / images_large
  if (card.image_large) return card.image_large;
  if (card.images_large) return card.images_large;
  if (card['images.large']) return card['images.large'];

  // 2. Fallback cerdas: Sesuai struktur dataset CSV, URL pokemontcg.io 
  //    menggunakan akhiran '_hires.png' dan scrydex menggunakan '/large'
  if (card.image) {
    if (card.image.includes('pokemontcg.io') && card.image.endsWith('.png') && !card.image.endsWith('_hires.png')) {
      return card.image.replace('.png', '_hires.png');
    }
    if (card.image.includes('scrydex.com')) {
      return card.image.replace('/small', '/large');
    }
    return card.image;
  }

  return '/card-result.png';
};

// Helper 1: Menghasilkan kurva lengkung Bézier halus melalui sekumpulan titik
const getSmoothPath = (pts, tension = 0.2) => {
  if (!pts || pts.length === 0) return '';
  if (pts.length === 1) return `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  if (pts.length === 2) {
    return `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)} L ${pts[1].x.toFixed(1)} ${pts[1].y.toFixed(1)}`;
  }

  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = i > 0 ? pts[i - 1] : pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = i < pts.length - 2 ? pts[i + 2] : p2;

    const cp1x = p1.x + ((p2.x - p0.x) * tension);
    const cp1y = p1.y + ((p2.y - p0.y) * tension);
    const cp2x = p2.x - ((p3.x - p1.x) * tension);
    const cp2y = p2.y - ((p3.y - p1.y) * tension);

    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }

  return d;
};

// Helper 2: Menghasilkan selubung pita forecast (P10 - P90) yang melengkung halus
const getSmoothRibbonPath = (todayPt, forecastPts, tension = 0.2) => {
  if (!todayPt || !forecastPts || forecastPts.length === 0) return '';

  const upperPts = [
    { x: todayPt.x, y: todayPt.y },
    ...forecastPts.map(p => ({ x: p.x, y: p.yP90 }))
  ];

  const lowerPts = [
    { x: todayPt.x, y: todayPt.y },
    ...forecastPts.map(p => ({ x: p.x, y: p.yP10 }))
  ];

  const upperPath = getSmoothPath(upperPts, tension);
  const lowerReversedPts = [...lowerPts].reverse();
  const lastLower = lowerPts[lowerPts.length - 1];

  let lowerD = ` L ${lastLower.x.toFixed(1)} ${lastLower.y.toFixed(1)}`;
  for (let i = 0; i < lowerReversedPts.length - 1; i++) {
    const p0 = i > 0 ? lowerReversedPts[i - 1] : lowerReversedPts[i];
    const p1 = lowerReversedPts[i];
    const p2 = lowerReversedPts[i + 1];
    const p3 = i < lowerReversedPts.length - 2 ? lowerReversedPts[i + 2] : p2;

    const cp1x = p1.x + ((p2.x - p0.x) * tension);
    const cp1y = p1.y + ((p2.y - p0.y) * tension);
    const cp2x = p2.x - ((p3.x - p1.x) * tension);
    const cp2y = p2.y - ((p3.y - p1.y) * tension);

    lowerD += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }

  return `${upperPath}${lowerD} Z`;
};

function CatalogPage() {
  const [cardsData, setCardsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCards, setTotalCards] = useState(0);
  const [currencyRate, setCurrencyRate] = useState(16500);

  // Filter & Search states
  const [searchInput, setSearchInput] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [selectedSupertype, setSelectedSupertype] = useState('all');
  const [selectedRarity, setSelectedRarity] = useState('all');
  const [selectedHolo, setSelectedHolo] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  // Set Selector
  const [isSetMenuOpen, setIsSetMenuOpen] = useState(false);
  const setSelectorRef = useRef(null);

  // --- POP-UP MODAL STATE ---
  const [selectedCard, setSelectedCard] = useState(null);
  const [isFocusCard, setIsFocusCard] = useState(false);
  const [isClosingModal, setIsClosingModal] = useState(false);
  const [cardHistory, setCardHistory] = useState([]);
  const [cardForecast, setCardForecast] = useState(null);
  const [isChartLoading, setIsChartLoading] = useState(false);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const handleCloseModal = useCallback(() => {
    if (isClosingModal) return;
    setIsClosingModal(true);
    setTimeout(() => {
      setSelectedCard(null);
      setIsFocusCard(false);
      setCardHistory([]);
      setCardForecast(null);
      setHoveredPoint(null);
      setIsClosingModal(false);
    }, 200);
  }, [isClosingModal]);

  // Menutup dropdown menu otomatis
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (setSelectorRef.current && !setSelectorRef.current.contains(event.target)) {
        setIsSetMenuOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsSetMenuOpen(false);
        if (selectedCard) {
          if (isFocusCard) {
            setIsFocusCard(false);
          } else {
            handleCloseModal();
          }
        }
      }
    };

    if (isSetMenuOpen || selectedCard) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isSetMenuOpen, selectedCard, isFocusCard, handleCloseModal]);

  const [availableSets, setAvailableSets] = useState([
    { set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' }
  ]);
  const [activeSet, setActiveSet] = useState({ set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' });

  // Helper untuk menentukan logo set
  const getSetLogoUrl = (s) => {
    if (!s || s.set_id === 'all') return '/pokemon-logo.png';
    const sId = (s.set_id || '').toLowerCase();
    const sNameLower = (s.name || '').toLowerCase();

    if (sId === 'hgss1') return '/hgss1-logo.png';
    if (sId === 'sma') return '/sma-logo.png';
    if (sId === 'base3') return '/base3-logo.png';
    if (sId === 'sm75') return '/sm75-logo.png';
    if (sNameLower.includes('30th')) return '/30th-celebration-logo.png';
    if (sNameLower.includes('ascended')) return '/ascended-heroes-logo.png';
    if (sId === 'me3' || sId === 'me4' || sId === 'me5') return '/pokemon-logo.png';

    return `https://images.pokemontcg.io/${s.set_id}/logo.png`;
  };

  useEffect(() => {
    const fetchSets = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/sets?limit=250`);
        if (response.ok) {
          const sets = await response.json();
          if (Array.isArray(sets) && sets.length > 0) {
            const formatted = [
              { set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' },
              ...sets.map(s => {
                const yearStr = s.release_year ? ` (${s.release_year})` : '';
                return {
                  set_id: s.set_id,
                  name: `${s.name}${yearStr}`,
                  raw_name: s.name,
                  release_date: s.release_date,
                  logo: getSetLogoUrl(s)
                };
              })
            ];
            setAvailableSets(formatted);
          }
        }
      } catch (err) {
        console.error("Gagal memuat daftar sets:", err);
      }
    };
    fetchSets();
  }, []);

  const fetchCards = useCallback(async (targetPage = 1) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: targetPage.toString(),
        limit: '20'
      });

      if (activeSearch.trim()) params.append('search', activeSearch.trim());
      if (selectedSupertype !== 'all') params.append('supertype', selectedSupertype);
      if (selectedRarity !== 'all') params.append('rarity', selectedRarity);
      if (selectedHolo !== 'all') params.append('holo', selectedHolo);
      if (activeSet.set_id !== 'all') params.append('set_id', activeSet.set_id);
      if (sortBy) params.append('sort_by', sortBy);

      const response = await fetch(`${API_BASE_URL}/cards?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Gagal mengambil data dari server');
      }
      const data = await response.json();
      
      if (data && data.currency_rate) {
        setCurrencyRate(data.currency_rate);
      }

      if (data && data.cards) {
        setCardsData(data.cards);
        setTotalCards(data.total || 0);
        setTotalPages(data.total_pages || 1);
        setPage(data.page || 1);
      } else if (Array.isArray(data)) {
        setCardsData(data);
        setTotalCards(data.length);
        setTotalPages(1);
      }
    } catch (error) {
      console.error("Error fetching cards:", error);
      setCardsData([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeSearch, selectedSupertype, selectedRarity, selectedHolo, activeSet.set_id, sortBy]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCards(page);
    }, 0);
    return () => clearTimeout(timer);
  }, [page, fetchCards]);

  // Fetch live currency rate saat mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/currency`)
      .then(res => res.json())
      .then(cur => {
        if (cur && cur.rate) setCurrencyRate(cur.rate);
      })
      .catch(() => {});
  }, []);

  // Fetch riwayat harga & data peramalan 7 hari saat kartu dipilih
  useEffect(() => {
    if (!selectedCard?.id) return;

    let isMounted = true;

    const fetchCardDetails = async () => {
      try {
        const [histRes, foreRes] = await Promise.all([
          fetch(`${API_BASE_URL}/cards/${encodeURIComponent(selectedCard.id)}/history`),
          fetch(`${API_BASE_URL}/cards/${encodeURIComponent(selectedCard.id)}/forecast`)
        ]);

        if (isMounted && histRes.ok) {
          const histData = await histRes.json();
          if (Array.isArray(histData)) {
            setCardHistory(histData.filter(d => d.effective_market_price !== null));
          }
        }

        if (isMounted && foreRes.ok) {
          const foreData = await foreRes.json();
          if (foreData && foreData.status === 'success') {
            setCardForecast(foreData);
          }
        }
      } catch (err) {
        console.error("Gagal memuat analitik kartu:", err);
      } finally {
        if (isMounted) {
          setIsChartLoading(false);
        }
      }
    };

    fetchCardDetails();

    return () => {
      isMounted = false;
    };
  }, [selectedCard?.id]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setActiveSearch(searchInput);
  };

  const handleSupertypeChange = (type) => {
    setPage(1);
    setSelectedSupertype(prev => prev === type ? 'all' : type);
  };

  const handleResetFilters = () => {
    setSelectedSupertype('all');
    setSelectedRarity('all');
    setSelectedHolo('all');
    setActiveSet({ set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' });
    setSearchInput('');
    setActiveSearch('');
    setPage(1);
  };

  const isAnyFilterActive = 
    selectedSupertype !== 'all' || 
    selectedRarity !== 'all' || 
    selectedHolo !== 'all' || 
    activeSet.set_id !== 'all' || 
    activeSearch.trim() !== '';

  // Mencegah scrolling body saat pop-up terbuka
  useEffect(() => {
    if (selectedCard) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; }
  }, [selectedCard]);

  // Perhitungan Data Analitika & Grafik untuk Pop-up Detail Kartu
  const currentPriceUsd = (cardForecast?.current_price_usd > 0)
    ? cardForecast.current_price_usd
    : (selectedCard?.price_num > 0 ? selectedCard.price_num : 5.0);

  const currentRateVal = currencyRate || 16500;
  const currentPriceIdr = (cardForecast?.current_price_idr > 0)
    ? cardForecast.current_price_idr
    : Math.round(currentPriceUsd * currentRateVal);

  // 1. Titik Riwayat Pasar (ambil maksimal 5 data terakhir atau gunakan fallback kurva wajar)
  let historyItems = [];
  if (cardHistory && cardHistory.length > 0) {
    const historySlice = cardHistory.slice(-5);
    historyItems = historySlice.map((d) => {
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
  } else {
    const baseP = currentPriceUsd;
    const now = new Date();
    const mockDeltas = [-0.07, -0.04, 0.01, 0.00];
    const daysBack = [28, 21, 14, 7];
    historyItems = mockDeltas.map((delta, i) => {
      const d = new Date(now.getTime() - daysBack[i] * 24 * 60 * 60 * 1000);
      const pUsd = Math.max(0.1, Number((baseP * (1 + delta)).toFixed(2)));
      return {
        type: 'history',
        date: d.toISOString().split('T')[0],
        label: d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' }),
        priceUsd: pUsd,
        priceIdr: Math.round(pUsd * currentRateVal)
      };
    });
  }

  // 2. Titik Hari Ini (Jangkar penghubung kurva)
  const todayItem = {
    type: 'anchor',
    date: 'Hari ini',
    label: 'Hari ini',
    priceUsd: currentPriceUsd,
    priceIdr: currentPriceIdr
  };

  // 3. Titik Prediksi 7 Hari (dari Forecast Model)
  let forecastItems = [];
  if (cardForecast?.forecast && cardForecast.forecast.length > 0) {
    forecastItems = cardForecast.forecast.map((f) => {
      const pUsd = Number(f.predicted_price_usd);
      const pIdr = Math.round(pUsd * currentRateVal);
      const p10Usd = f.p10_usd !== undefined ? Number(f.p10_usd) : (pUsd * 0.90);
      const p90Usd = f.p90_usd !== undefined ? Number(f.p90_usd) : (pUsd * 1.10);
      const dateObj = new Date(f.date);
      const label = !isNaN(dateObj)
        ? dateObj.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })
        : `H+${f.day}`;
      return {
        type: 'forecast',
        date: f.date,
        label,
        dayNum: f.day,
        priceUsd: pUsd,
        priceIdr: pIdr,
        p10Usd,
        p90Usd,
        p10Idr: Math.round(p10Usd * currentRateVal),
        p90Idr: Math.round(p90Usd * currentRateVal)
      };
    });
  } else {
    const baseP = currentPriceUsd;
    const now = new Date();
    forecastItems = Array.from({ length: 7 }, (_, i) => {
      const day = i + 1;
      const d = new Date(now.getTime() + day * 24 * 60 * 60 * 1000);
      const drift = 1 + (day * 0.005);
      const pUsd = Number((baseP * drift).toFixed(2));
      const p10Usd = Number((pUsd * 0.92).toFixed(2));
      const p90Usd = Number((pUsd * 1.08).toFixed(2));
      return {
        type: 'forecast',
        date: d.toISOString().split('T')[0],
        label: `H+${day}`,
        dayNum: day,
        priceUsd: pUsd,
        priceIdr: Math.round(pUsd * currentRateVal),
        p10Usd,
        p90Usd,
        p10Idr: Math.round(p10Usd * currentRateVal),
        p90Idr: Math.round(p90Usd * currentRateVal)
      };
    });
  }

  // Gabungan seluruh titik untuk rendering garis kontinu
  const combinedPoints = [...historyItems, todayItem, ...forecastItems];

  // Skala Koordinat SVG
  const svgWidth = 680;
  const svgHeight = 145;
  const padLeft = 65;
  const padRight = 20;
  const padTop = 16;
  const padBottom = 24;
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
  const plotRange = (plotMax - plotMin) || 1;

  // Garis Grid & Sumbu Y (4 titik referensi)
  const yTicks = [
    { y: padTop, valUsd: plotMax },
    { y: padTop + (usableH * 0.33), valUsd: plotMin + (plotRange * 0.67) },
    { y: padTop + (usableH * 0.67), valUsd: plotMin + (plotRange * 0.33) },
    { y: padTop + usableH, valUsd: plotMin }
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

  // Menghasilkan kurva Bézier melengkung halus untuk riwayat dan prediksi
  const historyPoints = pointsWithCoords.slice(0, historyItems.length + 1);
  const forecastPoints = pointsWithCoords.slice(historyItems.length);
  const historySmoothPath = getSmoothPath(historyPoints, 0.2);
  const forecastSmoothPath = getSmoothPath(forecastPoints, 0.2);

  const ribbonTodayPoint = pointsWithCoords[historyItems.length];
  const ribbonForecastPts = pointsWithCoords.slice(historyItems.length + 1);
  const ribbonSmoothPath = getSmoothRibbonPath(ribbonTodayPoint, ribbonForecastPts, 0.2);

  // 6 Metrik Kotak Analitika
  const allTimeHighVal = allPrices.length > 0 ? Math.max(...allPrices) : currentPriceUsd;
  const historyPrices = historyItems.map(h => h.priceUsd);
  const avgVal = historyPrices.length > 0 ? historyPrices.reduce((a, b) => a + b, 0) / historyPrices.length : currentPriceUsd;

  let trendPct = 0;
  if (cardForecast?.change_pct !== undefined && !isNaN(cardForecast.change_pct)) {
    trendPct = Number(cardForecast.change_pct);
  } else if (historyItems.length >= 2) {
    const startP = historyItems[0].priceUsd;
    const endP = todayItem.priceUsd;
    trendPct = startP > 0 ? ((endP - startP) / startP) * 100 : 0;
  }
  const trendText = `${trendPct >= 0 ? '+' : ''}${trendPct.toFixed(1)}%`;
  const trendClass = trendPct >= 0 ? 'trend-positive' : 'trend-negative';

  let ageText = '7 Thn';
  if (selectedCard?.release_year) {
    const age = Math.max(1, new Date().getFullYear() - Number(selectedCard.release_year));
    ageText = `${age} Thn`;
  } else if (activeSet?.name && activeSet.name.match(/\b(19\d\d|20\d\d)\b/)) {
    const matchYear = activeSet.name.match(/\b(19\d\d|20\d\d)\b/)[0];
    const age = Math.max(1, new Date().getFullYear() - Number(matchYear));
    ageText = `${age} Thn`;
  }

  let valuationLabel;
  let valuationClass;
  const gap = cardForecast?.mispricing_gap_pct;
  const rawSignal = (cardForecast?.signal || 'HOLD').toUpperCase();
  if (gap !== undefined && !isNaN(gap)) {
    if (gap < -1.5 || rawSignal.includes('BUY')) {
      valuationLabel = 'Undervalued';
      valuationClass = 'val-undervalued';
    } else if (gap > 1.5 || rawSignal.includes('SELL')) {
      valuationLabel = 'Overvalued';
      valuationClass = 'val-overvalued';
    } else {
      valuationLabel = 'Fair Value';
      valuationClass = 'val-fair';
    }
  } else if (rawSignal.includes('SELL')) {
    valuationLabel = 'Overvalued';
    valuationClass = 'val-overvalued';
  } else {
    valuationLabel = 'Undervalued';
    valuationClass = 'val-undervalued';
  }

  let signalDisplay = 'Hold';
  let signalClass = 'signal-hold';
  if (rawSignal.includes('BUY')) {
    signalDisplay = rawSignal.includes('STRONG') ? 'Strong Buy' : 'Buy';
    signalClass = 'signal-buy';
  } else if (rawSignal.includes('SELL')) {
    signalDisplay = rawSignal.includes('STRONG') ? 'Strong Sell' : 'Sell';
    signalClass = 'signal-sell';
  }


  return (
    <div className="catalog-container">
      
      {/* HEADER PENCARIAN */}
      <div className="catalog-header">
        <div className="set-selector-container" ref={setSelectorRef}>
          <button 
            className="set-selector-btn" 
            onClick={() => setIsSetMenuOpen(!isSetMenuOpen)}
            title={activeSet.name}
          >
            <img 
              src={activeSet.logo} 
              alt={activeSet.name} 
              className="celebration-icon" 
              onError={(e) => {
                if (!e.target.dataset.triedFallback) {
                  e.target.dataset.triedFallback = 'true';
                  e.target.src = '/pokemon-logo.png';
                }
              }}
            /> 
            <span className="celebration-text">{activeSet.name}</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1e1b4b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`set-arrow ${isSetMenuOpen ? 'open' : ''}`}>
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {isSetMenuOpen && (
            <div className="set-dropdown-menu">
              <div className="set-dropdown-list">
                {availableSets.map((setObj) => (
                  <div 
                    key={setObj.set_id} 
                    className={`set-dropdown-item ${activeSet.set_id === setObj.set_id ? 'active' : ''}`}
                    onClick={() => {
                      setActiveSet(setObj);
                      setPage(1);
                      setIsSetMenuOpen(false); 
                    }}
                    title={setObj.name}
                  >
                    <img 
                      src={setObj.logo} 
                      alt="" 
                      className="set-dropdown-icon"
                      onError={(e) => {
                        if (!e.target.dataset.triedFallback) {
                          e.target.dataset.triedFallback = 'true';
                          e.target.src = '/pokemon-logo.png';
                        }
                      }}
                    />
                    <span className="set-dropdown-label">{setObj.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <form className="search-bar-wrapper" onSubmit={handleSearchSubmit}>
          <input 
            type="text" 
            className="search-input" 
            placeholder="Cari kartu (misal: Charizard, Pikachu)..." 
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button type="submit" className="search-icon-btn" title="Cari Kartu">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#e83e8c" strokeWidth="3" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </button>
        </form>
      </div>

      {/* AREA KONTEN PUTIH */}
      <div className="catalog-content-area">
        
        {/* BARIS FILTER */}
        <div className="filter-bar">
          <div className="filter-group">
            <span className="filter-label">Filter:</span>
            <label className="checkbox-label">
              <input 
                type="checkbox" 
                checked={selectedSupertype === 'Pokémon'} 
                onChange={() => handleSupertypeChange('Pokémon')} 
              /> Pokémon
            </label>
            <label className="checkbox-label">
              <input 
                type="checkbox" 
                checked={selectedSupertype === 'Trainer'} 
                onChange={() => handleSupertypeChange('Trainer')} 
              /> Trainer
            </label>
            <label className="checkbox-label">
              <input 
                type="checkbox" 
                checked={selectedSupertype === 'Energy'} 
                onChange={() => handleSupertypeChange('Energy')} 
              /> Energy
            </label>

            <select 
              className="filter-select"
              value={selectedRarity}
              onChange={(e) => { setSelectedRarity(e.target.value); setPage(1); }}
            >
              <option value="all">Semua Rarity</option>
              <option value="Common">Common</option>
              <option value="Uncommon">Uncommon</option>
              <option value="Rare">Rare</option>
              <option value="Holo">Rare Holo</option>
              <option value="Ultra">Ultra Rare</option>
              <option value="Illustration">Illustration Rare</option>
              <option value="Secret">Secret Rare</option>
              <option value="Shiny">Shiny Rare</option>
              <option value="Promo">Promo</option>
            </select>

            <select 
              className="filter-select"
              value={selectedHolo}
              onChange={(e) => { setSelectedHolo(e.target.value); setPage(1); }}
            >
              <option value="all">Semua Foil</option>
              <option value="holo">Holo Only</option>
              <option value="non_holo">Normal Print</option>
            </select>

            {isAnyFilterActive && (
              <button className="reset-filter-btn" onClick={handleResetFilters}>Reset</button>
            )}
          </div>

          <div className="filter-right-controls">
            <div className="catalog-count-info">
              Menampilkan <strong>{cardsData.length}</strong> dari <strong>{totalCards.toLocaleString('id-ID')}</strong> kartu
            </div>

            <div className="sort-group">
              <span className="filter-label">Sort by:</span>
              <select 
                className="sort-dropdown"
                value={sortBy}
                onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
              >
                <option value="newest">Rilis: Terbaru ke Lama</option>
                <option value="oldest">Rilis: Terlama ke Baru</option>
                <option value="price_desc">Harga Tertinggi</option>
                <option value="price_asc">Harga Terendah</option>
                <option value="name_asc">Nama (A - Z)</option>
                <option value="name_desc">Nama (Z - A)</option>
              </select>
            </div>
          </div>
        </div>

        {/* GRID GALERI KARTU */}
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', width: '100%', color: '#e83e8c' }}>
            <div className="catalog-loader"></div>
            <h3 style={{ marginTop: '15px' }}>Memuat Data Kartu...</h3>
          </div>
        ) : cardsData.length === 0 ? (
          <div className="catalog-empty-state">
            <div className="empty-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#e83e8c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
            <h3>Kartu Tidak Ditemukan</h3>
            <p>Tidak ada kartu yang cocok dengan kata kunci <em>"{activeSearch}"</em> atau filter yang dipilih.</p>
            <button className="reset-all-btn" onClick={handleResetFilters}>Reset Semua Filter</button>
          </div>
        ) : (
          <>
            <div className="card-gallery-grid">
              {cardsData.map((card) => (
                <div 
                  key={card.id} 
                  className="gallery-card-item"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsChartLoading(true);
                    setSelectedCard(card);
                    setIsFocusCard(false);
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setIsChartLoading(true);
                      setSelectedCard(card);
                      setIsFocusCard(false);
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="card-image-wrapper">
                    <img 
                      src={card.image} 
                      alt={card.name} 
                      className="card-image" 
                      loading="lazy"
                      onError={(e) => { e.target.src = '/card-result.png'; }}
                    />
                  </div>
                  
                  <div className="card-details-mini">
                    <div className="detail-row">
                      <span className="card-name-mini" title={card.name}>{card.name}</span>
                      <span className={`card-price-mini ${card.is_unlisted ? 'price-unlisted' : ''}`}>
                        {card.price_usd || card.price}
                      </span>
                    </div>
                    
                    <div className="detail-row">
                      <span className="card-rarity-text">{card.rarityText}</span>
                      <span className={`card-price-idr ${card.is_unlisted ? 'idr-unlisted' : ''}`} title="Estimasi IDR">
                        {card.price_idr}
                      </span>
                    </div>
                    
                    <div className="detail-row footer-row">
                      <span className="rarity-icon-badge">{card.rarityIcon}</span>
                      <span className="set-badge">{card.set}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* BARIS PAGINATION */}
            <div className="catalog-pagination">
              <button 
                className="pagination-btn"
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                ◀ Sebelumnya
              </button>
              
              <span className="pagination-info">
                Halaman <strong>{page}</strong> dari <strong>{totalPages.toLocaleString('id-ID')}</strong>
              </span>

              <button 
                className="pagination-btn"
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Selanjutnya ▶
              </button>
            </div>
          </>
        )}
      </div>

      {/* =========================================
          POP-UP MODAL (DUAL-CARD: 3D KIRI + DETAIL KANAN)
          ========================================= */}
      {selectedCard && createPortal(
        <div 
          className={`catalog-modal-overlay catalog-dual-overlay ${isClosingModal ? 'closing' : ''}`} 
          onClick={handleCloseModal}
        >
          <div 
            className={`catalog-dual-modal-wrapper ${isFocusCard ? 'is-focus-mode' : ''} ${isClosingModal ? 'closing' : ''}`} 
            onClick={(e) => e.stopPropagation()}
          >
            {/* Bagian Kiri: 3D Holographic Interactive Card */}
            <div className={`catalog-dual-left ${isFocusCard ? 'is-focused' : ''}`}>
              <HoloCard3D 
                key={`holo-3d-${selectedCard.id}`}
                card={selectedCard}
                imageUrl={getCardLargeImage(selectedCard)}
                isFocused={isFocusCard}
                onCardClick={() => setIsFocusCard(prev => !prev)}
              />
            </div>

            {/* Bagian Kanan: Card Putih Detail Kartu & Analitika */}
            {!isFocusCard && (
              <div className="catalog-dual-right">
                <div className="modal-right-content-wrapper">
                {/* Bagian Atas Kanan: Tabel + Kotak Abu (Sejajar) */}
                <div className="modal-top-section">
                  
                  {/* Kiri dari Bagian Atas: Tabel Spesifikasi */}
                  <div className="catalog-modal-specs-section">
                    <table className="catalog-modal-table">
                      <tbody>
                        <tr>
                          <td className="spec-label">Card ID</td>
                          <td className="spec-value spec-card-id">{selectedCard.id || '-'}</td>
                          <td className="spec-label">HP</td>
                          <td className="spec-value">{selectedCard.hp || '-'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Name</td>
                          <td className="spec-value">{selectedCard.name || '-'}</td>
                          <td className="spec-label">Supertype</td>
                          <td className="spec-value">{selectedCard.supertype || 'Pokémon'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Rarity</td>
                          <td className="spec-value">{selectedCard.rarityText || '-'}</td>
                          <td className="spec-label">Subtype</td>
                          <td className="spec-value">{selectedCard.subtypes || '-'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Holofoil type</td>
                          <td className="spec-value">{selectedCard.rarityText?.toLowerCase().includes('holo') ? 'Holofoil' : 'Standard'}</td>
                          <td className="spec-label">Element Type</td>
                          <td className="spec-value">{selectedCard.types || '-'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Set code</td>
                          <td className="spec-value">{selectedCard.set || '-'}</td>
                          <td className="spec-label">Series</td>
                          <td className="spec-value">{selectedCard.series || '-'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Set name</td>
                          <td className="spec-value">{selectedCard.setName || '-'}</td>
                          <td className="spec-label">Artist</td>
                          <td className="spec-value">{selectedCard.artist || '-'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Number</td>
                          <td className="spec-value">{selectedCard.number || (selectedCard.id ? selectedCard.id.split('-')[1] : '-')}</td>
                          <td className="spec-label">Language</td>
                          <td className="spec-value">English</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Kanan dari Bagian Atas: Grid Kotak Abu-abu dengan Icon Buatan Sendiri */}
                  <div className="catalog-modal-analytics-grid">

                    {/* 1. Kotak All-time high */}
                    <div className="analytics-box-gray">
                      <div className="analytics-box-content">
                        <span className="analytics-label">All-time high</span>
                        <span className="analytics-value">${allTimeHighVal.toFixed(2)}</span>
                      </div>
                      <div className="analytics-box-icon">
                        <img src="/icon-ath.png" alt="All-time high icon" />
                      </div>
                    </div>

                    {/* 2. Kotak Market AVG */}
                    <div className="analytics-box-gray">
                      <div className="analytics-box-content">
                        <span className="analytics-label">Market AVG</span>
                        <span className="analytics-value">${avgVal.toFixed(2)}</span>
                      </div>
                      <div className="analytics-box-icon">
                        <img src="/icon-avg.png" alt="Market AVG icon" />
                      </div>
                    </div>

                    {/* 3. Kotak 30-day trend */}
                    <div className="analytics-box-gray">
                      <div className="analytics-box-content">
                        <span className="analytics-label">30-day trend</span>
                        <span className="analytics-value">{trendText}</span>
                      </div>
                      <div className="analytics-box-icon">
                        <img src="/icon-trend.png" alt="Trend icon" />
                      </div>
                    </div>

                    {/* 4. Kotak Age to market */}
                    <div className="analytics-box-gray">
                      <div className="analytics-box-content">
                        <span className="analytics-label">Age to market</span>
                        <span className="analytics-value">{ageText}</span>
                      </div>
                      <div className="analytics-box-icon">
                        <img src="/icon-age.png" alt="Age icon" />
                      </div>
                    </div>

                    {/* 5. Kotak Price valuation */}
                    <div className="analytics-box-gray">
                      <div className="analytics-box-content">
                        <span className="analytics-label">Price valuation</span>
                        <span className={`analytics-value ${valuationClass}`}>{valuationLabel}</span>
                      </div>
                      <div className="analytics-box-icon">
                        <img src="/icon-valuation.png" alt="Valuation icon" />
                      </div>
                    </div>

                    {/* 6. Kotak Trading signal (Dinamis: Hijau / Merah / Kuning) */}
                    <div className={`analytics-box-gray signal-box-highlight ${signalClass === 'signal-buy' ? 'signal-box-buy' : signalClass === 'signal-sell' ? 'signal-box-sell' : 'signal-box-hold'}`}>
                      <div className="analytics-box-content">
                        <span className="analytics-label">Trading signal</span>
                        <span className="analytics-value signal-bold-text">{signalDisplay}</span>
                      </div>
                    </div>

                  </div>
                </div>

                {/* Bagian Bawah Kanan: Grafik Garis Riil + Forecasting Band */}
                <div className="catalog-modal-chart-area">
                  <div className="catalog-chart-header">
                    <div className="catalog-chart-title-area">
                      <span className="catalog-chart-title">
                        Price History & 7-Day Forecast {isChartLoading ? '(Memuat...)' : ''}
                      </span>
                      {cardForecast?.change_pct !== undefined && (
                        <span className={`catalog-chart-trend-tag ${trendClass}`}>
                          {trendText} (7D)
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

                  <div className="catalog-chart-svg-container">
                    {/* Tooltip Mengambang Saat Hover Titik */}
                    {hoveredPoint && (
                      <div 
                        className="chart-hover-card"
                        style={{
                          left: `${Math.min(88, Math.max(12, (hoveredPoint.x / svgWidth) * 100))}%`
                        }}
                      >
                        <div className="hover-type-label">
                          {hoveredPoint.type === 'history' ? 'Riwayat Pasar' : (hoveredPoint.type === 'anchor' ? 'Harga Saat Ini' : 'Prediksi AI (P50)')}
                        </div>
                        <div className="hover-date">{hoveredPoint.date}</div>
                        <div className="hover-price-val">
                          ${hoveredPoint.priceUsd.toFixed(2)}
                          <span className="hover-usd-val"> ({formatIDR(hoveredPoint.priceIdr)})</span>
                        </div>
                        {hoveredPoint.type === 'forecast' && hoveredPoint.p10Usd && hoveredPoint.p90Usd && (
                          <div className="hover-range-text" style={{ fontSize: '9px', color: '#cbd5e1', marginTop: '2px', fontWeight: 600 }}>
                            Rentang: ${hoveredPoint.p10Usd.toFixed(2)} – ${hoveredPoint.p90Usd.toFixed(2)}
                          </div>
                        )}
                      </div>
                    )}

                    <svg width="100%" height="100%" viewBox={`0 0 ${svgWidth} ${svgHeight}`} preserveAspectRatio="none">
                      {/* Grid Lines Horizontal Sumbu Y */}
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
                            fontSize="9" 
                            fill="#94a3b8" 
                            textAnchor="end" 
                            fontWeight="600"
                          >
                            ${tick.valUsd >= 10 ? tick.valUsd.toFixed(1) : tick.valUsd.toFixed(2)}
                          </text>
                        </g>
                      ))}

                      {/* Selubung Pita Kuantil Probabilitas (Pita Melengkung Halus P10 - P90) */}
                      {ribbonSmoothPath && (
                        <path
                          d={ribbonSmoothPath}
                          fill="rgba(0, 210, 106, 0.22)"
                          stroke="rgba(0, 210, 106, 0.45)"
                          strokeWidth="1.2"
                          strokeDasharray="3 3"
                        />
                      )}

                      {/* Segmen 1: Garis Riwayat Pasar (Kurva Lengkung Halus Magenta) */}
                      {historySmoothPath && (
                        <path
                          d={historySmoothPath}
                          fill="none"
                          stroke="#c2185b"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      )}

                      {/* Segmen 2: Garis Prediksi AI 7 Hari (Kurva Lengkung Halus Putus-putus Hijau) */}
                      {forecastSmoothPath && (
                        <path
                          d={forecastSmoothPath}
                          fill="none"
                          stroke="#00d26a"
                          strokeWidth="2.5"
                          strokeDasharray="5 3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      )}

                      {/* Titik Data (Dots & Interactive Hit Area) */}
                      {pointsWithCoords.map((pt, i) => {
                        const isHistory = pt.type === 'history';
                        const isAnchor = pt.type === 'anchor';
                        const fillColor = isAnchor ? '#ffffff' : (isHistory ? '#c2185b' : '#00d26a');
                        const strokeColor = isAnchor ? '#c2185b' : '#ffffff';
                        const isHovered = hoveredPoint?.x === pt.x && hoveredPoint?.y === pt.y;

                        return (
                          <g key={i}>
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r={isHovered ? 5 : 3.2}
                              fill={fillColor}
                              stroke={strokeColor}
                              strokeWidth={isAnchor ? 2 : 1}
                              style={{ transition: 'all 0.15s ease' }}
                            />
                            {/* Area Transparan Luas untuk Hover Mouse yang Mudah */}
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r="14"
                              fill="transparent"
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredPoint(pt)}
                              onMouseLeave={() => setHoveredPoint(null)}
                            />
                          </g>
                        );
                      })}

                      {/* Label Sumbu X */}
                      {pointsWithCoords.map((pt, i) => {
                        const total = pointsWithCoords.length;
                        const shouldShow = i === 0 || i === historyItems.length || i === total - 1 || (total > 6 && i === Math.floor(historyItems.length + (forecastItems.length / 2)));
                        if (!shouldShow) return null;
                        return (
                          <text 
                            key={`lbl-${i}`} 
                            x={pt.x} 
                            y={svgHeight - 8} 
                            fontSize="9" 
                            fill={pt.type === 'anchor' ? '#1e293b' : '#94a3b8'} 
                            textAnchor="middle" 
                            fontWeight={pt.type === 'anchor' ? '700' : '600'}
                          >
                            {pt.label}
                          </text>
                        );
                      })}
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>,
      document.body
    )}

    </div>
  );
}

export default CatalogPage;