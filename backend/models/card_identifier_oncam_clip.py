"""
=============================================================================
Pokemon Card Value Analytic Tool — Webcam Scanner (varian CLIP)
=============================================================================
Salinan card_identifier_oncam.py yang memakai backend CLIP
(card_identifier_clip.py) alih-alih MobileNet. Semua fitur (kamera dari .env,
deteksi ketajaman & kemiringan real-time, ORB re-rank, dsb) identik dengan
versi MobileNet -- cuma backbone ekstraksi fiturnya yang beda.

WAJIB sudah menjalankan build_card_index_clip.py dulu sebelum pakai script
ini (butuh card_embeddings_clip.index & card_id_map_clip.json).
=============================================================================
"""

import os
import sys
import cv2
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()  # baca file .env di root project kalau ada
except ImportError:
    print("[peringatan] python-dotenv belum terinstall (pip install python-dotenv).")
    print("             Lanjut tanpa .env -- CAMERA_SOURCE akan pakai fallback default.")

# Pastikan folder model ada di python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from card_identifier_clip import CardIdentifier

# Sumber kamera dibaca dari .env (var CAMERA_SOURCE), BUKAN di-hardcode.
# - Isi dengan URL kamera IP, mis. CAMERA_SOURCE=http://192.168.1.5:8080/video
# - Atau isi index webcam biasa, mis. CAMERA_SOURCE=0
# - Kalau .env tidak ada / variabel tidak diisi, fallback ke webcam default (index 0)
# Lihat .env.example untuk template.
_camera_source_raw = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE = int(_camera_source_raw) if _camera_source_raw.strip().isdigit() else _camera_source_raw

# Ambang batas ketajaman (variance of Laplacian).
SHARPNESS_THRESHOLD = 70.0
BURST_FRAMES = 6

# --- KONFIGURASI ENGINE ---
USE_TTA = False              # Rata-rata augmentasi gambar
USE_ORB_RERANK = True        # AKTIF -- pencocokan keypoint fitur visual lokal
ORB_POOL_SIZE = 50           # Naikkan ke 50 kandidat agar tahan terhadap noise/variasi cahaya

# --- MODE DEBUG ---
DEBUG_MODE = True
DEBUG_TOP_K = 5
DEBUG_ALIGNED_PATH = "debug_last_scan_aligned_clip.jpg"

LABEL_COLOR = {
    "Tinggi": (0, 200, 0),      # hijau (BGR)
    "Sedang": (0, 200, 255),    # kuning
    "Rendah": (0, 0, 255),      # merah
}

def sharpness_score(gray_frame):
    return cv2.Laplacian(gray_frame, cv2.CV_64F).var()

def estimate_tilt_deviation(gray_frame):
    """
    Perkiraan CEPAT (bukan pipeline alignment penuh) seberapa miring kartu di
    dalam kotak panduan, dihitung tiap frame di live preview -- supaya user
    bisa diperingatkan SEBELUM menekan scan, bukan sesudah buang ~1 detik
    untuk capture yang sudah pasti jelek (kasus kartu Charcadet yang ke-capture
    miring ~80-90 derajat).

    Return: deviasi sudut dari posisi tegak/rata (0 = lurus sempurna,
    45 = paling miring), atau None kalau kontur kartu tidak terlihat jelas.
    """
    edges = cv2.Canny(gray_frame, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    frame_area = gray_frame.shape[0] * gray_frame.shape[1]
    if cv2.contourArea(c) < 0.15 * frame_area:
        return None  # kontur terlalu kecil, kemungkinan bukan kartu yang terdeteksi
    angle = cv2.minAreaRect(c)[2]
    angle_mod = abs(angle) % 90
    return min(angle_mod, 90 - angle_mod)

TILT_WARNING_DEGREES = 12.0  # di atas ini, kartu dianggap "terlalu miring"

def capture_best_of_burst(cap, x1, y1, x2, y2, n_frames=BURST_FRAMES):
    best_crop = None
    best_score = -1.0
    for _ in range(n_frames):
        ret, frame = cap.read()
        if not ret:
            continue
        crop = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        score = sharpness_score(gray)
        if score > best_score:
            best_score = score
            best_crop = crop
    return best_crop, best_score

def show_scanning_indicator(window_name, frame, x1, y1, x2, y2):
    overlay_frame = frame.copy()
    cv2.rectangle(overlay_frame, (x1, y1), (x2, y2), (0, 200, 255), 3)
    cv2.putText(overlay_frame, "Memindai... mohon tunggu", (x1 - 10, y1 - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
    cv2.imshow(window_name, overlay_frame)
    cv2.waitKey(1)

def main():
    print("Memuat AI Engine (backend: CLIP) dan Index (Mohon tunggu sebentar)...")
    try:
        identifier = CardIdentifier(use_tta=USE_TTA, use_orb_rerank=USE_ORB_RERANK,
                                     orb_rerank_pool_size=ORB_POOL_SIZE)
        print(f"[debug] use_tta={USE_TTA}  use_orb_rerank={USE_ORB_RERANK}  "
              f"orb_pool_size={ORB_POOL_SIZE}  confidence_temperature={identifier.confidence_temperature}")
    except Exception as e:
        print(f"Gagal memuat engine: {e}")
        return

    # Inisialisasi Kamera dari CAMERA_SOURCE (.env), preferensi resolusi HD (1280x720)
    print(f"[info] Menghubungkan ke sumber kamera: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print(f"Error: Kamera '{CAMERA_SOURCE}' tidak dapat diakses.")
        print("Cek lagi CAMERA_SOURCE di file .env kamu, atau pastikan aplikasi kamera IP")
        print("di HP sedang aktif & terhubung ke jaringan WiFi yang sama.")
        return

    # Baca resolusi riil yang disetujui oleh driver kamera
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[info] Resolusi Kamera Terdeteksi: {actual_w}x{actual_h}")

    WINDOW_NAME = "Pemindai Kartu Pokemon (CLIP)"

    print("\n=======================================================")
    print("Kamera menyala!")
    print("Posisikan kartu TEPAT di dalam kotak hijau di layar.")
    print("Tekan 's' pada keyboard untuk SCAN kartu di layar.")
    if USE_ORB_RERANK:
        print(f"(ORB re-rank aktif -- top-{ORB_POOL_SIZE} kandidat diverifikasi keypoint)")
    print("Tekan 'q' pada keyboard untuk KELUAR dari program.")
    print("=======================================================\n")

    # Hitung proporsi kotak kartu berdasarkan aspek rasio standar kartu (63:88)
    card_aspect = 63.0 / 88.0
    CARD_HEIGHT = int(actual_h * 0.72)
    CARD_WIDTH = int(CARD_HEIGHT * card_aspect)

    last_result_text = ""
    last_result_color = (255, 255, 255)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal mengambil gambar dari kamera.")
            break

        h, w, _ = frame.shape
        x1 = int((w - CARD_WIDTH) / 2)
        y1 = int((h - CARD_HEIGHT) / 2)
        x2 = x1 + CARD_WIDTH
        y2 = y1 + CARD_HEIGHT

        cropped_frame = frame[y1:y2, x1:x2]
        crop_gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
        live_sharpness = sharpness_score(crop_gray)
        is_sharp_enough = live_sharpness >= SHARPNESS_THRESHOLD

        tilt_deviation = estimate_tilt_deviation(crop_gray)
        is_too_tilted = tilt_deviation is not None and tilt_deviation > TILT_WARNING_DEGREES

        is_ready = is_sharp_enough and not is_too_tilted

        display_frame = frame.copy()
        overlay = display_frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, display_frame, 0.55, 0, display_frame)
        display_frame[y1:y2, x1:x2] = frame[y1:y2, x1:x2]

        guide_color = (0, 255, 0) if is_ready else (0, 165, 255)
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), guide_color, 2)

        # Corner accents
        corner_len = 20
        cv2.line(display_frame, (x1, y1), (x1 + corner_len, y1), (0, 255, 255), 3)
        cv2.line(display_frame, (x1, y1), (x1, y1 + corner_len), (0, 255, 255), 3)
        cv2.line(display_frame, (x2, y1), (x2 - corner_len, y1), (0, 255, 255), 3)
        cv2.line(display_frame, (x2, y1), (x2, y1 + corner_len), (0, 255, 255), 3)
        cv2.line(display_frame, (x1, y2), (x1 + corner_len, y2), (0, 255, 255), 3)
        cv2.line(display_frame, (x1, y2), (x1, y2 - corner_len), (0, 255, 255), 3)
        cv2.line(display_frame, (x2, y2), (x2 - corner_len, y2), (0, 255, 255), 3)
        cv2.line(display_frame, (x2, y2), (x2, y2 - corner_len), (0, 255, 255), 3)

        guide_text = "Posisikan kartu pas di dalam kotak"
        if is_too_tilted:
            guide_text = f"Kartu terlalu miring (~{tilt_deviation:.0f}°) - luruskan dulu"
        elif not is_sharp_enough:
            guide_text = "Gambar buram/goyang - stabilkan posisi"
        cv2.putText(display_frame, guide_text, (x1 - 10, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, guide_color, 2)
        cv2.putText(display_frame, "[S] Scan | [Q] Keluar", (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f"Ketajaman: {live_sharpness:.0f} (Target: >{SHARPNESS_THRESHOLD:.0f})", (15, h - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, guide_color, 2)

        if last_result_text:
            cv2.putText(display_frame, last_result_text, (15, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, last_result_color, 2)

        cv2.imshow(WINDOW_NAME, display_frame)
        cv2.imshow("Debug: Hasil Crop Kartu (Input AI - CLIP)", cropped_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            if is_too_tilted:
                print(f"\n[peringatan] Kartu masih terdeteksi miring (~{tilt_deviation:.0f}°) -- "
                      "hasil kemungkinan kurang akurat. Tetap lanjut scan...")
            print("\nMengambil beberapa frame untuk memilih yang paling tajam...")
            best_crop, best_score = capture_best_of_burst(cap, x1, y1, x2, y2)

            if best_crop is None or best_score < SHARPNESS_THRESHOLD * 0.5:
                print("Gambar terlalu blur untuk dipindai. Stabilkan kamera & coba lagi.")
                last_result_text = "Terlalu blur, coba lagi"
                last_result_color = (0, 0, 255)
                continue

            if USE_ORB_RERANK:
                show_scanning_indicator(WINDOW_NAME, frame, x1, y1, x2, y2)

            print(f"Memindai kartu (ketajaman terbaik: {best_score:.0f})... 🔍")
            save_path = DEBUG_ALIGNED_PATH if DEBUG_MODE else None

            # v3.2 FIX: kembalikan ke auto_align=True (default). Kotak panduan cuma
            # bantu POSISI kartu di frame, BUKAN pengganti alignment. Menonaktifkan
            # alignment (auto_align=False) berarti gambar langsung di-resize paksa
            # ke 448x625 tanpa deteksi tepi, tanpa koreksi rotasi/kemiringan, dan
            # tanpa buang sisa background -- ini kemungkinan besar penyebab utama
            # banyak kartu gagal terdeteksi & confidence rendah, karena akurasi
            # sepenuhnya bergantung pada presisi tangan memposisikan kartu pas di
            # kotak panduan (yang hampir mustahil sempurna).
            result = identifier.identify_card(best_crop, top_k=DEBUG_TOP_K, debug=DEBUG_MODE,
                                               debug_save_path=save_path)
            if DEBUG_MODE:
                print(f"[debug] gambar hasil scan disimpan di: {os.path.abspath(DEBUG_ALIGNED_PATH)}")

            if result['status'] == 'success' and result['candidates']:
                top_match = result['candidates'][0]
                label = top_match.get('confidence_label', 'Rendah')
                print(f"Hasil Scan      : {top_match.get('name', 'Unknown')} ({top_match.get('set_name', 'Unknown')})")
                print(f"Confidence      : {top_match['confidence_percentage']}% ({label})")
                print(f"Waktu Inferensi : {result['execution_time_ms']} ms")

                if DEBUG_MODE:
                    print(f"[debug] raw_similarity_score (top-1)  : {top_match.get('raw_similarity_score')}")
                    print(f"[debug] margin_to_runner_up            : {top_match.get('margin_to_runner_up')}")
                    print(f"[debug] temperature dipakai            : {result.get('debug_temperature')}")
                    print(f"[debug] {DEBUG_TOP_K} kandidat teratas (nama - raw_sim - conf - orb):")
                    for c in result['candidates']:
                        orb_str = f" orb={c['orb_verification_score']:.3f}" if c.get('orb_verification_score') is not None else ""
                        print(f"         #{c['rank']} {c.get('name','?'):20s} raw={c['raw_similarity_score']:.4f}  conf={c['confidence_percentage']}%{orb_str}")
                    pool = result.get('debug_similarity_pool', [])
                    print(f"[debug] seluruh pool similarity (top-{len(pool)}): {pool}")

                last_result_text = f"{top_match.get('name', 'Unknown')} - {top_match['confidence_percentage']}% ({label})"
                last_result_color = LABEL_COLOR.get(label, (255, 255, 255))

                if label == "Rendah":
                    print("Confidence rendah -- coba perbaiki pencahayaan/sudut lalu scan ulang.")
            else:
                print("Kartu tidak dikenali.")
                last_result_text = "Kartu tidak dikenali"
                last_result_color = (0, 0, 255)

        elif key == ord('q'):
            print("\nMenutup program...")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()