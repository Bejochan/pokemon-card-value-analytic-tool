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

function UploadPage({ onUploadComplete }) {
  // State Upload Tradisional
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

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

  // --- LOGIKA UPLOAD FILE BIASA ---
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
          alert('Gagal terhubung ke backend.');
        } finally {
          setIsUploading(false);
        }
      };
      reader.readAsDataURL(selectedFile);
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
                    <p className="hud-upload-title">Menganalisis Kartu...</p>
                  </div>
                ) : (
                  <>
                    <div className="drop-zone">
                      <div className="upload-icon">☁️</div>
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
                        BROWSE FILE
                      </button>
                    </div>

                    <p className="or-text">— OR —</p>
                    
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
                    <div className="standby-icon-spinner">🔍</div>
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
                    <span className="btn-icon">↩</span>
                    KEMBALI KE HALAMAN SEBELUMNYA
                  </button>

                  <button 
                    className={`action-btn pause-btn ${isPaused ? 'active-paused' : ''}`}
                    onClick={() => setIsPaused(prev => !prev)}
                    title="Freeze frame kamera agar tidak perlu terus menahan kartu"
                  >
                    <span className="btn-icon">{isPaused ? "▶️" : "⏸️"}</span>
                    {isPaused ? "RESUME STREAM [SPASI]" : "FREEZE / PAUSE [SPASI]"}
                  </button>
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