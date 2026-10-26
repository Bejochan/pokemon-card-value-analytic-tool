import React, { useState } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import UploadPage from './components/UploadPage';
import ScannerDashboard from './components/ScannerDashboard';
import CatalogPage from './components/CatalogPage';
import DashboardPage from './components/DashboardPage';
import Marketplace from './components/Marketplace';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [scanResult, setScanResult] = useState(null);

  return (
    <div>
      {/* --- PERBAIKAN 1 --- */}
      {/* Tambahkan prop onNavigate ke Navbar utama agar tombolnya berfungsi */}
      <Navbar onNavigate={setCurrentPage} />
      
      {/* Trik React: Atribut 'key' memaksa animasi CSS diputar ulang tiap state berubah */}
      <div key={currentPage} className={currentPage === 'result' ? '' : 'page-transition'}>
        
        {currentPage === 'home' && (
          <HeroSection onNavigate={() => setCurrentPage('upload')} />
        )}

        {currentPage === 'upload' && (
          <UploadPage 
            onUploadComplete={(resultData) => {
              setScanResult(resultData);
              setCurrentPage('result');
            }} 
          />
        )}

        {currentPage === 'result' && (
          <ScannerDashboard 
            scanResult={scanResult} 
            onScanOther={() => setCurrentPage('upload')}
          />
        )}

        {/* --- PERBAIKAN 2 --- */}
        {/* Render CatalogPage saat state currentPage adalah 'catalog' */}
        {currentPage === 'catalog' && (
          <CatalogPage />
        )}
        
        {currentPage === 'dashboard' && (
          <DashboardPage />
        )}

      </div>
    </div>
  );
}

export default App;