import { useState, useEffect, Component } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import UploadPage from './components/UploadPage';
import ScannerDashboard from './components/ScannerDashboard';
import CatalogPage from './components/CatalogPage';
import DashboardPage from './components/DashboardPage';
import Marketplace from './components/Marketplace';

const VALID_PAGES = ['home', 'upload', 'result', 'catalog', 'dashboard', 'marketplace'];

// =========================================================================
// 1. ERROR BOUNDARY: Jaring Pengaman agar Website Tidak Menjadi Blank Screen
// =========================================================================
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[ErrorBoundary] Terjadi error pada komponen anak:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '60px 20px', textAlign: 'center', fontFamily: "'Montserrat', sans-serif" }}>
          <h2 style={{ color: '#1e1b4b', marginBottom: '8px' }}>Terjadi kesalahan saat memuat tampilan</h2>
          <p style={{ color: '#64748b', marginBottom: '24px' }}>Komponen mengalami kendala. Silakan muat ulang atau kembali ke beranda.</p>
          <button 
            onClick={() => {
              this.setState({ hasError: false });
              window.location.hash = 'home';
              window.location.reload();
            }}
            style={{
              padding: '10px 24px',
              backgroundColor: '#c2185b',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontFamily: "'Montserrat', sans-serif"
            }}
          >
            Kembali ke Beranda
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// =========================================================================
// 2. KOMPONEN UTAMA APP
// =========================================================================
function App() {
  const [currentPage, setCurrentPage] = useState(() => {
    const hash = window.location.hash.replace('#', '').toLowerCase();
    return VALID_PAGES.includes(hash) ? hash : 'home';
  });

  // Memulihkan scanResult dari sessionStorage jika halaman di-refresh (F5)
  const [scanResult, setScanResult] = useState(() => {
    try {
      const saved = sessionStorage.getItem('regokemon_scan_result');
      return saved ? JSON.parse(saved) : null;
    } catch (err) {
      console.error("Gagal membaca sessionStorage:", err);
      return null;
    }
  });

  // Fungsi helper untuk menyimpan/memperbarui scanResult di memory & sessionStorage
  const handleSetScanResult = (resultData) => {
    setScanResult(resultData);
    if (resultData) {
      try {
        sessionStorage.setItem('regokemon_scan_result', JSON.stringify(resultData));
      } catch (err) {
        console.error("Gagal menyimpan ke sessionStorage:", err);
      }
    } else {
      sessionStorage.removeItem('regokemon_scan_result');
    }
  };

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

  // Mencegah halaman result terbuka saat scanResult null (otomatis kembali ke upload)
  useEffect(() => {
    if (currentPage === 'result' && !scanResult) {
      const timer = setTimeout(() => handleNavigate('upload'), 0);
      return () => clearTimeout(timer);
    }
  }, [currentPage, scanResult]);

  return (
    <ErrorBoundary>
      <div>
        {/* Navbar utama dengan sinkronisasi URL hash */}
        <Navbar currentPage={currentPage} onNavigate={handleNavigate} />
        
        {/* Trik React: Atribut 'key' memaksa animasi CSS diputar ulang tiap state berubah */}
        <div key={currentPage} className={currentPage === 'result' ? '' : 'page-transition'}>
          
          {currentPage === 'home' && (
            <HeroSection onNavigate={() => handleNavigate('upload')} />
          )}

          {currentPage === 'upload' && (
            <UploadPage 
              onUploadComplete={(resultData) => {
                handleSetScanResult(resultData);
                handleNavigate('result');
              }} 
            />
          )}

          {currentPage === 'result' && scanResult && (
            <ScannerDashboard 
              scanResult={scanResult} 
              onScanOther={() => {
                handleSetScanResult(null);
                handleNavigate('upload');
              }}
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
    </ErrorBoundary>
  );
}

export default App;