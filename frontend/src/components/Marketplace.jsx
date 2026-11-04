import React, { useState } from 'react';
import './Marketplace.css';

// ==========================================
// 1. DATA DUMMY (Menggunakan gambar default)
// ==========================================
const mockCards = [
  { id: 1, name: 'Deoxys VSTAR', price: 12.00, rarityName: 'Common', language: 'UK', raritySymbol: 'circle', rarityAbbr: 'C', setTag: 'M2a', saved: true, imgUrl: '/card-result.png' },
  { id: 2, name: 'Deoxys VSTAR', price: 12.00, rarityName: 'Special Illustration Rare', language: 'UK', raritySymbol: 'double-star', rarityAbbr: 'SAR', setTag: 'V2a', saved: true, imgUrl: '/card-result.png' },
  { id: 3, name: 'Deoxys VSTAR', price: 10.00, rarityName: 'Illustration Rare', language: 'JP', raritySymbol: 'star', rarityAbbr: 'AR', setTag: 'N2a', saved: true, imgUrl: '/card-result.png' },
  { id: 4, name: 'Deoxys VSTAR', price: 11.00, rarityName: 'Common', language: 'UK', raritySymbol: 'circle', rarityAbbr: 'C', setTag: 'N2a', saved: true, imgUrl: '/card-result.png' },
  { id: 5, name: 'Deoxys VSTAR', price: 9.00, rarityName: 'Double Rare', language: 'ID', raritySymbol: 'double-star', rarityAbbr: 'RR', setTag: 'N2a', saved: true, imgUrl: '/card-result.png' },
];

// ==========================================
// 2. KOMPONEN IKON SVG
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

// Ikon Baru untuk Drawer
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

const FlagIcon = ({ lang }) => {
  const flags = { 'UK': '🇬🇧', 'ID': '🇮🇩', 'JP': '🇯🇵' };
  return <span className="mk-flag-emoji" title={lang}>{flags[lang]}</span>;
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

// ==========================================
// 3. KOMPONEN UTAMA MARKETPLACE
// ==========================================
export default function Marketplace() {
  const [searchQuery, setSearchQuery] = useState('Deaoxys VSTAR');
  
  // STATE BARU: Mengontrol buka/tutup panel Saved Items
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Ambil hanya item yang tersimpan untuk ditampilkan di panel
  const savedItemsList = mockCards.filter(card => card.saved);

  return (
    <div className="mk-wrapper">
      
      {/* AREA CHECKERBOARD KUNING (PENCARIAN) */}
      <div className="mk-search-section">
        <div className="mk-search-container">
          <div className="mk-search-box">
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari kartu (misal: Charizard, Pikachu)..."
              className="mk-search-input"
            />
            <div className="mk-search-icon">
              <SearchIcon />
            </div>
          </div>

          {/* PERBAIKAN: Tambahkan event onClick untuk membuka panel */}
          <button className="mk-saved-btn" onClick={() => setIsDrawerOpen(true)}>
            <span>Saved Items</span>
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
          <div className="mk-filter-item">
            <span className="mk-filter-label">Sort by</span>
            <div className="mk-dropdown">
              <span>A - Z</span>
              <ChevronDownIcon />
            </div>
          </div>

          <div className="mk-filter-item">
            <span className="mk-filter-label">Rarity</span>
            <div className="mk-dropdown">
              <span>Ultra Rare</span>
              <ChevronDownIcon />
            </div>
          </div>

          <div className="mk-filter-item">
            <span className="mk-filter-label">Language</span>
            <div className="mk-flags-container">
              <div className="mk-flag-circle"><FlagIcon lang="UK" /></div>
              <div className="mk-flag-circle"><FlagIcon lang="ID" /></div>
              <div className="mk-flag-circle"><FlagIcon lang="JP" /></div>
            </div>
          </div>

          <div className="mk-price-inputs">
            <input type="text" placeholder="$ lowest" className="mk-price-input" />
            <span className="mk-price-separator">—</span>
            <input type="text" placeholder="$ highest" className="mk-price-input" />
          </div>
        </div>

        {/* Grid Kartu Produk */}
        <div className="mk-grid">
          {mockCards.map((card) => (
            <div key={card.id} className="mk-card">
              
              {/* Pita Bookmark Pink */}
              {card.saved && (
                <div className="mk-bookmark-ribbon">
                  <BookmarkIcon className="mk-bookmark-svg-white" />
                </div>
              )}

              {/* Gambar Kartu */}
              <div className="mk-card-img-box">
                <img src={card.imgUrl} alt={card.name} className="mk-card-img" />
              </div>

              {/* Informasi Kartu */}
              <div className="mk-card-content">
                <div className="mk-card-row-1">
                  <span className="mk-card-title">{card.name}</span>
                  <span className="mk-card-price">$ {card.price.toFixed(2)}</span>
                </div>
                <div className="mk-card-row-2">
                  <span className="mk-card-rarity">{card.rarityName}</span>
                  <div className="mk-dotted-line"></div>
                  <FlagIcon lang={card.language} />
                </div>
                <div className="mk-card-row-3">
                  <div className="mk-symbol-group">
                    <RarityIcon type={card.raritySymbol} />
                    <span className="mk-card-abbr">{card.rarityAbbr}</span>
                  </div>
                  <span className="mk-card-set">{card.setTag}</span>
                </div>
              </div>
            </div>
          ))}
          
          {/* Kartu Kosong (Placeholder) */}
          <div className="mk-empty-card"></div>
          <div className="mk-empty-card"></div>
          <div className="mk-empty-card"></div>
        </div>
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
            <span className="mk-drawer-count">{savedItemsList.length}</span>
          </div>
          <button className="mk-drawer-close-btn" onClick={() => setIsDrawerOpen(false)}>
            <CloseIcon />
          </button>
        </div>

        {/* Daftar Kartu yang Disimpan */}
        <div className="mk-drawer-content">
          {savedItemsList.length > 0 ? (
            savedItemsList.map((item) => (
              <div key={item.id} className="mk-drawer-item">
                <div className="mk-drawer-item-img-box">
                  <img src={item.imgUrl} alt={item.name} className="mk-drawer-item-img" />
                </div>
                <div className="mk-drawer-item-info">
                  <span className="mk-drawer-item-name">{item.name}</span>
                  <span className="mk-drawer-item-desc">{item.rarityName} • {item.rarityAbbr}</span>
                  <span className="mk-drawer-item-price">$ {item.price.toFixed(2)}</span>
                </div>
                <button className="mk-drawer-remove-btn" title="Hapus dari tersimpan">
                  <TrashIcon />
                </button>
              </div>
            ))
          ) : (
            <div className="mk-drawer-empty">
              <p>Belum ada kartu yang disimpan.</p>
            </div>
          )}
        </div>

        {/* Footer Panel */}
        <div className="mk-drawer-footer">
          <button className="mk-drawer-action-btn">
            Lihat Semua Koleksi
          </button>
        </div>

      </div>

    </div>
  );
}