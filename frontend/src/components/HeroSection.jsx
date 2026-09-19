import React from 'react';
import './HeroSection.css';

function HeroSection({ onNavigate }) {
  return (
    <div className="hero-container">
      {/* --- VIDEO BACKGROUND DITAMBAHKAN DI SINI --- */}
      <video autoPlay loop muted playsInline className="video-background">
        <source src="/bg-hero.mp4" type="video/mp4" />
      </video>

      {/* Teks dan Tombol Utama */}
      <div className="hero-content">
        <h1 className="title">
          POKEMON CARD VALUE<br />DETECTOR
        </h1>
        <p className="subtitle">Unpack - Scan - Sell - Profit</p>
        
        <button className="scan-button" onClick={onNavigate}>
          <span className="text-pink">SCAN</span> <span className="text-black">NOW</span> <span className="text-pink">!</span>
        </button>
      </div>

      {/* 7 Dekorasi Kartu Melayang */}
      <img src="/card1.jpg" alt="Card 1" className="floating-card card-1" />
      <img src="/card2.jpg" alt="Card 2" className="floating-card card-2" />
      <img src="/card3.jpg" alt="Card 3" className="floating-card card-3" />
      <img src="/card4.jpg" alt="Card 4" className="floating-card card-4" />
      <img src="/card5.jpg" alt="Card 5" className="floating-card card-5" />
      <img src="/card6.jpg" alt="Card 6" className="floating-card card-6" />
      <img src="/card7.jpg" alt="Card 7" className="floating-card card-7" />
    </div>
  );
}

export default HeroSection;