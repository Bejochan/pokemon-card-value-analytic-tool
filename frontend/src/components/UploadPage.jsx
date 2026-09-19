import React, { useState, useRef, useEffect } from 'react';
import './UploadPage.css';

function UploadPage({ onUploadComplete }) {
  const [isUploading, setIsUploading] = useState(false);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null); // Menyimpan referensi aliran video agar bisa dimatikan nanti

  // --- LOGIKA UPLOAD FILE ---
  const handleBrowseClick = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setIsUploading(true);
      setTimeout(() => {
        setIsUploading(false);
        onUploadComplete();
      }, 3000);
    }
  };

  // --- LOGIKA KAMERA ---
  const openCamera = async () => {
    try {
      // Meminta akses video ke browser
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      setIsCameraOpen(true);
    } catch (err) {
      console.error("Gagal mengakses kamera:", err);
      alert("Tidak dapat mengakses kamera. Pastikan memberi izin pada browser!");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      // Mematikan semua jalur video (mematikan lampu indikator kamera laptop)
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsCameraOpen(false);
  };

  const handleCameraScan = () => {
    setIsScanning(true);
    // Simulasi pura-pura memindai wajah kartu
    setTimeout(() => {
      setIsScanning(false);
      stopCamera(); // Matikan kamera sebelum pindah halaman
      onUploadComplete();
    }, 3000);
  };

  // --- PENGAMANAN ---
  // Menyambungkan aliran video ke elemen HTML saat kamera terbuka
  useEffect(() => {
    if (isCameraOpen && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [isCameraOpen]);

  // Memastikan kamera mati jika komponen ini tiba-tiba ditutup/berpindah
  useEffect(() => {
    return () => stopCamera();
  }, []);

  return (
    <div className="upload-container">
      <img src="/card-back-left.png" alt="Card Left" className="bg-card left-card" />
      <img src="/card-back-right.png" alt="Card Right" className="bg-card right-card" />

      <div className="device-frame">
        <div className="upload-screen">
          
          {/* JIKA KAMERA TERBUKA */}
          {isCameraOpen ? (
            <div className="camera-view">
              {isScanning ? (
                <div className="scanning-animation">
                  <p>Scanning...</p>
                  <div className="laser-beam"></div>
                </div>
              ) : (
                <>
                  <video ref={videoRef} autoPlay playsInline className="video-feed" />
                  <div className="camera-controls">
                    <button className="scan-btn" onClick={handleCameraScan}>SCAN</button>
                    <button className="cancel-btn" onClick={stopCamera}>CANCEL</button>
                  </div>
                </>
              )}
            </div>
          ) : (
            
          /* JIKA KAMERA TERTUTUP (TAMPILAN DEFAULT) */
            <div className="upload-content-wrapper">
              {isUploading ? (
                <div className="scanning-animation">
                  <p>Uploading File...</p>
                  <div className="laser-beam"></div>
                </div>
              ) : (
                <>
                  <div className="drop-zone">
                    <div className="upload-icon">☁️</div>
                    <p className="main-text">select your file or drag and drop</p>
                    <p className="sub-text">png, pdf, jpg, docx accepted</p>
                    
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      style={{ display: 'none' }} 
                      onChange={handleFileChange} 
                      accept=".png, .jpg, .jpeg" 
                    />
                    <button className="browse-btn" onClick={handleBrowseClick}>BROWSE</button>
                  </div>

                  <p className="or-text">— OR —</p>
                  
                  <button className="open-camera-btn" onClick={openCamera}>
                    OPEN CAMERA
                  </button>
                </>
              )}
            </div>
          )}
          
        </div>
      </div>
    </div>
  );
}

export default UploadPage;