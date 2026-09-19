import React from 'react';
import './Navbar.css';

function Navbar() {
  return (
    <nav className="navbar">
      {/* KIRI: Logo */}
      <div className="navbar-left">
        <img src="/pokemon-logo.png" alt="Pokemon Logo" className="logo" />
      </div>

      {/* TENGAH: Menu Navigasi (Teks Kapital ala Lexar) */}
      <div className="navbar-center">
        <a href="#home" className="nav-link">HOME</a>
        <a href="#about" className="nav-link">ABOUT US</a>
        <a href="#resources" className="nav-link">RESOURCES</a>
      </div>

      {/* KANAN: Ikon Lokasi dan Pencarian */}
      <div className="navbar-right">
        {/* Ikon Lokasi (Pin) */}
        <button className="icon-btn" title="Location">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
            <circle cx="12" cy="10" r="3"></circle>
          </svg>
        </button>
        
        {/* Ikon Pencarian (Kaca Pembesar) */}
        <button className="icon-btn" title="Search">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>
      </div>
    </nav>
  );
}

export default Navbar;