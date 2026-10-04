import React from 'react';
import './Navbar.css';

// Tambahkan { onNavigate } di sini untuk menerima perintah pindah halaman
function Navbar({ onNavigate }) {
  return (
    <nav className="navbar">
      {/* KIRI: Logo */}
      <div className="navbar-left">
        <img src="/pokemon-logo.png" alt="Pokemon Logo" className="logo" />
      </div>

      {/* TENGAH: Menu Navigasi (Teks Kapital) */}
      <div className="navbar-center">
        {/* Tambahkan onClick untuk memicu perpindahan halaman */}
        <a href="#home" className="nav-link" onClick={() => onNavigate('home')}>HOME</a>
        {/* Ini adalah tombol Catalog yang baru di tengah */}
        <a href="#catalog" className="nav-link" onClick={() => onNavigate('catalog')}>CATALOG</a>
        <a href="#dashboard" className="nav-link" onClick={() => onNavigate('dashboard')}>DASHBOARD</a>
        <a href="#about" className="nav-link">ABOUT US</a>
        <a href="#resources" className="nav-link">RESOURCES</a>
      </div>

      {/* KANAN: Ikon Lokasi dan Pencarian */}
      <div className="navbar-right">
        <button className="icon-btn" title="Location">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
            <circle cx="12" cy="10" r="3"></circle>
          </svg>
        </button>
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