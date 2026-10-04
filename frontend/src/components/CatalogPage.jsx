import React, { useState } from 'react';
import './CatalogPage.css';

function CatalogPage() {
  // --- PERBAIKAN: Membuat Data Kartu Dinamis & Menggunakan card-result.png ---
  // Objek dasar data kartu yang akan diulang-ulang.
  // Ganti source gambar dengan card-result.png
  const baseCardData = {
    name: "Fuecoco",
    price: "$ 5.00",
    rarityText: "Common",
    rarityIcon: "C",
    set: "m2a",
    image: "/card-result.png" // Menggunakan card-result.png untuk semua kartu
  };

  // Membuat array data simulasi yang terdiri dari 25 kartu (5 baris x 5 kolom)
  // key 'id' dibuat unik untuk React.
  const [cardsData] = useState(
    Array.from({ length: 25 }, (_, i) => ({
      ...baseCardData,
      id: i + 1, // ID unik untuk setiap item
    }))
  );

  const [isSetMenuOpen, setIsSetMenuOpen] = useState(false);
  
  const pokemonSetsData = [
    { name: "30th Celebration", logo: "/30th-celebration-logo.png" },
    // Untuk sementara gunakan gambar yang sama, nanti tinggal diganti nama filenya
    { name: "Ascended Heroes", logo: "/pokemon-logo.png" }, 
    { name: "Crimson Haze", logo: "/pokemon-logo.png" },
    { name: "Twilight Masquerade", logo: "/pokemon-logo.png" }
  ];

  // Set default menggunakan objek pertama (30th Celebration)
  const [activeSet, setActiveSet] = useState(pokemonSetsData[0]);

  return (
    <div className="catalog-container">
      
      {/* HEADER PENCARIAN (Warna akan diubah di CSS) */}
      <div className="catalog-header">
        <div className="set-selector-container">
          <button className="set-selector-btn" onClick={() => setIsSetMenuOpen(!isSetMenuOpen)}>
            {/* 2. UBAH src GAMBAR MENJADI DINAMIS MENGAMBIL DARI STATE */}
            <img src={activeSet.logo} alt={`${activeSet.name} Icon`} className="celebration-icon" /> 
            
            {/* 3. UBAH TEKS MENJADI DINAMIS */}
            <span className="celebration-text">{activeSet.name}</span>
            
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1e1b4b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`set-arrow ${isSetMenuOpen ? 'open' : ''}`}>
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {/* MENU SET (Muncul saat diklik) */}
          {isSetMenuOpen && (
            <div className="set-dropdown-menu">
              {/* 4. LOOPING MENGGUNAKAN DATA OBJEK BARU */}
              {pokemonSetsData.map((setObj) => (
                <div 
                  key={setObj.name} 
                  className={`set-dropdown-item ${activeSet.name === setObj.name ? 'active' : ''}`}
                  onClick={() => {
                    setActiveSet(setObj); // Memasukkan seluruh objek ke state aktif
                    setIsSetMenuOpen(false); 
                  }}
                >
                  {setObj.name}
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="search-bar-wrapper">
          <input type="text" className="search-input" placeholder="Look for a specific card!" />
          <button className="search-icon-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#e83e8c" strokeWidth="3" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </button>
        </div>
      </div>

      {/* AREA KONTEN PUTIH */}
      <div className="catalog-content-area">
        
        {/* BARIS FILTER */}
        <div className="filter-bar">
          <div className="filter-group">
            <span className="filter-label">Filter</span>
            <label className="checkbox-label"><input type="checkbox" /> Pokemon</label>
            <label className="checkbox-label"><input type="checkbox" /> Trainer</label>
            <label className="checkbox-label"><input type="checkbox" /> Energy</label>
          </div>

          <div className="filter-group">
            <span className="filter-label">Language</span>
            <span className="flag-icon">🇬🇧</span>
            <span className="flag-icon">🇯🇵</span>
            <span className="flag-icon">🇮🇩</span>
          </div>

          <div className="filter-group">
            <label className="checkbox-label"><input type="checkbox" /> Near mint</label>
            <label className="checkbox-label"><input type="checkbox" /> Lightly used</label>
            <span className="more-dots">...</span>
          </div>

          <div className="sort-group">
            <span className="filter-label">Sort by</span>
            <select className="sort-dropdown">
              <option>Newest</option>
              <option>Most Expensive</option>
              <option>Most Inexpensive</option>
            </select>
          </div>
        </div>

        {/* GRID GALERI KARTU (Akan berderet ke bawah secara otomatis) */}
        <div className="card-gallery-grid">
          {cardsData.map((card) => (
            <div key={card.id} className="gallery-card-item">
              <div className="card-image-wrapper">
                <img src={card.image} alt={card.name} className="card-image" />
              </div>
              
              <div className="card-details-mini">
                <div className="detail-row">
                  <span className="card-name-mini">{card.name}</span>
                  <span className="card-price-mini">{card.price}</span>
                </div>
                
                <div className="detail-row">
                  <span className="card-rarity-text">{card.rarityText}</span>
                  <span className="flag-icon-mini">🇬🇧</span>
                </div>
                
                <div className="detail-row footer-row">
                  <span className="rarity-icon-badge">{card.rarityIcon}</span>
                  <span className="set-badge">{card.set}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

export default CatalogPage;