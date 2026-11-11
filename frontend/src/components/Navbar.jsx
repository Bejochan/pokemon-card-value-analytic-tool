import { useState } from 'react';
import './Navbar.css';

function Navbar({ currentPage = 'home', onNavigate }) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const handleLinkClick = (page) => {
    if (onNavigate) onNavigate(page);
    setIsMobileOpen(false);
  };

  return (
    <nav className="navbar">
      {/* KIRI: Logo */}
      <div className="navbar-left">
        <img src="/pokemon-logo.png" alt="Pokemon Logo" className="logo" />
      </div>

      {/* TENGAH: Menu Navigasi (Teks Kapital Asli Milikmu) */}
      <div className={`navbar-center ${isMobileOpen ? 'mobile-open' : ''}`}>
        <a 
          href="#home" 
          className="nav-link" 
          aria-current={currentPage === 'home' ? 'page' : undefined}
          onClick={() => handleLinkClick('home')}
        >
          HOME
        </a>
        <a 
          href="#catalog" 
          className="nav-link" 
          aria-current={currentPage === 'catalog' ? 'page' : undefined}
          onClick={() => handleLinkClick('catalog')}
        >
          CATALOG
        </a>
        <a 
          href="#marketplace" 
          className="nav-link" 
          aria-current={currentPage === 'marketplace' ? 'page' : undefined}
          onClick={() => handleLinkClick('marketplace')}
        >
          MARKETPLACE
        </a>
        <a 
          href="#dashboard" 
          className="nav-link" 
          aria-current={currentPage === 'dashboard' ? 'page' : undefined}
          onClick={() => handleLinkClick('dashboard')}
        >
          DASHBOARD
        </a>
      </div>

      {/* KANAN: Tombol Pencarian Cepat & Tombol HP */}
      <div className="navbar-right">
        <button 
          className="icon-btn" 
          title="Cari di Katalog"
          onClick={() => handleLinkClick('catalog')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>

        {/* Tombol Hamburger Hanya Muncul di HP */}
        <button 
          className="mobile-hamburger-btn" 
          onClick={() => setIsMobileOpen(prev => !prev)}
          aria-label="Toggle menu"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
    </nav>
  );
}

export default Navbar;