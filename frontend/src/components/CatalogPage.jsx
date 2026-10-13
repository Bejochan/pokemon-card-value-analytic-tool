import React, { useState, useEffect } from 'react';
import './CatalogPage.css';

function CatalogPage() {
  const [cardsData, setCardsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCards, setTotalCards] = useState(0);
  const [currencyRate, setCurrencyRate] = useState(null);

  // Filter & Search states
  const [searchInput, setSearchInput] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [selectedSupertype, setSelectedSupertype] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  // Set Selector
  const [isSetMenuOpen, setIsSetMenuOpen] = useState(false);
  const [availableSets, setAvailableSets] = useState([
    { set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' }
  ]);
  const [activeSet, setActiveSet] = useState({ set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' });

  // 1. Ambil daftar Sets secara dinamis dari backend
  useEffect(() => {
    const fetchSets = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/sets?limit=30');
        if (response.ok) {
          const sets = await response.json();
          if (Array.isArray(sets) && sets.length > 0) {
            const formatted = [
              { set_id: 'all', name: 'All Sets', logo: '/pokemon-logo.png' },
              ...sets.map(s => {
                let logoPath = '/pokemon-logo.png'; // Default logo Regokemon
                const sNameLower = (s.name || '').toLowerCase();
                if (sNameLower.includes('30th')) {
                  logoPath = '/30th-celebration-logo.png';
                } else if (sNameLower.includes('ascended')) {
                  logoPath = '/ascended-heroes-logo.png';
                }
                return {
                  set_id: s.set_id,
                  name: s.name,
                  logo: logoPath
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

  // 2. Fungsi Mengambil Data Kartu
  const fetchCards = async (targetPage = 1) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: targetPage.toString(),
        limit: '20'
      });

      if (activeSearch.trim()) params.append('search', activeSearch.trim());
      if (selectedSupertype !== 'all') params.append('supertype', selectedSupertype);
      if (activeSet.set_id !== 'all') params.append('set_id', activeSet.set_id);
      if (sortBy) params.append('sort_by', sortBy);

      const response = await fetch(`http://127.0.0.1:8000/cards?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Gagal mengambil data dari server');
      }
      const data = await response.json();
      
      if (data && data.cards) {
        setCardsData(data.cards);
        setTotalCards(data.total || 0);
        setTotalPages(data.total_pages || 1);
        setPage(data.page || 1);
        if (data.currency_rate) setCurrencyRate(data.currency_rate);
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

  // Re-fetch saat filter / search / sort / set berubah
  useEffect(() => {
    fetchCards(page);
  }, [page, activeSearch, selectedSupertype, activeSet, sortBy]);

  // Handler Submit Pencarian
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setActiveSearch(searchInput);
  };

  const handleSupertypeChange = (type) => {
    setPage(1);
    setSelectedSupertype(prev => prev === type ? 'all' : type);
  };

  return (
    <div className="catalog-container">
      
      {/* HEADER PENCARIAN */}
      <div className="catalog-header">
        <div className="set-selector-container">
          <button className="set-selector-btn" onClick={() => setIsSetMenuOpen(!isSetMenuOpen)}>
            <img src={activeSet.logo} alt={`${activeSet.name} Icon`} className="celebration-icon" /> 
            <span className="celebration-text">{activeSet.name}</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1e1b4b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`set-arrow ${isSetMenuOpen ? 'open' : ''}`}>
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {/* MENU SET (Dropdown) */}
          {isSetMenuOpen && (
            <div className="set-dropdown-menu">
              {availableSets.map((setObj) => (
                <div 
                  key={setObj.set_id} 
                  className={`set-dropdown-item ${activeSet.set_id === setObj.set_id ? 'active' : ''}`}
                  onClick={() => {
                    setActiveSet(setObj);
                    setPage(1);
                    setIsSetMenuOpen(false); 
                  }}
                >
                  {setObj.name}
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* FORM SEARCH BAR */}
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
            {selectedSupertype !== 'all' && (
              <button 
                className="reset-filter-btn" 
                onClick={() => setSelectedSupertype('all')}
              >
                Reset
              </button>
            )}
          </div>

          <div className="catalog-count-info">
            Menampilkan <strong>{cardsData.length}</strong> dari <strong>{totalCards.toLocaleString('id-ID')}</strong> kartu
          </div>

          <div className="sort-group">
            <span className="filter-label">Sort by:</span>
            <select 
              className="sort-dropdown"
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
            >
              <option value="newest">Default / Rilis</option>
              <option value="name_asc">Nama (A - Z)</option>
              <option value="name_desc">Nama (Z - A)</option>
              <option value="price_desc">Harga Tertinggi</option>
              <option value="price_asc">Harga Terendah</option>
            </select>
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
            <div className="empty-icon">🔍</div>
            <h3>Kartu Tidak Ditemukan</h3>
            <p>Tidak ada kartu yang cocok dengan kata kunci <em>"{activeSearch}"</em> atau filter yang dipilih.</p>
            <button 
              className="reset-all-btn"
              onClick={() => {
                setActiveSearch('');
                setSearchInput('');
                setSelectedSupertype('all');
                setActiveSet(availableSets[0]);
                setPage(1);
              }}
            >
              Reset Semua Filter
            </button>
          </div>
        ) : (
          <>
            <div className="card-gallery-grid">
              {cardsData.map((card) => (
                <div key={card.id} className="gallery-card-item">
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
    </div>
  );
}

export default CatalogPage;