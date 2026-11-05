import React, { useState, useEffect, useCallback } from 'react';
import './Marketplace.css';

// ==========================================
// 1. KOMPONEN IKON SVG (BEBAS EMOTIKON)
// ==========================================
const SearchIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#475086" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const BookmarkIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} width="100%" height="100%" fill="currentColor">
    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
  </svg>
);

const ChevronDownIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#475086" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
  </svg>
);

const FlagBadge = ({ lang }) => {
  return <span className="mk-flag-label" title={`Wilayah Rilis: ${lang}`}>{lang}</span>;
};

const RarityIcon = ({ type }) => {
  if (type === 'circle') return <span className="mk-symbol-circle"></span>;
  if (type === 'star') return (
    <svg viewBox="0 0 24 24" width="10" height="10" fill="#f59e0b" className="mk-symbol-star">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
    </svg>
  );
  if (type === 'double-star') return (
    <div className="mk-symbol-double">
      <svg viewBox="0 0 24 24" width="10" height="10" fill="#1e293b">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
      </svg>
      <svg viewBox="0 0 24 24" width="10" height="10" fill="#1e293b" style={{ marginLeft: '-4px' }}>
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
      </svg>
    </div>
  );
  return null;
};

// Helper: Memetakan nama kelangkaan ke simbol visual & singkatan
function getRarityMeta(rarityStr) {
  const r = (rarityStr || '').toLowerCase();
  if (r.includes('special') || r.includes('hyper') || r.includes('secret')) {
    return { symbol: 'double-star', abbr: 'SAR' };
  }
  if (r.includes('ultra') || r.includes('illustration') || r.includes('double')) {
    return { symbol: 'star', abbr: 'AR' };
  }
  if (r.includes('rare') || r.includes('holo')) {
    return { symbol: 'star', abbr: 'R' };
  }
  if (r.includes('uncommon')) {
    return { symbol: 'circle', abbr: 'U' };
  }
  return { symbol: 'circle', abbr: 'C' };
}

// ==========================================
// 2. KOMPONEN UTAMA MARKETPLACE
// ==========================================
export default function Marketplace() {
  // State Data Kartu dari Backend
  const [cards, setCards] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCards, setTotalCards] = useState(0);

  // State Filter & Pencarian
  const [searchInput, setSearchInput] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [sortBy, setSortBy] = useState('name_asc');
  const [selectedRarity, setSelectedRarity] = useState('all');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');

  // State Saved Items (Tersinkronisasi ke LocalStorage)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [savedCards, setSavedCards] = useState(() => {
    try {
      const saved = localStorage.getItem('regokemon_saved_cards');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Fungsi Toggle Simpan / Hapus Kartu
  const toggleSaveCard = (card) => {
    setSavedCards((prev) => {
      const isAlreadySaved = prev.some((item) => item.id === card.id);
      let updated;
      if (isAlreadySaved) {
        updated = prev.filter((item) => item.id !== card.id);
      } else {
        updated = [...prev, card];
      }
      try {
        localStorage.setItem('regokemon_saved_cards', JSON.stringify(updated));
      } catch (err) {
        console.error('Gagal menyimpan ke localStorage:', err);
      }
      return updated;
    });
  };

  const removeSavedCard = (cardId) => {
    setSavedCards((prev) => {
      const updated = prev.filter((item) => item.id !== cardId);
      try {
        localStorage.setItem('regokemon_saved_cards', JSON.stringify(updated));
      } catch (err) {
        console.error('Gagal menghapus dari localStorage:', err);
      }
      return updated;
    });
  };

  const isCardSaved = (cardId) => savedCards.some((item) => item.id === cardId);

  // 3. Panggilan API ke Backend (GET /cards)
  const fetchMarketCards = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        limit: '30',
        page: '1'
      });

      if (activeSearch.trim()) {
        params.append('search', activeSearch.trim());
      }
      if (selectedRarity !== 'all') {
        params.append('rarity', selectedRarity);
      }
      if (sortBy) {
        params.append('sort_by', sortBy);
      }

      const response = await fetch(`http://127.0.0.1:8000/cards?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Gagal mengambil data katalog dari backend.');
      }
      const data = await response.json();
      
      const rawCards = data.cards || (Array.isArray(data) ? data : []);
      setCards(rawCards);
      setTotalCards(data.total || rawCards.length);
    } catch (err) {
      console.error('Error fetching marketplace cards:', err);
      setCards([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeSearch, selectedRarity, sortBy]);

  useEffect(() => {
    fetchMarketCards();
  }, [fetchMarketCards]);

  // Handler Kirim Pencarian
  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    setActiveSearch(searchInput);
  };

  // Filter Harga Klien (Jika diisi rentang)
  const filteredCards = cards.filter((card) => {
    const price = card.price_num || 0;
    if (minPrice && !isNaN(parseFloat(minPrice)) && price < parseFloat(minPrice)) {
      return false;
    }
    if (maxPrice && !isNaN(parseFloat(maxPrice)) && price > parseFloat(maxPrice)) {
      return false;
    }
    return true;
  });

  return (
    <div className="mk-wrapper">
      
      {/* AREA CHECKERBOARD KUNING (PENCARIAN) */}
      <div className="mk-search-section">
        <div className="mk-search-container">
          <form className="mk-search-box" onSubmit={handleSearchSubmit}>
            <input 
              type="text" 
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Cari kartu pasar (misal: Charizard, Pikachu, Mew)..."
              className="mk-search-input"
            />
            <button type="submit" className="mk-search-icon" title="Cari">
              <SearchIcon />
            </button>
          </form>

          {/* Tombol Buka Panel Saved Items */}
          <button className="mk-saved-btn" onClick={() => setIsDrawerOpen(true)}>
            <span>Saved Items ({savedCards.length})</span>
            <div className="mk-bookmark-icon-wrapper">
              <BookmarkIcon className="mk-bookmark-svg" />
            </div>
          </button>
        </div>
      </div>

      {/* PAPAN UTAMA BIRU GELAP (KONTEN) */}
      <div className="mk-main-board">
        
        {/* Baris Filter */}
        <div className="mk-filter-bar">
          
          {/* SORT BY DROPDOWN */}
          <div className="mk-filter-item">
            <span className="mk-filter-label">Sort by</span>
            <div className="mk-dropdown">
              <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value)}
                className="mk-native-select"
                title="Urutkan Kartu"
              >
                <option value="name_asc">A - Z</option>
                <option value="name_desc">Z - A</option>
                <option value="price_asc">Termurah</option>
                <option value="price_desc">Termahal</option>
                <option value="newest">Rilis Terbaru</option>
              </select>
              <div className="mk-dropdown-icon">
                <ChevronDownIcon />
              </div>
            </div>
          </div>

          {/* RARITY DROPDOWN */}
          <div className="mk-filter-item">
            <span className="mk-filter-label">Rarity</span>
            <div className="mk-dropdown">
              <select 
                value={selectedRarity} 
                onChange={(e) => setSelectedRarity(e.target.value)}
                className="mk-native-select"
                title="Filter Kelangkaan"
              >
                <option value="all">Semua Rarity</option>
                <option value="Common">Common</option>
                <option value="Uncommon">Uncommon</option>
                <option value="Rare">Rare</option>
                <option value="Ultra Rare">Ultra Rare</option>
                <option value="Special Illustration Rare">Special Illustration</option>
              </select>
              <div className="mk-dropdown-icon">
                <ChevronDownIcon />
              </div>
            </div>
          </div>

          {/* LANGUAGE (DIRESERVASI UNTUK PENGEMBANGAN SELANJUTNYA) */}
          <div className="mk-filter-item">
            <span className="mk-filter-label">Language</span>
            <div className="mk-flags-container">
              <div className="mk-flag-circle active-flag"><FlagBadge lang="EN" /></div>
              <div className="mk-flag-circle"><FlagBadge lang="ID" /></div>
              <div className="mk-flag-circle"><FlagBadge lang="JP" /></div>
            </div>
          </div>

          {/* INPUT RENTANG HARGA USD */}
          <div className="mk-price-inputs">
            <input 
              type="number" 
              step="any"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="$ min" 
              className="mk-price-input" 
              title="Harga minimum (USD)"
            />
            <span className="mk-price-separator">-</span>
            <input 
              type="number" 
              step="any"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="$ max" 
              className="mk-price-input" 
              title="Harga maksimum (USD)"
            />
            {(minPrice || maxPrice || activeSearch || selectedRarity !== 'all') && (
              <button 
                type="button" 
                className="mk-reset-btn"
                onClick={() => {
                  setSearchInput('');
                  setActiveSearch('');
                  setSelectedRarity('all');
                  setSortBy('name_asc');
                  setMinPrice('');
                  setMaxPrice('');
                }}
                title="Reset Semua Filter"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* STATUS LOADING ATAU KOSONG */}
        {isLoading ? (
          <div className="mk-loading-state">
            <div className="mk-loading-spinner"></div>
            <p>Memuat katalog pasar Supabase...</p>
          </div>
        ) : filteredCards.length === 0 ? (
          <div className="mk-empty-state">
            <p className="mk-empty-title">Tidak ada kartu yang cocok</p>
            <p className="mk-empty-desc">Coba gunakan kata kunci pencarian lain atau ubah pengaturan filter.</p>
          </div>
        ) : (
          /* Grid Kartu Produk Riil */
          <div className="mk-grid">
            {filteredCards.map((card) => {
              const rarityMeta = getRarityMeta(card.rarityText);
              const saved = isCardSaved(card.id);
              const displayPrice = card.price_num && card.price_num > 0 
                ? `$ ${card.price_num.toFixed(2)}` 
                : (card.price || 'Unlisted');

              return (
                <div key={card.id} className="mk-card">
                  
                  {/* Pita / Tombol Bookmark Interaktif */}
                  <button 
                    type="button"
                    className={`mk-bookmark-ribbon ${saved ? 'is-saved' : 'not-saved'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSaveCard(card);
                    }}
                    title={saved ? "Hapus dari koleksi tersimpan" : "Simpan kartu ini"}
                  >
                    <BookmarkIcon className="mk-bookmark-svg-white" />
                  </button>

                  {/* Gambar Kartu Riil dari Supabase */}
                  <div className="mk-card-img-box">
                    <img 
                      src={card.image || '/card-result.png'} 
                      alt={card.name} 
                      className="mk-card-img" 
                      loading="lazy"
                    />
                  </div>

                  {/* Informasi Kartu */}
                  <div className="mk-card-content">
                    <div className="mk-card-row-1">
                      <span className="mk-card-title" title={card.name}>{card.name}</span>
                      <span className="mk-card-price">{displayPrice}</span>
                    </div>
                    <div className="mk-card-row-2">
                      <span className="mk-card-rarity">{card.rarityText || 'Standard'}</span>
                      <div className="mk-dotted-line"></div>
                      <FlagBadge lang="EN" />
                    </div>
                    <div className="mk-card-row-3">
                      <div className="mk-symbol-group">
                        <RarityIcon type={rarityMeta.symbol} />
                        <span className="mk-card-abbr">{rarityMeta.abbr}</span>
                      </div>
                      <span className="mk-card-set">{card.set || 'PROMO'}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>

      {/* =========================================
          UI SIDE DRAWER (SAVED ITEMS PANEL)
          ========================================= */}
      
      {/* 1. Latar Gelap (Overlay) */}
      <div 
        className={`mk-drawer-overlay ${isDrawerOpen ? 'open' : ''}`} 
        onClick={() => setIsDrawerOpen(false)}
      ></div>

      {/* 2. Panel Samping */}
      <div className={`mk-saved-drawer ${isDrawerOpen ? 'open' : ''}`}>
        
        {/* Header Panel */}
        <div className="mk-drawer-header">
          <div className="mk-drawer-title-group">
            <div className="mk-drawer-icon">
              <BookmarkIcon className="w-full h-full" />
            </div>
            <h2>Saved Items</h2>
            <span className="mk-drawer-count">{savedCards.length}</span>
          </div>
          <button 
            type="button" 
            className="mk-drawer-close-btn" 
            onClick={() => setIsDrawerOpen(false)}
            title="Tutup Panel"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Daftar Kartu yang Disimpan */}
        <div className="mk-drawer-content">
          {savedCards.length > 0 ? (
            savedCards.map((item) => {
              const displayItemPrice = item.price_num && item.price_num > 0 
                ? `$ ${item.price_num.toFixed(2)}` 
                : (item.price || 'Unlisted');

              return (
                <div key={item.id} className="mk-drawer-item">
                  <div className="mk-drawer-item-img-box">
                    <img 
                      src={item.image || '/card-result.png'} 
                      alt={item.name} 
                      className="mk-drawer-item-img" 
                    />
                  </div>
                  <div className="mk-drawer-item-info">
                    <span className="mk-drawer-item-name" title={item.name}>{item.name}</span>
                    <span className="mk-drawer-item-desc">{item.rarityText || 'Standard'} • {item.set || 'SET'}</span>
                    <span className="mk-drawer-item-price">{displayItemPrice}</span>
                  </div>
                  <button 
                    type="button"
                    className="mk-drawer-remove-btn" 
                    onClick={() => removeSavedCard(item.id)}
                    title="Hapus dari tersimpan"
                  >
                    <TrashIcon />
                  </button>
                </div>
              );
            })
          ) : (
            <div className="mk-drawer-empty">
              <p>Belum ada kartu yang disimpan.</p>
              <span>Klik ikon pita bookmark pada kartu untuk menyimpannya di sini.</span>
            </div>
          )}
        </div>

        {/* Footer Panel */}
        <div className="mk-drawer-footer">
          <button 
            type="button" 
            className="mk-drawer-action-btn"
            onClick={() => setIsDrawerOpen(false)}
          >
            Tutup Panel
          </button>
        </div>

      </div>

    </div>
  );
}
