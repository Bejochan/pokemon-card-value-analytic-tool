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
        <a href="#catalog" className="nav-link" onClick={() => onNavigate('catalog')}>CATALOG</a>
        <a href="#dashboard" className="nav-link" onClick={() => onNavigate('dashboard')}>DASHBOARD</a>
      </div>

      {/* KANAN: Tombol Pencarian Cepat */}
      <div className="navbar-right">
        <button 
          className="icon-btn" 
          title="Cari di Katalog"
          onClick={() => onNavigate && onNavigate('catalog')}
        >
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