"""
=============================================================================
Pokemon Card Value Analytic Tool — Live Webcam / Phone Camera Scanner
=============================================================================
Pemindai Langsung On-Cam (Dioptimasi untuk Kamera HP Xiaomi/Redmi & IP Webcam):
- Membaca CAMERA_SOURCE dari .env (contoh: http://192.168.110.181:8080/video).
- Mendukung kontrol jarak jauh kamera HP:
    * Tekan 'F' -> Memicu Auto-Focus kamera HP Redmi.
    * Tekan 'L' -> Menyalakan/mematikan Lampu Flash/Torch HP Redmi.
    * Klik Mouse / Tekan 'S' -> Memindai (Scan) kartu.
- Minimalisir buffer latency (zero-lag live preview).
- Panduan bingkai Smart Static Frame berasio standar kartu 63:88.
- Deteksi ketajaman gambar (Laplacian variance) & estimasi kemiringan real-time.
- Mengirim potongan bersih ke engine CLIP dengan 4-way auto-orientation.
=============================================================================
"""

import os
import sys
import time
import urllib.request
from urllib.parse import urlparse
import cv2
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Pastikan folder model ada di python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from card_identifier import CardIdentifier

# Sumber kamera dibaca dari .env (var CAMERA_SOURCE)
_camera_source_raw = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE = int(_camera_source_raw) if _camera_source_raw.strip().isdigit() else _camera_source_raw

# Ambang batas ketajaman & orientasi
SHARPNESS_THRESHOLD = 75.0
BURST_FRAMES = 6
TILT_WARNING_DEGREES = 14.0

# Konfigurasi Engine
USE_TTA = False
USE_ORB_RERANK = True
ORB_POOL_SIZE = 100

# Mode Debug
DEBUG_MODE = True
DEBUG_TOP_K = 5
DEBUG_ALIGNED_PATH = "debug_last_scan_aligned.jpg"

LABEL_COLOR = {
    "Tinggi": (0, 220, 0),      # hijau cerah
    "Sedang": (0, 215, 255),    # kuning
    "Rendah": (0, 50, 255),     # merah
}


def send_ipwebcam_cmd(cmd_path):
    """Kirim perintah kontrol jarak jauh ke aplikasi IP Webcam di HP."""
    if not isinstance(CAMERA_SOURCE, str) or not CAMERA_SOURCE.startswith("http"):
        return False
    try:
        parsed = urlparse(CAMERA_SOURCE)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        target_url = f"{base_url}/{cmd_path.lstrip('/')}"
        req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[remote-hp] Perintah '{cmd_path}' gagal: {e}")
        return False


def sharpness_score(gray_frame):
    return cv2.Laplacian(gray_frame, cv2.CV_64F).var()


def estimate_tilt_deviation(gray_frame):
    edges = cv2.Canny(gray_frame, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    frame_area = gray_frame.shape[0] * gray_frame.shape[1]
    if cv2.contourArea(c) < 0.15 * frame_area:
        return None
    angle = cv2.minAreaRect(c)[2]
    angle_mod = abs(angle) % 90
    return min(angle_mod, 90 - angle_mod)


def apply_camera_rotation(frame, rotation_deg):
    """Putar orientasi citra kamera jika HP dipegang secara tegak (portrait)."""
    if rotation_deg == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_deg == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    elif rotation_deg == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame


def capture_best_of_burst(cap, x1, y1, x2, y2, rotation_deg=0, n_frames=BURST_FRAMES):
    # Buang 2 frame buffer lama agar mendapatkan citra real-time saat tombol ditekan
    for _ in range(2):
        cap.grab()

    best_crop = None
    best_score = -1.0
    for _ in range(n_frames):
        ret, frame = cap.read()
        if not ret:
            continue
        if rotation_deg != 0:
            frame = apply_camera_rotation(frame, rotation_deg)
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
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)
    cv2.imshow(window_name, overlay_frame)
    cv2.waitKey(1)


def main():
    print("Memuat AI Engine (CLIP ViT-B-32) dan Index FAISS...")
    try:
        identifier = CardIdentifier(use_tta=USE_TTA, use_orb_rerank=USE_ORB_RERANK,
                                     orb_rerank_pool_size=ORB_POOL_SIZE)
        print(f"[debug] use_tta={USE_TTA}  use_orb_rerank={USE_ORB_RERANK}  "
              f"orb_pool_size={ORB_POOL_SIZE}  confidence_temperature={identifier.confidence_temperature}")
    except Exception as e:
        print(f"Gagal memuat engine: {e}")
        return

    print(f"[info] Menghubungkan ke sumber kamera: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)

    # Set buffer minimalis agar tidak ada delay/lag pada streaming IP Webcam
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"\n[ERROR] Kamera '{CAMERA_SOURCE}' tidak dapat diakses.")
        print("Petunjuk untuk HP Redmi 15:")
        print("1. Pastikan aplikasi 'IP Webcam' sudah dibuka dan 'Start server' sudah aktif.")
        print("2. Pastikan laptop dan HP Redmi 15 terhubung ke jaringan Wi-Fi yang sama.")
        print("3. Periksa IP yang tertera di layar HP dan samakan dengan CAMERA_SOURCE di backend/.env\n")
        return

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[info] Kamera Berhasil Terhubung! Resolusi Sensor: {actual_w}x{actual_h}")

    WINDOW_NAME = "Pemindai Kartu Pokemon (Redmi 15 Optimized)"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 560, 920)

    # Fitur klik mouse untuk scan langsung
    mouse_scan_triggered = False

    def on_mouse(event, x, y, flags, param):
        nonlocal mouse_scan_triggered
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_scan_triggered = True

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    is_torch_on = False
    is_phone_stream = isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.startswith("http")

    print("\n=======================================================")
    print("KAMERA REDMI 15 AKTIF!")
    print("-------------------------------------------------------")
    print("• [Spasi] atau [S] atau [Klik Mouse] : SCAN KARTU")
    if is_phone_stream:
        print("• [F]                                : Trigger Auto-Focus HP Redmi")
        print("• [L]                                : Toggle Lampu Flash/Torch HP")
    print("• [Q]                                : KELUAR")
    print("=======================================================\n")

    # Orientasi kamera: baca dari .env CAMERA_ROTATION (default 90 derajat jika stream HP agar portrait)
    default_rot = 90 if is_phone_stream else 0
    current_rotation = int(os.getenv("CAMERA_ROTATION", str(default_rot)))

    card_aspect = 63.0 / 88.0

    last_result_text = ""
    last_result_color = (255, 255, 255)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal mengambil gambar dari kamera.")
            break

        if current_rotation != 0:
            frame = apply_camera_rotation(frame, current_rotation)

        h, w, _ = frame.shape

        # Hitung proporsi kotak kartu adaptif terhadap portrait/landscape
        if h > w:
            # Mode Portrait (HP dipegang tegak)
            CARD_WIDTH = int(w * 0.76)
            CARD_HEIGHT = int(CARD_WIDTH / card_aspect)
        else:
            # Mode Landscape
            CARD_HEIGHT = int(h * 0.74)
            CARD_WIDTH = int(CARD_HEIGHT * card_aspect)

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

        # Dark overlay di luar kotak kartu agar fokus visual terarah
        overlay = display_frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, display_frame, 0.55, 0, display_frame)
        display_frame[y1:y2, x1:x2] = frame[y1:y2, x1:x2]

        guide_color = (0, 255, 0) if is_ready else (0, 165, 255)
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), guide_color, 2)

        # Corner accents estetis
        corner_len = 24
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
            guide_text = f"Kartu agak miring (~{tilt_deviation:.0f}°) - luruskan"
        elif not is_sharp_enough:
            guide_text = "Gambar buram/goyang - stabilkan atau tekan 'F'"
        cv2.putText(display_frame, guide_text, (x1 - 10, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, guide_color, 2)

        # Status Bar Atas
        controls_text = f"[S / Klik] Scan | [R] Rotasi:{current_rotation} deg | [Q] Keluar"
        if is_phone_stream:
            torch_status = "ON" if is_torch_on else "OFF"
            controls_text += f" | [F] Focus | [L] Flash:{torch_status}"
        cv2.putText(display_frame, controls_text, (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

        # Indikator Ketajaman Sensor Redmi
        focus_label = "FOKUS TAJAM" if is_sharp_enough else "KURANG FOKUS"
        sharp_color = (0, 255, 0) if is_sharp_enough else (0, 165, 255)
        cv2.putText(display_frame, f"Ketajaman Sensor: {live_sharpness:.0f} [{focus_label}]", (15, h - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, sharp_color, 2)

        if last_result_text:
            cv2.putText(display_frame, last_result_text, (15, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, last_result_color, 2)

        cv2.imshow(WINDOW_NAME, display_frame)

        key = cv2.waitKey(1) & 0xFF

        # Trigger Scan via keyboard 's', spasi (32), atau klik mouse
        trigger_scan = (key == ord('s')) or (key == 32) or mouse_scan_triggered
        mouse_scan_triggered = False

        if trigger_scan:
            print("\n[capture] Mengambil burst frame terbaik dari sensor Redmi...")
            best_crop, best_score = capture_best_of_burst(cap, x1, y1, x2, y2, rotation_deg=current_rotation)

            if best_crop is None or best_score < SHARPNESS_THRESHOLD * 0.4:
                print("Gambar terlalu blur untuk dipindai. Coba tekan 'F' untuk fokus ulang.")
                last_result_text = "Terlalu blur, coba tekan 'F' (Fokus)"
                last_result_color = (0, 0, 255)
                continue

            show_scanning_indicator(WINDOW_NAME, display_frame, x1, y1, x2, y2)

            print(f"Memindai kartu (skor ketajaman: {best_score:.0f})... 🔍")
            save_path = DEBUG_ALIGNED_PATH if DEBUG_MODE else None

            # Kirim crop ke engine CLIP (dengan Dual-View Retrieval & 4-Way Auto-Orientation)
            result = identifier.identify_card(best_crop, top_k=DEBUG_TOP_K, debug=DEBUG_MODE,
                                               debug_save_path=save_path, auto_align=True)

            if result['status'] == 'success' and result['candidates']:
                top_match = result['candidates'][0]
                label = top_match.get('confidence_label', 'Rendah')
                print(f"================ HASIL DETEKSI ================")
                print(f"Nama Kartu      : {top_match.get('name', 'Unknown')}")
                print(f"Set             : {top_match.get('set_name', 'Unknown')}")
                print(f"Card ID         : {top_match.get('card_id', 'Unknown')}")
                print(f"Confidence      : {top_match['confidence_percentage']}% ({label})")
                print(f"Waktu Inferensi : {result['execution_time_ms']} ms")
                print(f"===============================================")

                if DEBUG_MODE:
                    print(f"[debug] raw similarity top-1 : {top_match.get('raw_similarity_score')}")
                    print(f"[debug] margin ke runner-up  : {top_match.get('margin_to_runner_up')}")
                    print(f"[debug] Top-{DEBUG_TOP_K} kandidat:")
                    for c in result['candidates']:
                        orb_str = f" orb={c['orb_verification_score']:.3f}" if c.get('orb_verification_score') is not None else ""
                        set_str = f" [{c.get('set_name', '')}]" if c.get('set_name') else ""
                        print(f"         #{c['rank']} {c.get('name','?'):18s}{set_str:25s} raw={c['raw_similarity_score']:.4f}  conf={c['confidence_percentage']}%{orb_str}")

                last_result_text = f"{top_match.get('name', 'Unknown')} - {top_match['confidence_percentage']}% ({label})"
                last_result_color = LABEL_COLOR.get(label, (255, 255, 255))
            else:
                print("Kartu tidak dikenali.")
                last_result_text = "Kartu tidak dikenali"
                last_result_color = (0, 0, 255)

        elif key == ord('r'):
            current_rotation = (current_rotation + 90) % 360
            print(f"\n[kamera] Rotasi layar diubah ke: {current_rotation}°")

        elif key == ord('f'):
            if is_phone_stream:
                print("\n[remote-hp] Mengirim perintah Auto-Focus ke Redmi 15...")
                ok = send_ipwebcam_cmd("focus")
                if ok:
                    print("[remote-hp] Fokus diperbarui.")
            else:
                print("[info] Shortcut Fokus hanya aktif pada streaming IP Webcam HP.")

        elif key == ord('l'):
            if is_phone_stream:
                is_torch_on = not is_torch_on
                endpoint = "enabletorch" if is_torch_on else "disabletorch"
                status_str = "MENYALA" if is_torch_on else "MATI"
                print(f"\n[remote-hp] Lampu Flash HP Redmi: {status_str}")
                send_ipwebcam_cmd(endpoint)
            else:
                print("[info] Shortcut Lampu Flash hanya aktif pada streaming IP Webcam HP.")

        elif key == ord('q'):
            print("\nMenutup program...")
            break

    # Pastikan lampu flash mati saat keluar
    if is_phone_stream and is_torch_on:
        send_ipwebcam_cmd("disabletorch")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
