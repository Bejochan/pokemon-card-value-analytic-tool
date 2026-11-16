import { useRef, useState, useEffect, useCallback } from 'react';
import './HoloCard3D.css';

/**
 * Helper untuk menentukan kategori foil berdasarkan kelangkaan kartu Pokémon
 */
const getHoloFoilType = (card) => {
  if (!card) return 'none';
  const rarity = (card.rarityText || card.rarity || '').toLowerCase();
  const holoType = (card.holo || '').toLowerCase();

  if (rarity.includes('rainbow') || rarity.includes('secret') || rarity.includes('hyper')) {
    return 'rainbow';
  }
  if (rarity.includes('illustration') || rarity.includes('radiant') || rarity.includes('shiny') || rarity.includes('amazing')) {
    return 'sparkle';
  }
  if (
    rarity.includes('holo') ||
    rarity.includes('ultra') ||
    rarity.includes('double rare') ||
    rarity.includes('vmax') ||
    rarity.includes('vstar') ||
    rarity.includes('ex') ||
    rarity.includes('gx') ||
    (holoType && holoType !== 'normal print' && holoType !== 'standard')
  ) {
    return 'holo';
  }
  return 'standard';
};

/**
 * Komponen Kartu 3D Holografik Interaktif
 * Direverse-engineer dari konsep Simon Goellner (poke-holo.simey.me):
 * 1. Kontainer stasioner untuk event pointer agar terhindar dari feedback loop getBoundingClientRect.
 * 2. requestAnimationFrame dengan redaman pegas (spring damping / lerp) untuk gerakan mulus 60-120 FPS.
 * 3. Rotasi halus terkontrol (maksimal ±11 derajat) tanpa sentakan liar atau jitter.
 * 4. Tanpa teks/badge petunjuk visual yang tidak perlu.
 */
export default function HoloCard3D({
  card,
  imageUrl,
  backImageUrl,
  isFocused = false,
  onCardClick = null
}) {
  const containerRef = useRef(null);
  const cardRef = useRef(null);
  const animFrameRef = useRef(null);

  const prevFocusedRef = useRef(null);
  const [flipAnimClass, setFlipAnimClass] = useState('');

  // Sinkronisasi animasi putaran 360 derajat (The Collector's Flip) saat mode fokus berubah
  useEffect(() => {
    if (prevFocusedRef.current === null) {
      prevFocusedRef.current = isFocused;
      return;
    }
    if (prevFocusedRef.current !== isFocused) {
      setFlipAnimClass(isFocused ? 'anim-flip-to-focus' : 'anim-flip-to-dual');
      prevFocusedRef.current = isFocused;
    }
  }, [isFocused]);

  // Nilai posisi target kursor
  const target = useRef({
    rotX: 0,
    rotY: 0,
    px: 50,
    py: 50,
    opacity: 0
  });

  // Nilai fisik terinterpolasi saat ini
  const current = useRef({
    rotX: 0,
    rotY: 0,
    px: 50,
    py: 50,
    opacity: 0
  });

  const foilType = getHoloFoilType(card);
  const isHolo = foilType !== 'standard';

  // Loop requestAnimationFrame untuk spring lerp physics yang super mulus
  const startAnimationLoop = useCallback(() => {
    if (animFrameRef.current) return;

    const animate = () => {
      const cur = current.current;
      const tgt = target.current;

      // Damping factor 0.12 memberikan sensasi gerakan berbobot dan halus
      const ease = 0.12;
      cur.rotX += (tgt.rotX - cur.rotX) * ease;
      cur.rotY += (tgt.rotY - cur.rotY) * ease;
      cur.px += (tgt.px - cur.px) * ease;
      cur.py += (tgt.py - cur.py) * ease;
      cur.opacity += (tgt.opacity - cur.opacity) * ease;

      if (cardRef.current) {
        const el = cardRef.current;
        el.style.setProperty('--rotate-x', `${cur.rotX.toFixed(2)}deg`);
        el.style.setProperty('--rotate-y', `${cur.rotY.toFixed(2)}deg`);
        el.style.setProperty('--pointer-x', `${cur.px.toFixed(2)}%`);
        el.style.setProperty('--pointer-y', `${cur.py.toFixed(2)}%`);
        el.style.setProperty('--card-opacity', cur.opacity.toFixed(3));
      }

      // Cek apakah animasi sudah berhenti di posisi tengah
      const isSettled =
        Math.abs(tgt.rotX - cur.rotX) < 0.01 &&
        Math.abs(tgt.rotY - cur.rotY) < 0.01 &&
        Math.abs(tgt.opacity - cur.opacity) < 0.005;

      if (!isSettled || tgt.opacity > 0) {
        animFrameRef.current = requestAnimationFrame(animate);
      } else {
        animFrameRef.current = null;
      }
    };

    animFrameRef.current = requestAnimationFrame(animate);
  }, []);

  // Cleanup loop saat unmount
  useEffect(() => {
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  // Handler interaksi pointer pada kontainer stasioner
  const handlePointerMove = useCallback((e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const clientX = Math.min(Math.max(e.clientX, rect.left), rect.right);
    const clientY = Math.min(Math.max(e.clientY, rect.top), rect.bottom);

    const x = clientX - rect.left;
    const y = clientY - rect.top;

    const px = (x / rect.width) * 100;
    const py = (y / rect.height) * 100;

    // Sudut kemiringan halus terukur (maksimal ±11 derajat seperti poke-holo)
    const rotX = -((py - 50) / 50) * 11;
    const rotY = ((px - 50) / 50) * 11;

    target.current.rotX = rotX;
    target.current.rotY = rotY;
    target.current.px = px;
    target.current.py = py;
    target.current.opacity = 1;

    startAnimationLoop();
  }, [startAnimationLoop]);

  const handlePointerLeave = useCallback(() => {
    // Easing halus kembali ke posisi tegak
    target.current.rotX = 0;
    target.current.rotY = 0;
    target.current.px = 50;
    target.current.py = 50;
    target.current.opacity = 0;

    startAnimationLoop();
  }, [startAnimationLoop]);

  // Handler sentuh untuk smartphone / tablet
  const handleTouchMove = useCallback((e) => {
    if (!containerRef.current || !e.touches || e.touches.length === 0) return;
    const touch = e.touches[0];
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const clientX = Math.min(Math.max(touch.clientX, rect.left), rect.right);
    const clientY = Math.min(Math.max(touch.clientY, rect.top), rect.bottom);

    const px = ((clientX - rect.left) / rect.width) * 100;
    const py = ((clientY - rect.top) / rect.height) * 100;

    target.current.rotX = -((py - 50) / 50) * 11;
    target.current.rotY = ((px - 50) / 50) * 11;
    target.current.px = px;
    target.current.py = py;
    target.current.opacity = 1;

    startAnimationLoop();
  }, [startAnimationLoop]);

  // Dukungan sensor fisik ponsel (Gyroscope)
  useEffect(() => {
    const handleOrientation = (e) => {
      if (e.gamma === null || e.beta === null) return;
      const rotY = Math.min(11, Math.max(-11, e.gamma * 0.35));
      const rotX = Math.min(11, Math.max(-11, (e.beta - 45) * 0.35));

      target.current.rotX = -rotX;
      target.current.rotY = rotY;
      target.current.px = 50 + (rotY / 11) * 35;
      target.current.py = 50 + (rotX / 11) * 35;
      target.current.opacity = 0.7;

      startAnimationLoop();
    };

    if (window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', handleOrientation, { passive: true });
    }
    return () => {
      if (window.DeviceOrientationEvent) {
        window.removeEventListener('deviceorientation', handleOrientation);
      }
    };
  }, [startAnimationLoop]);

  return (
    <div
      ref={containerRef}
      className={`holo-card-container ${isFocused ? 'is-focused' : ''}`}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      onTouchMove={handleTouchMove}
      onTouchEnd={handlePointerLeave}
      onClick={onCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onCardClick && onCardClick();
        }
      }}
      title={isFocused ? 'Klik untuk kembali ke tampilan detail' : (card?.name ? `${card.name} (Klik untuk memperbesar)` : 'Klik untuk memperbesar')}
    >
      <div className="holo-card-entrance">
        <div className={`holo-card-flipper ${flipAnimClass}`}>
          <div
            ref={cardRef}
            className={`holo-card-rotator foil-${foilType}`}
          >
            {/* Sisi Muka Depan Kartu (0deg) */}
            <div className="holo-card-face holo-card-front">
              <img
                src={imageUrl || '/card-result.png'}
                alt={card?.name || 'Pokemon Card'}
                className="holo-card-image"
                loading="eager"
                onError={(e) => {
                  if (e.target.src !== card?.image && card?.image) {
                    e.target.src = card.image;
                  } else {
                    e.target.src = '/card-result.png';
                  }
                }}
              />

              {/* Lapisan 1: Efek Holografik Berpendar */}
              {isHolo && (
                <div className={`holo-layer-foil foil-${foilType}`} aria-hidden="true" />
              )}

              {/* Lapisan 2: Pantulan Cahaya (Specular Glare) */}
              <div className="holo-layer-glare" aria-hidden="true" />

              {/* Lapisan 3: Kilau Pinggiran Halus */}
              <div className="holo-layer-edge" aria-hidden="true" />
            </div>

            {/* Sisi Muka Belakang Kartu (180deg) */}
            <div className="holo-card-face holo-card-back">
              <img
                src={backImageUrl || '/pokemon-card-back.png'}
                alt="Pokemon Card Back"
                className="holo-card-image"
                loading="eager"
                onError={(e) => {
                  e.target.src = '/pokemon-card-back.png';
                }}
              />

              {/* Pantulan Cahaya & Kilau Pinggiran untuk Sisi Belakang */}
              <div className="holo-layer-glare" aria-hidden="true" />
              <div className="holo-layer-edge" aria-hidden="true" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
