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
      
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64String = reader.result;
        try {
          const response = await fetch('http://127.0.0.1:8000/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: base64String })
          });
          const data = await response.json();
          if (data.status === 'success') {
            onUploadComplete(data);
          } else {
            alert(data.message || 'Error dari AI');
          }
        } catch (error) {
          console.error('Error uploading file:', error);
          alert('Gagal terhubung ke backend');
        } finally {
          setIsUploading(false);
        }
      };
      reader.readAsDataURL(selectedFile);
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
    if (!videoRef.current) return;
    setIsScanning(true);
    
    // Buat canvas sementara untuk menangkap frame dari video
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    
    // Ubah gambar menjadi Base64
    const base64String = canvas.toDataURL('image/jpeg');

    setTimeout(async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64String })
        });
        const data = await response.json();
        if (data.status === 'success') {
          stopCamera();
          onUploadComplete(data);
        } else {
          alert(data.message || 'Error dari AI');
        }
      } catch (error) {
        console.error('Error scanning camera:', error);
        alert('Gagal terhubung ke backend');
      } finally {
        setIsScanning(false);
      }
    }, 1500); // Simulasi animasi scan sebentar
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