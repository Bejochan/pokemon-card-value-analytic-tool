import React, { useState } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import UploadPage from './components/UploadPage';
import ScannerDashboard from './components/ScannerDashboard';

function App() {
  const [currentPage, setCurrentPage] = useState('home');

  return (
    <div>
      <Navbar />
      
      {/* Trik React: Atribut 'key' memaksa animasi CSS diputar ulang tiap state berubah */}
      <div key={currentPage} className="page-transition">
        
        {currentPage === 'home' && (
          <HeroSection onNavigate={() => setCurrentPage('upload')} />
        )}

        {currentPage === 'upload' && (
          <UploadPage onUploadComplete={() => setCurrentPage('result')} />
        )}

        {currentPage === 'result' && (
          <ScannerDashboard />
        )}
        
      </div>
    </div>
  );
}

export default App;