import React, { useState } from 'react';
import './Marketplace.css';

// ==========================================
// DUMMY DATA UNTUK KARTU MARKETPLACE
// ==========================================
const mockCards = [
  {
    id: 1,
    name: 'Deoxys VSTAR',
    price: 12.00,
    rarityName: 'Common',
    language: 'UK', // 'UK', 'ID', 'JP'
    raritySymbol: 'circle', // 'circle', 'star', 'double-star'
    rarityAbbr: 'C',
    setTag: 'M2a',
    saved: true,
    imgUrl: 'https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?q=80&w=400&auto=format&fit=crop'
  },
  {
    id: 2,
    name: 'Deoxys VSTAR',
    price: 12.00,
    rarityName: 'Special Illustration Rare',
    language: 'UK',
    raritySymbol: 'double-star',
    rarityAbbr: 'SAR',
    setTag: 'V2a',
    saved: true,
    imgUrl: 'https://images.unsplash.com/photo-1627856013091-fed6e4e30025?q=80&w=400&auto=format&fit=crop'
  },
  {
    id: 3,
    name: 'Deoxys VSTAR',
    price: 10.00,
    rarityName: 'Illustration Rare',
    language: 'JP',
    raritySymbol: 'star',
    rarityAbbr: 'AR',
    setTag: 'N2a',
    saved: true,
    imgUrl: 'https://images.unsplash.com/photo-1613771404721-1f92d799e49f?q=80&w=400&auto=format&fit=crop'
  },
  {
    id: 4,
    name: 'Deoxys VSTAR',
    price: 11.00,
    rarityName: 'Common',
    language: 'UK',
    raritySymbol: 'circle',
    rarityAbbr: 'C',
    setTag: 'N2a',
    saved: true,
    imgUrl: 'https://images.unsplash.com/photo-1643725173053-ed68676f1878?q=80&w=400&auto=format&fit=crop'
  },
  {
    id: 5,
    name: 'Deoxys VSTAR',
    price: 9.00,
    rarityName: 'Double Rare',
    language: 'ID',
    raritySymbol: 'double-star',
    rarityAbbr: 'RR',
    setTag: 'N2a',
    saved: true,
    imgUrl: 'https://images.unsplash.com/photo-1613771810034-754668b5a037?q=80&w=400&auto=format&fit=crop'
  },
  {
    id: 6,
    name: 'Deoxys VMAX',
    price: 15.00,
    rarityName: 'Ultra Rare',
    language: 'UK',
    raritySymbol: 'star',
    rarityAbbr: 'UR',
    setTag: 'M2a',
    saved: false,
    imgUrl: 'https://images.unsplash.com/photo-1636109968430-8beaf8e24483?q=80&w=400&auto=format&fit=crop'
  },
  {
    id: 7,
    name: 'Deoxys V',
    price: 4.50,
    rarityName: 'Rare',
    language: 'JP',
    raritySymbol: 'star',
    rarityAbbr: 'R',
    setTag: 'V2a',
    saved: false,
    imgUrl: 'https://images.unsplash.com/photo-1627856014754-2907e2bea5b5?q=80&w=400&auto=format&fit=crop'
  }
];

// ==========================================
// KOMPONEN IKON SVG (Inline untuk kemandirian file)
// ==========================================
const SearchIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#475086" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const BookmarkIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor">
    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
  </svg>
);

const ChevronDownIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#475086" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

// Ikon Bendera Simpel (Menggunakan Emoji untuk stabilitas rendering)
const FlagIcon = ({ lang }) => {
  const flags = {
    'UK': '🇬🇧',
    'ID': '🇮🇩',
    'JP': '🇯🇵'
  };
  return <span className="text-sm leading-none" title={lang}>{flags[lang]}</span>;
};

// Ikon Simbol Kelangkaan (Rarity)
const RarityIcon = ({ type }) => {
  if (type === 'circle') return <span className="inline-block w-2 h-2 bg-black rounded-full mx-1"></span>;
  if (type === 'star') return (
    <svg viewBox="0 0 24 24" width="10" height="10" fill="#f59e0b" className="mx-1 inline-block">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
    </svg>
  );
  if (type === 'double-star') return (
    <div className="inline-flex mx-1">
      <svg viewBox="0 0 24 24" width="10" height="10" fill="#1e293b"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
      <svg viewBox="0 0 24 24" width="10" height="10" fill="#1e293b" className="-ml-1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
    </div>
  );
  return null;
};

// ==========================================
// KOMPONEN UTAMA
// ==========================================
export default function Marketplace() {
  const [searchQuery, setSearchQuery] = useState('Deaoxys VSTAR');
  
  return (
    <div className="min-h-screen flex flex-col font-sans bg-white">
      
      {/* --- INJECT CUSTOM CSS --- */}
      <style>{`
        .bg-checkerboard {
          background-color: #f7d560;
          background-image: 
            linear-gradient(45deg, #f3c745 25%, transparent 25%, transparent 75%, #f3c745 75%, #f3c745), 
            linear-gradient(45deg, #f3c745 25%, transparent 25%, transparent 75%, #f3c745 75%, #f3c745);
          background-size: 60px 60px;
          background-position: 0 0, 30px 30px;
        }
        
        .market-dotted-line {
          flex-grow: 1;
          height: 1px;
          border-bottom: 2px dotted #cbd5e1;
          margin: 0 6px;
          position: relative;
          top: -3px; /* Penyesuaian vertikal agar sejajar dengan teks */
        }

        /* Menyembunyikan scrollbar di kontainer grid agar rapi */
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .hide-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>

      {/* --- MOCK NAVBAR --- */}
      <nav className="h-16 flex items-center justify-between px-8 bg-white border-b shadow-sm z-10 sticky top-0">
        <div className="text-2xl font-black text-blue-600 tracking-tighter" style={{ textShadow: '2px 2px 0px #fbbf24' }}>
          Regokemon
        </div>
        <div className="hidden md:flex items-center space-x-8 text-sm font-bold text-pink-500 uppercase tracking-wide">
          <a href="#" className="hover:text-pink-600">Home</a>
          <a href="#" className="hover:text-pink-600">Catalog</a>
          <a href="#" className="hover:text-pink-600">Dashboard</a>
          <a href="#" className="border-b-2 border-pink-500 pb-1">Marketplace</a>
          <a href="#" className="hover:text-pink-600">About Us</a>
          <a href="#" className="hover:text-pink-600">Resources</a>
        </div>
        <div className="flex items-center space-x-4 text-pink-500">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
        </div>
      </nav>

      {/* --- AREA CHECKERBOARD (SEARCH & CONTAINER) --- */}
      <div className="bg-checkerboard flex-1 flex flex-col pt-8">
        
        {/* Search Bar & Saved Items Button */}
        <div className="w-full max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4 mb-8">
          
          <div className="relative w-full md:max-w-2xl flex-1 shadow-lg rounded-full">
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cards..."
              className="w-full h-14 pl-6 pr-12 rounded-full border-2 border-blue-900/20 outline-none text-lg font-medium text-gray-700 bg-white placeholder-gray-400 focus:border-pink-500 transition-colors"
            />
            <div className="absolute right-4 top-1/2 transform -translate-y-1/2 cursor-pointer">
              <SearchIcon />
            </div>
          </div>

          <button className="flex items-center gap-2 bg-white px-6 py-3.5 rounded-full shadow-lg border-2 border-transparent hover:border-pink-200 transition-all group">
            <span className="text-pink-500 font-bold text-sm tracking-wide">Saved Items</span>
            <BookmarkIcon className="w-5 h-5 text-pink-500 group-hover:scale-110 transition-transform" />
          </button>
          
        </div>

        {/* --- BLUE CONTAINER (MAIN CONTENT) --- */}
        <div className="bg-[#475086] w-full flex-1 rounded-t-[40px] shadow-2xl px-6 md:px-12 pt-8 pb-16 flex flex-col">
          
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center gap-6 mb-8 text-white font-medium text-sm">
            
            <div className="flex items-center gap-3">
              <span className="font-bold tracking-wide">Sort by</span>
              <div className="relative bg-white text-gray-800 rounded-lg px-4 py-2 flex items-center justify-between min-w-[140px] cursor-pointer shadow-sm">
                <span>A - Z</span>
                <ChevronDownIcon />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="font-bold tracking-wide">Rarity</span>
              <div className="relative bg-white text-gray-800 rounded-lg px-4 py-2 flex items-center justify-between min-w-[140px] cursor-pointer shadow-sm">
                <span>Ultra Rare</span>
                <ChevronDownIcon />
              </div>
            </div>

            <div className="flex items-center gap-3 ml-2">
              <span className="font-bold tracking-wide">Language</span>
              <div className="flex items-center gap-2 bg-white/10 rounded-full px-2 py-1 border border-white/20">
                <div className="w-6 h-6 rounded-full overflow-hidden flex items-center justify-center bg-white cursor-pointer hover:ring-2 ring-pink-500"><FlagIcon lang="UK" /></div>
                <div className="w-6 h-6 rounded-full overflow-hidden flex items-center justify-center bg-white cursor-pointer hover:ring-2 ring-pink-500"><FlagIcon lang="ID" /></div>
                <div className="w-6 h-6 rounded-full overflow-hidden flex items-center justify-center bg-white cursor-pointer hover:ring-2 ring-pink-500"><FlagIcon lang="JP" /></div>
              </div>
            </div>

            <div className="flex items-center gap-3 ml-auto">
              <input type="text" placeholder="$ lowest" className="w-24 px-3 py-2 rounded-lg text-gray-800 outline-none focus:ring-2 ring-pink-500" />
              <span className="text-white/60">—</span>
              <input type="text" placeholder="$ highest" className="w-24 px-3 py-2 rounded-lg text-gray-800 outline-none focus:ring-2 ring-pink-500" />
            </div>

          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {mockCards.map((card) => (
              <div key={card.id} className="bg-white rounded-xl p-3 flex flex-col relative shadow-lg transform transition duration-200 hover:-translate-y-1 hover:shadow-xl group cursor-pointer">
                
                {/* Floating Bookmark */}
                {card.saved && (
                  <div className="absolute -top-1 right-3 z-10 text-pink-500 filter drop-shadow-md">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                    </svg>
                  </div>
                )}

                {/* Card Image */}
                <div className="w-full aspect-[63/88] rounded-lg overflow-hidden mb-3 bg-gray-100 flex items-center justify-center border border-gray-200">
                  <img 
                    src={card.imgUrl} 
                    alt={card.name} 
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                </div>

                {/* Card Info Area */}
                <div className="flex flex-col flex-1 px-1">
                  
                  {/* Row 1: Name & Price */}
                  <div className="flex justify-between items-start mb-1.5">
                    <span className="font-semibold text-gray-800 text-[13px] leading-tight truncate pr-2">
                      {card.name}
                    </span>
                    <span className="font-bold text-[#00d26a] text-[13px] whitespace-nowrap">
                      $ {card.price.toFixed(2)}
                    </span>
                  </div>

                  {/* Row 2: Rarity Name, Dotted Line, Flag */}
                  <div className="flex items-center w-full mb-2">
                    <span className="text-[10px] font-medium text-gray-600 truncate max-w-[60%]">
                      {card.rarityName}
                    </span>
                    <div className="market-dotted-line"></div>
                    <div className="flex-shrink-0 relative top-[1px]">
                      <FlagIcon lang={card.language} />
                    </div>
                  </div>

                  {/* Row 3: Rarity Icon/Abbr & Set Logo */}
                  <div className="flex justify-between items-end mt-auto pt-1">
                    <div className="flex items-center">
                      <RarityIcon type={card.raritySymbol} />
                      <span className="text-[11px] font-bold text-gray-800 ml-1">{card.rarityAbbr}</span>
                    </div>
                    <div className="bg-black text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-sm">
                      {card.setTag}
                    </div>
                  </div>

                </div>
              </div>
            ))}

            {/* Empty Placeholders (to match layout look) */}
            <div className="bg-white rounded-xl min-h-[300px] opacity-80 shadow-md"></div>
            <div className="bg-white rounded-xl min-h-[300px] opacity-80 shadow-md"></div>
            
          </div>
        </div>
      </div>
    </div>
  );
}