import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config/api';
import './CatalogPage.css';

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

function CatalogPage() {
  const [cardsData, setCardsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCards, setTotalCards] = useState(0);

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
        setSelectedCard(null); 
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
  }, [isSetMenuOpen, selectedCard]);

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
        const response = await fetch(`${API_BASE_URL}/sets?limit=150`);
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

  const fetchCards = async (targetPage = 1) => {
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
  };

  useEffect(() => {
    fetchCards(page);
  }, [page, activeSearch, selectedSupertype, selectedRarity, selectedHolo, activeSet, sortBy]);

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
              <option value="Ultra">Ultra / Secret Rare</option>
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
                  onClick={() => setSelectedCard(card)} 
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
          POP-UP MODAL (DETAIL KARTU) - LAYOUT REVISI
          ========================================= */}
      {selectedCard && (
        <div className="catalog-modal-overlay" onClick={() => setSelectedCard(null)}>
          <div className="catalog-modal-content" onClick={(e) => e.stopPropagation()}>
            
            {/* Tombol Tutup */}
            <button className="catalog-modal-close" onClick={() => setSelectedCard(null)}>
              <CloseIcon />
            </button>

            {/* Kolom Kiri (Latar Kuning Penuh) */}
            <div className="catalog-modal-left">
              <div className="modal-card-img-container">
                <img 
                  src={selectedCard.image} 
                  alt={selectedCard.name} 
                  className="catalog-modal-card-img"
                  onError={(e) => { e.target.src = '/card-result.png'; }} 
                />
              </div>
            </div>

            {/* Kolom Kanan (Konten Putih) */}
            <div className="catalog-modal-right">
              
              <div className="modal-right-content-wrapper">
                {/* Bagian Atas Kanan: Tabel + Kotak Abu (Sejajar) */}
                <div className="modal-top-section">
                  
                  {/* Kiri dari Bagian Atas: Tabel Spesifikasi */}
                  <div className="catalog-modal-specs-section">
                    <table className="catalog-modal-table">
                      <tbody>
                        <tr>
                          <td className="spec-label">Name</td>
                          <td className="spec-value">{selectedCard.name || '-'}</td>
                          <td className="spec-label">HP</td>
                          <td className="spec-value">{selectedCard.hp || '120'}</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Rarity</td>
                          <td className="spec-value">{selectedCard.rarityText || '-'}</td>
                          <td className="spec-label">Attack</td>
                          <td className="spec-value">Windmill <span style={{float: 'right'}}>20</span></td>
                        </tr>
                        <tr>
                          <td className="spec-label">Holofoil type</td>
                          <td className="spec-value">Standard holofoil</td>
                          <td className="spec-label"></td>
                          <td className="spec-value">Flower tornado <span style={{float: 'right'}}>60</span></td>
                        </tr>
                        <tr>
                          <td className="spec-label">Language</td>
                          <td className="spec-value">English</td>
                          <td className="spec-label">Weakness</td>
                          <td className="spec-value">*fire x 2</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Set number</td>
                          <td className="spec-value">036 / 084</td>
                          <td className="spec-label">Resistance</td>
                          <td className="spec-value">-</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Year</td>
                          <td className="spec-value">2017</td>
                          <td className="spec-label">Retreat</td>
                          <td className="spec-value">*</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Set code</td>
                          <td className="spec-value">{selectedCard.set || '-'}</td>
                          <td className="spec-label">Number</td>
                          <td className="spec-value">182</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Regulation mark</td>
                          <td className="spec-value">H</td>
                          <td className="spec-label">Height</td>
                          <td className="spec-value">1' 04"</td>
                        </tr>
                        <tr>
                          <td className="spec-label">Stage</td>
                          <td className="spec-value">2</td>
                          <td className="spec-label">Weight</td>
                          <td className="spec-value">12.8 lbs.</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Kanan dari Bagian Atas: Grid Kotak Abu-abu */}
                  <div className="catalog-modal-analytics-grid">
                    <div className="analytics-box-gray"><span className="analytics-label">All-time high</span>
                    <span className="analytics-value">$12.50</span></div>
                    <div className="analytics-box-gray"><span className="analytics-label">Market AVG</span>
                    <span className="analytics-value">$4.80</span></div>
                    <div className="analytics-box-gray"><span className="analytics-label">30 day trend</span>
                    <span className="analytics-value trend-positive">+14.5%</span></div>
                    <div className="analytics-box-gray"><span className="analytics-label">Age to market</span>
                    <span className="analytics-value">7 Thn</span></div>
                    <div className="analytics-box-gray"><span className="analytics-label">Price valuation</span>
                    <span className="analytics-value">Undervalued</span></div>
                    <div className="analytics-box-gray"><span className="analytics-label">Trading signal</span>
                    <span className="analytics-value signal-buy">Strong Buy</span></div>
                  </div>

                </div>

                {/* Bagian Bawah Kanan: Grafik Garis (Dengan Padding Atas Aman & Skala Lengkap 0-10) */}
                <div className="catalog-modal-chart-area">
                  <svg width="100%" height="100%" viewBox="0 0 700 155" preserveAspectRatio="none">
                    {/* Grid Lines Horizontal Sumbu Y (0, 2, 4, 6, 8, 10) */}
                    <line x1="35" y1="130" x2="680" y2="130" stroke="#f1f5f9" strokeWidth="1.5" />
                    <line x1="35" y1="108" x2="680" y2="108" stroke="#f1f5f9" strokeWidth="1.5" />
                    <line x1="35" y1="86"  x2="680" y2="86"  stroke="#f1f5f9" strokeWidth="1.5" />
                    <line x1="35" y1="64"  x2="680" y2="64"  stroke="#f1f5f9" strokeWidth="1.5" />
                    <line x1="35" y1="42"  x2="680" y2="42"  stroke="#f1f5f9" strokeWidth="1.5" />
                    <line x1="35" y1="20"  x2="680" y2="20"  stroke="#f1f5f9" strokeWidth="1.5" />
                    
                    {/* Label Angka Sumbu Y (Posisi y sudah diturunkan agar tidak terpotong) */}
                    <text x="25" y="134" fontSize="10" fill="#94a3b8" textAnchor="end" fontWeight="600">0</text>
                    <text x="25" y="112" fontSize="10" fill="#94a3b8" textAnchor="end" fontWeight="600">2</text>
                    <text x="25" y="90"  fontSize="10" fill="#94a3b8" textAnchor="end" fontWeight="600">4</text>
                    <text x="25" y="68"  fontSize="10" fill="#94a3b8" textAnchor="end" fontWeight="600">6</text>
                    <text x="25" y="46"  fontSize="10" fill="#94a3b8" textAnchor="end" fontWeight="600">8</text>
                    <text x="25" y="24"  fontSize="10" fill="#94a3b8" textAnchor="end" fontWeight="600">10</text>

                    {/* Garis Kurva Halus Magenta (#c2185b) Sesuai Mockup Canva */}
                    <path 
                      d="M 50 100 C 110 95, 130 90, 170 88 C 210 86, 250 66, 290 62 C 330 58, 370 72, 410 70 C 450 68, 490 48, 530 44 C 570 40, 610 35, 650 33" 
                      fill="none" 
                      stroke="#c2185b" 
                      strokeWidth="2.5" 
                      strokeLinecap="round" 
                    />
                    
                    {/* Titik Data (Dots) */}
                    <circle cx="50"  cy="100" r="3.5" fill="#c2185b" />
                    <circle cx="170" cy="88"  r="3.5" fill="#c2185b" />
                    <circle cx="290" cy="62"  r="3.5" fill="#c2185b" />
                    <circle cx="410" cy="70"  r="3.5" fill="#c2185b" />
                    <circle cx="530" cy="44"  r="3.5" fill="#c2185b" />
                    <circle cx="650" cy="33"  r="3.5" fill="#c2185b" />

                    {/* Label Bulan Sumbu X */}
                    <text x="50"  y="148" fontSize="9.5" fill="#94a3b8" textAnchor="middle" fontWeight="600">May</text>
                    <text x="170" y="148" fontSize="9.5" fill="#94a3b8" textAnchor="middle" fontWeight="600">Jun</text>
                    <text x="290" y="148" fontSize="9.5" fill="#94a3b8" textAnchor="middle" fontWeight="600">Jul</text>
                    <text x="410" y="148" fontSize="9.5" fill="#94a3b8" textAnchor="middle" fontWeight="600">Aug</text>
                    <text x="530" y="148" fontSize="9.5" fill="#94a3b8" textAnchor="middle" fontWeight="600">Sep</text>
                    <text x="650" y="148" fontSize="9.5" fill="#94a3b8" textAnchor="middle" fontWeight="600">Oct</text>
                  </svg>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default CatalogPage;