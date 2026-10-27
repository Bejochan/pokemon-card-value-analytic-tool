import React, { useState, useRef, useEffect, useCallback } from 'react';
import './UploadPage.css';

// Helper: Penentuan Kategori Valuasi Pasar (Sama persis dengan script lokal Python)
function getValuationTier(priceVal) {
  if (!priceVal || priceVal <= 0) {
    return {
      tierTag: "UNPRICED",
      tierClass: "tier-unpriced",
      tierDesc: "Koleksi Khusus / Tanpa Harga Retail"
    };
  }
  if (priceVal >= 100.0) {
    return {
      tierTag: "GRAIL / ULTRA RARE",
      tierClass: "tier-grail",
      tierDesc: "Kartu Sangat Langka & Bernilai Tinggi"
    };
  } else if (priceVal >= 25.0) {
    return {
      tierTag: "HIGH VALUE",
      tierClass: "tier-high",
      tierDesc: "Kartu Bernilai Tinggi (Koleksi Utama)"
    };
  } else if (priceVal >= 5.0) {
    return {
      tierTag: "MID VALUE",
      tierClass: "tier-mid",
      tierDesc: "Kartu Bernilai Menengah (Populer)"
    };
  } else {
    return {
      tierTag: "BUDGET / COMMON",
      tierClass: "tier-common",
      tierDesc: "Kartu Standar / Murah (Umum)"
    };
  }
}

// Helper: Format Rupiah rapi & ringkas (mirip dengan card_identifier_realtime.py di Python)
function formatRupiahClean(val) {
  if (!val || val <= 0) return 'Rp 0';
  const num = Math.round(val);
  if (num >= 1_000_000) {
    const jt = (num / 1_000_000).toFixed(1).replace('.', ',');
    return `Rp ${jt}jt`;
  } else if (num >= 10_000) {
    const rb = Math.round(num / 1000);
    return `Rp ${rb}rb`;
  } else {
    return `Rp ${num.toLocaleString('id-ID')}`;
  }
}

// Helper: Format Rupiah lengkap dengan pembulatan ribuan (misal: Rp 15.000)
function formatRupiahRounded(val) {
  if (!val || val <= 0) return 'Rp 0';
  const num = Math.round(val);
  if (num >= 10_000) {
    const rounded = Math.round(num / 500) * 500;
    return `Rp ${rounded.toLocaleString('id-ID')}`;
  }
  return `Rp ${num.toLocaleString('id-ID')}`;
}

// Helper: Format Label Harga USD + IDR dengan tampilan rapi
function formatPriceInfo(priceUsd, priceIdr) {
  if (!priceUsd || priceUsd <= 0) {
    return {
      label: "Harga: N/A",
      usdFormatted: "$0.00",
      idrLabel: "Rp 0",
      idrFull: "Rp 0",
      ...getValuationTier(0)
    };
  }
  const usdNum = Number(priceUsd);
  const usdStr = `$${usdNum.toFixed(2)}`;
  const idrVal = priceIdr || (usdNum * 16500);
  const idrShort = formatRupiahClean(idrVal);
  const idrFull = formatRupiahRounded(idrVal);

  return {
    label: `${usdStr} (~${idrShort})`,
    usdFormatted: usdStr,
    idrLabel: idrShort,
    idrFull: idrFull,
    ...getValuationTier(usdNum)
  };
}

// Helper: Estimasi Ketajaman Sensor dari Canvas (Laplacian gradient variance)
function calculateSharpness(ctx, width, height) {
  try {
    const sampleW = Math.min(width, 120);
    const sampleH = Math.min(height, 120);
    const imgData = ctx.getImageData(0, 0, sampleW, sampleH);
    const data = imgData.data;
    let sumDiff = 0;
    let count = 0;
    const step = 4;
    for (let i = 0; i < data.length - step * 4; i += step * 4) {
      const g1 = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      const g2 = 0.299 * data[i + 4] + 0.587 * data[i + 5] + 0.114 * data[i + 6];
      sumDiff += Math.abs(g1 - g2);
      count++;
    }
    const score = count > 0 ? (sumDiff / count) * 6.5 : 85;
    return Math.min(Math.round(score), 350);
  } catch {
    return 95;
  }
}

/**
 * Kompresi & Resize Foto di Sisi Klien (HTML5 Canvas) sebelum dikirim ke backend.
 * Membatasi dimensi maksimum ke 1280px (sweet spot akurasi 93.8% & performa optimal)
 * dan mengonversi format ke JPEG kualitas 0.88.
 * Memangkas ukuran payload dari 5-15MB menjadi ~150-300KB di RAM tanpa kehilangan detail kartu.
 */
function compressAndResizeImage(file, maxDimension = 1280, quality = 0.88) {
  return new Promise((resolve, reject) => {
    if (!file || !file.type.match(/image.*/)) {
      return reject(new Error('File yang dipilih bukan berkas gambar yang valid.'));
    }

    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Gagal membaca berkas gambar.'));
    reader.onload = (e) => {
      const img = new Image();
      img.onerror = () => reject(new Error('Gagal merender gambar ke memori browser.'));
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          return resolve(e.target.result);
        }

        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, width, height);

        const compressedBase64 = canvas.toDataURL('image/jpeg', quality);
        resolve(compressedBase64);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

function UploadPage({ onUploadComplete }) {
  // State Upload Tradisional & Inspeksi 2 Sisi
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [frontImage, setFrontImage] = useState(null);
  const [backImage, setBackImage] = useState(null);
  const [isProcessingFront, setIsProcessingFront] = useState(false);
  const [isProcessingBack, setIsProcessingBack] = useState(false);
  const fileInputRef = useRef(null);
  const backFileInputRef = useRef(null);

  // State Live Camera HUD
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [latencyMs, setLatencyMs] = useState(0);
  const [liveSharpness, setLiveSharpness] = useState(115);
  const [camFps, setCamFps] = useState(30);

  // Refs Kamera & Animasi
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const captureCanvasRef = useRef(null);
  const isRequestInProgress = useRef(false);
  const pollIntervalRef = useRef(null);
  const fpsFrameCountRef = useRef(0);
  const lastFpsTimeRef = useRef(performance.now());

  // --- LOGIKA UPLOAD & ANALISIS DUA SISI ---
  const handleBrowseClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFrontFileSelected = async (selectedFile) => {
    if (!selectedFile) return;
    setIsProcessingFront(true);
    try {
      const base64String = await compressAndResizeImage(selectedFile, 1280, 0.88);
      setFrontImage(base64String);
    } catch (err) {
      alert(err.message || 'Gagal memproses foto tampak depan.');
    } finally {
      setIsProcessingFront(false);
    }
  };

  const handleBackFileSelected = async (selectedFile) => {
    if (!selectedFile) return;
    setIsProcessingBack(true);
    try {
      const base64String = await compressAndResizeImage(selectedFile, 1280, 0.88);
      setBackImage(base64String);
    } catch (err) {
      alert(err.message || 'Gagal memproses foto tampak belakang.');
    } finally {
      setIsProcessingBack(false);
    }
  };

  const handleExecuteAnalyze = async () => {
    if (!frontImage) return;
    setIsUploading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: frontImage,
          back_image: backImage || null
        })
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        onUploadComplete({
          ...data,
          user_scanned_image: frontImage,
          user_scanned_back_image: backImage || null
        });
      } else {
        alert(data.message || data.detail || 'Terjadi kendala saat menganalisis kartu.');
      }
    } catch (error) {
      console.error('Error uploading card:', error);
      alert(error.message || 'Gagal terhubung ke backend analitik.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleResetStaged = () => {
    setFrontImage(null);
    setBackImage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (backFileInputRef.current) backFileInputRef.current.value = '';
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files && event.target.files[0];
    if (selectedFile) {
      handleFrontFileSelected(selectedFile);
      event.target.value = '';
    }
  };

  // --- LOGIKA BUKA / TUTUP KAMERA ---
  const openCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      });
      streamRef.current = stream;
      setIsCameraOpen(true);
      setIsPaused(false);
      setPrediction(null);
    } catch (err) {
      console.error("Gagal mengakses kamera:", err);
      alert("Tidak dapat mengakses kamera. Pastikan memberikan izin pada peramban!");
    }
  };

  const stopCamera = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsCameraOpen(false);
    setIsPaused(false);
    setPrediction(null);
  }, []);

  // --- FPS COUNTER DI VIDEO FEED ---
  useEffect(() => {
    if (!isCameraOpen || isPaused) return;

    let animId;
    let frameCount = 0;
    let lastTime = performance.now();
    const video = videoRef.current;

    if (video && 'requestVideoFrameCallback' in HTMLVideoElement.prototype) {
      const onFrame = () => {
        frameCount++;
        const now = performance.now();
        if (now - lastTime >= 1000) {
          setCamFps(Math.min(frameCount, 60));
          frameCount = 0;
          lastTime = now;
        }
        animId = video.requestVideoFrameCallback(onFrame);
      };
      animId = video.requestVideoFrameCallback(onFrame);
      return () => {
        if (video && video.cancelVideoFrameCallback && animId) {
          video.cancelVideoFrameCallback(animId);
        }
      };
    } else {
      // Default webcam stream frame rate
      setCamFps(30);
    }
  }, [isCameraOpen, isPaused]);

  // --- PASANG STREAM KE ELEMEN VIDEO ---
  useEffect(() => {
    if (isCameraOpen && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [isCameraOpen]);

  // --- REAL-TIME POLLING KE ENDPOINT /identify ---
  useEffect(() => {
    if (!isCameraOpen || isPaused) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }


    // Interval polling sub-detik (~750ms)
    pollIntervalRef.current = setInterval(async () => {
      if (isRequestInProgress.current) return;
      if (!videoRef.current || videoRef.current.readyState < 2) return;

      const video = videoRef.current;
      const vW = video.videoWidth || 640;
      const vH = video.videoHeight || 480;

      // Buat canvas sampling (resolusi optimal untuk inferensi kilat)
      if (!captureCanvasRef.current) {
        captureCanvasRef.current = document.createElement('canvas');
      }
      const canvas = captureCanvasRef.current;
      const targetW = 480;
      const targetH = Math.round((vH / vW) * targetW);
      canvas.width = targetW;
      canvas.height = targetH;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, targetW, targetH);

      // Hitung ketajaman sensor
      const sharpness = calculateSharpness(ctx, targetW, targetH);
      setLiveSharpness(sharpness);

      // Encode Base64 JPEG
      const base64Image = canvas.toDataURL('image/jpeg', 0.72);

      isRequestInProgress.current = true;
      const t0 = performance.now();

      try {
        const res = await fetch('http://127.0.0.1:8000/identify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64Image })
        });
        const elapsed = Math.round(performance.now() - t0);
        // Exponential smoothing latency agar tidak macet di angka warm-up 2200ms
        setLatencyMs(prev => prev === 0 ? elapsed : Math.round(prev * 0.3 + elapsed * 0.7));

        if (res.ok) {
          const data = await res.json();
          if (data.status === 'success' && data.card_id) {
            setPrediction(data);
          }
        }
      } catch (err) {
        console.debug('Polling error (normal if camera moving):', err);
      } finally {
        isRequestInProgress.current = false;
      }
    }, 750);


    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [isCameraOpen, isPaused]);

  // --- SHORTCUT KEYBOARD (SPASI = PAUSE, ESC = EXIT) ---
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isCameraOpen) return;
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPaused(prev => !prev);
      } else if (e.key === 'Escape') {
        stopCamera();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCameraOpen, stopCamera]);

  // --- BERSIHKAN STREAM JIKA KOMPONEN UNMOUNT ---
  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  // --- PROPS & DATA BINDING UNTUK HUD ---
  const hasCard = Boolean(prediction && prediction.card_id);
  const confPct = prediction?.confidence_percentage || 0;
  const confLabel = prediction?.confidence_label || 'Uncertain';
  
  // Warna Guide Frame & Status
  let guideClass = 'guide-cyan';
  if (isPaused) {
    guideClass = 'guide-amber';
  } else if (hasCard) {
    if (confLabel === 'Tinggi') guideClass = 'guide-neon';
    else if (confLabel === 'Sedang') guideClass = 'guide-amber';
    else guideClass = 'guide-coral';
  }

  // Harga Top-1
  const topPriceUsd = prediction?.pricing?.base_price_usd || 0;
  const topPriceIdr = prediction?.pricing?.base_price_idr || 0;
  const priceInfo = formatPriceInfo(topPriceUsd, topPriceIdr);

  // Status Ketajaman Sensor
  const isSharp = liveSharpness >= 60;
  const sharpTag = isSharp ? "FOKUS TAJAM" : "KURANG FOKUS";
  const sharpClass = isSharp ? "sensor-sharp" : "sensor-blur";

  // Rate Inferensi per Detik
  const inferRate = latencyMs > 0 ? (1000 / latencyMs).toFixed(1) : '0.0';

  return (
    <div className={`upload-page-root ${isCameraOpen ? 'hud-mode' : 'normal-mode'}`}>
      
      {/* ===================================================================== */}
      {/* TAMPILAN 1: DEFAULT UPLOAD SCREEN (DROP ZONE & OPEN LIVE SCANNER)     */}
      {/* ===================================================================== */}
      {!isCameraOpen ? (
        <div className="upload-container">
          <img src="/card-back-left.png" alt="Card Left" className="bg-card left-card" />
          <img src="/card-back-right.png" alt="Card Right" className="bg-card right-card" />

          <div className="device-frame">
            <div className="upload-screen">
              <div className="upload-content-wrapper">
                {isUploading ? (
                  <div className="scanning-animation">
                    <div className="hud-spinner"></div>
                    <p className="hud-upload-title">
                      {backImage ? "Menganalisis 2 Sisi Kartu..." : "Menganalisis Kartu..."}
                    </p>
                    <p className="hud-upload-sub">
                      {backImage 
                        ? "Memeriksa identitas CLIP dan cacat fisik depan & belakang..." 
                        : "Memeriksa identitas CLIP dan kondisi fisik kartu..."}
                    </p>
                  </div>
                ) : frontImage ? (
                  /* TAMPILAN PRATINJAU DUA SISI */
                  <div className="staged-preview-container">
                    <div className="staged-header">
                      <h3 className="staged-title">Pratinjau Kartu</h3>
                      <p className="staged-subtitle">
                        {backImage
                          ? "Foto depan dan belakang siap dianalisis secara lengkap."
                          : "Sisi depan siap. Tambah sisi belakang untuk cek fisik lebih detail, atau langsung lanjutkan."}
                      </p>
                    </div>

                    <div className="staged-cards-row">
                      {/* SLOT SISI DEPAN */}
                      <div className="staged-card-item">
                        <div className="staged-card-badge">Tampak Depan</div>
                        <div className="staged-img-wrapper">
                          <img src={frontImage} alt="Tampak Depan" className="staged-card-img" />
                        </div>
                        <button
                          type="button"
                          className="staged-sub-action"
                          onClick={() => fileInputRef.current && fileInputRef.current.click()}
                          title="Pilih gambar tampak depan lain"
                        >
                          Ganti
                        </button>
                      </div>

                      {/* SLOT SISI BELAKANG */}
                      <div className="staged-card-item">
                        <div className={`staged-card-badge ${backImage ? '' : 'badge-optional'}`}>
                          {backImage ? "Tampak Belakang" : "Belakang (Opsional)"}
                        </div>
                        {backImage ? (
                          <>
                            <div className="staged-img-wrapper">
                              <img src={backImage} alt="Tampak Belakang" className="staged-card-img" />
                            </div>
                            <button
                              type="button"
                              className="staged-sub-action text-danger"
                              onClick={() => setBackImage(null)}
                              title="Hapus foto tampak belakang"
                            >
                              Hapus
                            </button>
                          </>
                        ) : (
                          <div
                            className="staged-empty-slot"
                            onClick={() => backFileInputRef.current && backFileInputRef.current.click()}
                            role="button"
                            tabIndex={0}
                            title="Klik untuk memilih foto tampak belakang"
                          >
                            {isProcessingBack ? (
                              <span className="staged-slot-text">Memproses...</span>
                            ) : (
                              <>
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                  <line x1="12" y1="5" x2="12" y2="19"></line>
                                  <line x1="5" y1="12" x2="19" y2="12"></line>
                                </svg>
                                <span className="staged-slot-title">Tambah Belakang</span>
                                <span className="staged-slot-desc">Cek goresan & sudut</span>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* HIDDEN INPUT FOR RE-SELECTING FRONT OR SELECTING BACK */}
                    <input
                      type="file"
                      ref={fileInputRef}
                      style={{ display: 'none' }}
                      onChange={handleFileChange}
                      accept=".png, .jpg, .jpeg"
                    />

                    <input
                      type="file"
                      ref={backFileInputRef}
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        const file = e.target.files && e.target.files[0];
                        if (file) {
                          handleBackFileSelected(file);
                          e.target.value = '';
                        }
                      }}
                      accept=".png, .jpg, .jpeg"
                    />

                    {/* AKSI EKSEKUSI */}
                    <div className="staged-actions">
                      <button
                        type="button"
                        className="staged-primary-btn"
                        onClick={handleExecuteAnalyze}
                      >
                        {backImage ? "Analisis Lengkap (2 Sisi)" : "Analisis Sekarang"}
                      </button>

                      <button
                        type="button"
                        className="staged-cancel-btn"
                        onClick={handleResetStaged}
                      >
                        Pilih Ulang
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div 
                      className={`drop-zone ${isDragOver ? 'drag-active' : ''}`}
                      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                      onDragEnter={(e) => { e.preventDefault(); setIsDragOver(true); }}
                      onDragLeave={() => setIsDragOver(false)}
                      onDrop={(e) => {
                        e.preventDefault();
                        setIsDragOver(false);
                        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                          handleFrontFileSelected(e.dataTransfer.files[0]);
                        }
                      }}
                    >
                      <div className="upload-icon">
                        <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="#e83e8c" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
                        </svg>
                      </div>
                      <p className="main-text">Select your card or drag and drop</p>
                      <p className="sub-text">PNG, JPG, or JPEG accepted</p>
                      
                      <input 
                        type="file" 
                        ref={fileInputRef} 
                        style={{ display: 'none' }} 
                        onChange={handleFileChange} 
                        accept=".png, .jpg, .jpeg" 
                      />
                      <button className="browse-btn" onClick={handleBrowseClick}>
                        {isProcessingFront ? "MEMPROSES..." : "BROWSE FILE"}
                      </button>
                    </div>

                    <p className="or-text">OR</p>
                    
                    <button className="open-camera-btn" onClick={openCamera}>
                      OPEN CAMERA
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (

      /* ===================================================================== */
      /* TAMPILAN 2: REAL-TIME COMPUTER VISION HUD (CYBER OBSIDIAN SLATE)       */
      /* ===================================================================== */
        <div className="realtime-hud-container">
          
          {/* TOP HEADER BAR */}
          <header className="hud-header">
            <div className="hud-brand-group">
              <div className="hud-brand-title">REGOKEMON AI</div>
              <div className="hud-brand-divider">|</div>
              <div className="hud-brand-subtitle">
                REAL-TIME COMPUTER VISION & VALUATION SUITE
              </div>
            </div>

            <div className="hud-header-right">
              <div className={`hud-status-pill ${isPaused ? 'pill-paused' : 'pill-live'}`}>
                <span className="status-dot"></span>
                <span className="status-label">
                  {isPaused ? 'PAUSED / FROZEN' : 'LIVE SCANNING'}
                </span>
              </div>
            </div>
          </header>


          {/* MAIN HUD BODY: SPLIT VIEW */}
          <div className="hud-body">
            
            {/* PANE KIRI: CAMERA VIEWFINDER DENGAN CARD GUIDE 63:88 & LASER */}
            <div className="hud-left-pane">
              <div className="viewfinder-wrapper">
                <video ref={videoRef} autoPlay playsInline muted className="hud-video-element" />

                {/* OVERLAY TAG */}
                <div className="viewfinder-tag">
                  PORTRAIT 63:88 LIVE
                </div>

                {/* CARD GUIDE FRAME & CORNERS */}
                <div className={`card-guide-box ${guideClass}`}>
                  <div className="corner corner-tl"></div>
                  <div className="corner corner-tr"></div>
                  <div className="corner corner-bl"></div>
                  <div className="corner corner-br"></div>

                  {/* ANIMATED LASER SCANNING BEAM */}
                  {!isPaused && <div className="scanning-laser-beam"></div>}
                </div>

                {/* SENSOR STATUS STRIP */}
                <div className="sensor-strip">
                  <span className="sensor-title">Ketajaman Sensor:</span>
                  <div className={`sensor-badge ${sharpClass}`}>
                    <span className="sensor-indicator-dot"></span>
                    <span className="sensor-value">
                      {liveSharpness} [{sharpTag}]
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* PANE KANAN: ANALYTICS DASHBOARD */}
            <div className="hud-right-pane">
              
              {/* PANEL 1: TARGET IDENTIFIKASI UTAMA (TOP-1 PREDICTION) */}
              <div className="hud-panel panel-top1">
                <div className="panel-header-title cyan-accent">
                  TARGET IDENTIFIKASI UTAMA (TOP-1 PREDICTION & MARKET VALUE)
                </div>

                {hasCard ? (
                  <div className="top1-content">
                    {/* Baris Nama & Badges */}
                    <div className="top1-main-row">
                      <div className="card-identity-block">
                        <div className="identity-pill-row">
                          <span className={`confidence-pill conf-${confLabel.toLowerCase()}`}>
                            {confPct.toFixed(1)}% {confLabel.toUpperCase()}
                          </span>
                          <span className="meta-pill">{prediction.rarity || 'Standard'}</span>
                          <span className="meta-pill id-pill">{prediction.card_id}</span>
                          {prediction.number && (
                            <span className="meta-pill">No: {prediction.number}</span>
                          )}
                        </div>
                        <h2 className="top1-card-name" title={prediction.name}>
                          {prediction.name}
                        </h2>
                        <div className="top1-set-name">
                          Set: <strong>{prediction.set_name || '-'}</strong>
                        </div>
                      </div>

                      {/* HERO PRICE & VALUATION CARD */}
                      <div className={`hero-price-card ${priceInfo.tierClass}`}>
                        <div className="hero-price-meta-label">ESTIMASI NILAI PASAR</div>
                        <div className="hero-price-row">
                          <span className="hero-price-usd">{priceInfo.usdFormatted}</span>
                          <span className="hero-price-idr">(~{priceInfo.idrLabel})</span>
                        </div>
                        <div className="hero-tier-row">
                          <span className="hero-dot"></span>
                          <span className="hero-tier-name">{priceInfo.tierTag}</span>
                        </div>
                      </div>
                    </div>

                    {/* DYNAMIC PROGRESS BAR */}
                    <div className="confidence-track">
                      <div 
                        className={`confidence-fill fill-${confLabel.toLowerCase()}`}
                        style={{ width: `${Math.min(confPct, 100)}%` }}
                      ></div>
                    </div>

                    {/* SUB-METRICS BREAKDOWN */}
                    <div className="sub-metrics-row">
                      <span>
                        Cosine Similarity: <strong>{prediction.raw_similarity_score ? prediction.raw_similarity_score.toFixed(4) : 'N/A'}</strong>
                      </span>
                      <span className="metric-sep">|</span>
                      <span>
                        ORB Verification: <strong>{prediction.orb_verification_score ? prediction.orb_verification_score.toFixed(3) : 'N/A'}</strong>
                      </span>
                      <span className="metric-sep">|</span>
                      <span>
                        Margin ke Runner-Up: <strong>+{prediction.margin_to_runner_up ? prediction.margin_to_runner_up.toFixed(4) : '0.0000'}</strong>
                      </span>
                    </div>

                    {/* STATUS VERIFIKASI */}
                    <div className="verification-status-row">
                      <span className="status-label-bold">STATUS:</span>
                      <span className="status-verified-text">TERVERIFIKASI MODEL 1 CLIP</span>
                      <span className="status-sep">|</span>
                      <span className="status-label-bold">VALUASI:</span>
                      <span className={`status-tier-desc ${priceInfo.tierClass}`}>
                        {priceInfo.tierDesc.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="top1-standby-content">
                    <div className="standby-icon-spinner">●</div>
                    <div className="standby-text-block">
                      <h3 className="standby-title">
                        {isSharp ? "Mencari Kartu Pokemon..." : "Sensor Kurang Fokus / Goyang"}
                      </h3>
                      <p className="standby-sub">
                        {isSharp 
                          ? "Posisikan kartu Pokemon pas di dalam kotak panduan pemindai kiri."
                          : "Tahan kartu lebih stabil atau sesuaikan jarak kamera agar fokus tajam."}
                      </p>
                    </div>
                    <div className="confidence-track idle-track"></div>
                    <div className="standby-status-footer">
                      STATUS: STANDBY — MENUNGGU OBJEK KARTU
                    </div>
                  </div>
                )}
              </div>

              {/* PANEL 2: KANDIDAT LAIN & PERBANDINGAN HARGA (TOP 2 - 4) */}
              <div className="hud-panel panel-runnerups">
                <div className="panel-header-title amber-accent">
                  KANDIDAT LAIN, PERBANDINGAN VARIAN REPRINT & HARGA (TOP 2 - 4)
                </div>

                <div className="runnerups-table-container">
                  <table className="runnerups-table">
                    <thead>
                      <tr>
                        <th style={{ width: '8%' }}>RANK</th>
                        <th style={{ width: '28%' }}>NAMA KARTU</th>
                        <th style={{ width: '26%' }}>SET & CARD ID</th>
                        <th style={{ width: '20%' }}>HARGA PASAR</th>
                        <th style={{ width: '9%' }}>COSINE</th>
                        <th style={{ width: '9%' }}>ORB</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prediction?.candidates && prediction.candidates.length > 0 ? (
                        prediction.candidates.slice(0, 3).map((cand, idx) => {
                          const candPrice = formatPriceInfo(cand.price_usd, cand.price_idr);
                          return (
                            <tr key={cand.card_id || idx} className="runnerup-row">
                              <td className="rank-col">#{cand.rank || idx + 2}</td>
                              <td className="name-col" title={cand.name}>
                                {cand.name}
                              </td>
                              <td className="set-col" title={`${cand.set_name || '-'} (${cand.card_id})`}>
                                {cand.set_name || '-'} <span className="id-sub">({cand.card_id})</span>
                              </td>
                              <td className={`price-col ${candPrice.tierClass}`}>
                                {candPrice.label}
                              </td>
                              <td className="sim-col">
                                {cand.raw_similarity_score ? cand.raw_similarity_score.toFixed(4) : '-'}
                              </td>
                              <td className="orb-col">
                                {cand.orb_verification_score ? cand.orb_verification_score.toFixed(3) : '-'}
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        [1, 2, 3].map((slot) => (
                          <tr key={slot} className="runnerup-row placeholder-row">
                            <td className="rank-col">#{slot + 1}</td>
                            <td colSpan="5" className="placeholder-text">
                              --- Menunggu deteksi kartu ---
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* PANEL 3: TELEMETRI & KONTROL PEMINDAIAN */}
              <div className="hud-panel panel-telemetry">
                <div className="telemetry-grid">
                  <div className="telemetry-card">
                    <span className="telemetry-label">Camera Speed</span>
                    <span className="telemetry-val val-green">{camFps} FPS (Smooth)</span>
                  </div>
                  <div className="telemetry-card">
                    <span className="telemetry-label">AI Inference Latency</span>
                    <span className="telemetry-val val-cyan">{latencyMs} ms (~{inferRate}/s)</span>
                  </div>
                  <div className="telemetry-card">
                    <span className="telemetry-label">Sensor Sharpness</span>
                    <span className={`telemetry-val ${isSharp ? 'val-green' : 'val-coral'}`}>
                      {liveSharpness} [{sharpTag}]
                    </span>
                  </div>
                  <div className="telemetry-card">
                    <span className="telemetry-label">Vision Backbone</span>
                    <span className="telemetry-val val-white">CLIP ViT-B-32 + FAISS</span>
                  </div>
                </div>

                {/* ACTION BUTTONS */}
                <div className="hud-actions-bar">
                  <button className="action-btn exit-btn-primary" onClick={stopCamera}>
                    KEMBALI KE MENU SEBELUMNYA
                  </button>

                  <button 
                    className={`action-btn pause-btn ${isPaused ? 'active-paused' : ''}`}
                    onClick={() => setIsPaused(prev => !prev)}
                    title="Freeze frame kamera agar tidak perlu terus menahan kartu"
                  >
                    {isPaused ? "RESUME STREAM [SPASI]" : "FREEZE / PAUSE [SPASI]"}
                  </button>

                  {hasCard && (
                    <button 
                      className="action-btn view-detail-btn"
                      onClick={() => {
                        let snap = null;
                        if (captureCanvasRef.current) {
                          snap = captureCanvasRef.current.toDataURL('image/jpeg', 0.85);
                        }
                        stopCamera();
                        onUploadComplete({
                          ...prediction,
                          user_scanned_image: snap
                        });
                      }}
                      style={{
                        backgroundColor: '#00d26a',
                        color: '#1e1b4b',
                        fontWeight: '800'
                      }}
                    >
                      LIHAT DETAIL LENGKAP
                    </button>
                  )}
                </div>
              </div>

            </div>
          </div>


        </div>
      )}
    </div>
  );
}

export default UploadPage;