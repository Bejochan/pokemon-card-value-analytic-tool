import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import UploadPage from './components/UploadPage';
import ScannerDashboard from './components/ScannerDashboard';
import CatalogPage from './components/CatalogPage';
import DashboardPage from './components/DashboardPage';
import Marketplace from './components/Marketplace';

const VALID_PAGES = ['home', 'upload', 'result', 'catalog', 'dashboard', 'marketplace'];

function App() {
  const [currentPage, setCurrentPage] = useState(() => {
    const hash = window.location.hash.replace('#', '').toLowerCase();
    return VALID_PAGES.includes(hash) ? hash : 'home';
  });
  const [scanResult, setScanResult] = useState(null);

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').toLowerCase();
      if (VALID_PAGES.includes(hash)) {
        setCurrentPage(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleNavigate = (page) => {
    setCurrentPage(page);
    window.location.hash = page;
  };

  return (
    <div>
      {/* Navbar utama dengan sinkronisasi URL hash */}
      <Navbar onNavigate={handleNavigate} />
      
      {/* Trik React: Atribut 'key' memaksa animasi CSS diputar ulang tiap state berubah */}
      <div key={currentPage} className={currentPage === 'result' ? '' : 'page-transition'}>
        
        {currentPage === 'home' && (
          <HeroSection onNavigate={() => handleNavigate('upload')} />
        )}

        {currentPage === 'upload' && (
          <UploadPage 
            onUploadComplete={(resultData) => {
              setScanResult(resultData);
              handleNavigate('result');
            }} 
          />
        )}

        {currentPage === 'result' && (
          <ScannerDashboard 
            scanResult={scanResult} 
            onScanOther={() => handleNavigate('upload')}
          />
        )}

        {currentPage === 'catalog' && (
          <CatalogPage />
        )}
        
        {currentPage === 'dashboard' && (
          <DashboardPage />
        )}

        {currentPage === 'marketplace' && (
          <Marketplace />
        )}

      </div>
    </div>
  );
}

export default App;