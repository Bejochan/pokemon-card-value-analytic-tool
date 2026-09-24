"""
=============================================================================
Pokemon Card Value Analytic Tool — Real-Time Live Card Identifier
=============================================================================
Pemindai Real-Time Berkecepatan Tinggi (Untuk Demonstrasi Live Computer Vision):
- Menggunakan arsitektur Multithreaded Asynchronous Inference (UI preview tetap
  berjalan mulus di 30+ FPS tanpa freeze/stutter).
- Background Worker mengeksekusi inferensi CLIP ViT-B-32 + FAISS + Fast ORB
  secara kontinu (~5-8 prediksi per detik).
- Tampilan HUD Computer Vision interaktif:
    * Scanning beam / laser animasi real-time di area target kartu.
    * Indikator FPS Kamera vs Latensi Inferensi AI (ms).
    * Overlay nama kartu, set, nomor, dan bar confidence dinamis.
    * Top-3 kandidat live update.
- Kontrol Kamera IP Webcam / Redmi 15:
    * [F] -> Auto-Focus kamera HP
    * [L] -> Toggle Lampu Flash/Torch
    * [Space] -> Freeze/Pause tampilan
    * [Q] -> Keluar
=============================================================================
"""

import os
import sys
import time
import math
import queue
import threading
import urllib.request
from urllib.parse import urlparse
import cv2
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from card_identifier import CardIdentifier

# Sumber kamera dibaca dari .env (var CAMERA_SOURCE)
_camera_source_raw = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE = int(_camera_source_raw) if _camera_source_raw.strip().isdigit() else _camera_source_raw

# Konfigurasi Real-Time
SHARPNESS_MIN = 60.0
REALTIME_ORB_POOL = 15     # Pool ringkas agar inferensi real-time sangat gesit (~120-180 ms)
CONFIDENCE_TEMP = 0.03

LABEL_COLOR = {
    "Tinggi": (0, 230, 115),    # Hijau neon
    "Sedang": (0, 215, 255),    # Kuning emas
    "Rendah": (0, 90, 255),     # Merah oranye
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
    except Exception:
        return False


def sharpness_score(gray_frame):
    return cv2.Laplacian(gray_frame, cv2.CV_64F).var()


def apply_camera_rotation(frame, rotation_deg):
    """Putar orientasi citra kamera jika HP dipegang secara tegak (portrait)."""
    if rotation_deg == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_deg == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    elif rotation_deg == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame


class RealtimeInferenceWorker(threading.Thread):
    """
    Worker thread terpisah yang menjalankan inferensi CLIP + FAISS secara asinkron
    sehingga UI streaming kamera utama tetap stabil 30+ FPS tanpa patah-patah.
    """
    def __init__(self, identifier):
        super().__init__(daemon=True)
        self.identifier = identifier
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = True
        self.latest_result = None
        self.latest_latency_ms = 0.0
        self.lock = threading.Lock()

    def update_frame(self, crop_bgr):
        # Jika queue penuh, buang frame lama dan masukkan frame paling baru
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self.frame_queue.put_nowait(crop_bgr)
        except queue.Full:
            pass

    def get_result(self):
        with self.lock:
            return self.latest_result, self.latest_latency_ms

    def run(self):
        while self.running:
            try:
                crop_bgr = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            t0 = time.time()
            try:
                # Inferensi cepat (top_k=3)
                res = self.identifier.identify_card(crop_bgr, top_k=3, auto_align=False)
                t1 = time.time()
                latency = round((t1 - t0) * 1000, 1)

                with self.lock:
                    self.latest_result = res
                    self.latest_latency_ms = latency
            except Exception as e:
                pass


def draw_hud(frame, x1, y1, x2, y2, scan_ratio, prediction, latency_ms, cam_fps, live_sharpness, is_paused=False, current_rotation=0):
    """
    Menggambar antarmuka Computer Vision bernuansa futuristik dan rapi
    tanpa overlap teks, dengan scanner beam, corner accents, dan status bar.
    """
    h, w = frame.shape[:2]
    out = frame.copy()

    # 1. Darken background di luar kotak deteksi
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (14, 15, 20), -1)
    cv2.addWeighted(overlay, 0.45, out, 0.55, 0, out)
    out[y1:y2, x1:x2] = frame[y1:y2, x1:x2]

    # 2. Kotak pembatas kartu & corner accents
    border_color = (0, 255, 255) if is_paused else (0, 200, 255)
    if prediction and prediction.get("candidates") and live_sharpness >= SHARPNESS_MIN:
        top_label = prediction["candidates"][0].get("confidence_label", "Rendah")
        border_color = LABEL_COLOR.get(top_label, border_color)

    cv2.rectangle(out, (x1, y1), (x2, y2), border_color, 2)

    corner_len = 28
    corner_thick = 3
    # TL
    cv2.line(out, (x1, y1), (x1 + corner_len, y1), border_color, corner_thick)
    cv2.line(out, (x1, y1), (x1, y1 + corner_len), border_color, corner_thick)
    # TR
    cv2.line(out, (x2, y1), (x2 - corner_len, y1), border_color, corner_thick)
    cv2.line(out, (x2, y1), (x2, y1 + corner_len), border_color, corner_thick)
    # BL
    cv2.line(out, (x1, y2), (x1 + corner_len, y2), border_color, corner_thick)
    cv2.line(out, (x1, y2), (x1, y2 - corner_len), border_color, corner_thick)
    # BR
    cv2.line(out, (x2, y2), (x2 - corner_len, y2), border_color, corner_thick)
    cv2.line(out, (x2, y2), (x2, y2 - corner_len), border_color, corner_thick)

    # 3. Animasi laser scanning beam bergerak vertikal
    if not is_paused:
        beam_y = int(y1 + (y2 - y1) * scan_ratio)
        beam_overlay = out.copy()
        cv2.line(beam_overlay, (x1 + 2, beam_y), (x2 - 2, beam_y), (0, 255, 255), 2)
        cv2.rectangle(beam_overlay, (x1 + 2, max(y1, beam_y - 6)), (x2 - 2, min(y2, beam_y + 6)), (0, 220, 255), -1)
        cv2.addWeighted(beam_overlay, 0.25, out, 0.75, 0, out)

    # 4. Header Bar Atas (Rapi dua baris terpisah, bebas tabrakan)
    header_h = 70
    cv2.rectangle(out, (0, 0), (w, header_h), (18, 20, 26), -1)
    cv2.line(out, (0, header_h), (w, header_h), (50, 55, 70), 1)

    # Baris 1 Header: Judul App & Status Badge
    title_text = "REGOKEMON - AI VISION SCANNER"
    cv2.putText(out, title_text, (18, 30), cv2.FONT_HERSHEY_DUPLEX, 0.60, (255, 255, 255), 1)

    status_tag = "PAUSED" if is_paused else "LIVE"
    status_col = (0, 215, 255) if is_paused else (0, 240, 120)
    tag_w = 75
    cv2.rectangle(out, (w - tag_w - 18, 12), (w - 18, 36), (30, 35, 45), -1)
    cv2.rectangle(out, (w - tag_w - 18, 12), (w - 18, 36), status_col, 1)
    cv2.putText(out, status_tag, (w - tag_w - 8, 29), cv2.FONT_HERSHEY_DUPLEX, 0.44, status_col, 1)

    # Baris 2 Header: FPS & AI Latency
    infer_fps = (1000.0 / latency_ms) if latency_ms > 0 else 0.0
    stats_text = f"FPS: {cam_fps:.0f}  |  Inferensi: {latency_ms:.0f} ms (~{infer_fps:.1f}/s)"
    cv2.putText(out, stats_text, (18, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1)

    # 5. Panel Informasi Hasil Deteksi Bawah (Tinggi 185px)
    panel_h = 185
    panel_y = h - panel_h
    cv2.rectangle(out, (0, panel_y), (w, h), (18, 20, 26), -1)
    cv2.line(out, (0, panel_y), (w, panel_y), (0, 200, 255), 2)

    footer_h = 32

    if prediction and prediction.get("candidates") and live_sharpness >= SHARPNESS_MIN:
        cands = prediction["candidates"]
        top = cands[0]
        raw_name = top.get("name", "Unknown Card")
        name = raw_name if len(raw_name) <= 20 else raw_name[:18] + ".."
        set_name = top.get("set_name", "-")
        card_id = top.get("card_id", "-")
        conf_pct = top.get("confidence_percentage", 0.0)
        label = top.get("confidence_label", "Rendah")
        label_col = LABEL_COLOR.get(label, (255, 255, 255))

        # Baris 1: Nama Kartu + Badge Confidence di kanan
        cv2.putText(out, name, (18, panel_y + 36), cv2.FONT_HERSHEY_DUPLEX, 0.82, (255, 255, 255), 2)

        badge_w = 165
        badge_h = 32
        badge_x = w - badge_w - 18
        badge_y = panel_y + 12
        cv2.rectangle(out, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), (28, 32, 42), -1)
        cv2.rectangle(out, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), label_col, 2)
        badge_str = f"{conf_pct:.1f}% [{label}]"
        cv2.putText(out, badge_str, (badge_x + 10, badge_y + 22), cv2.FONT_HERSHEY_DUPLEX, 0.48, label_col, 1)

        # Baris 2: Set & ID Kartu
        set_info = f"Set: {set_name}  |  ID: {card_id}"
        if len(set_info) > 42:
            set_info = set_info[:40] + ".."
        cv2.putText(out, set_info, (18, panel_y + 68), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (175, 190, 210), 1)

        # Baris 3: Runner-up candidates
        if len(cands) > 1:
            runner_items = [f"#{c['rank']} {c.get('name','?')[:12]}" for c in cands[1:3]]
            runner_str = "Lainnya: " + "  |  ".join(runner_items)
            cv2.putText(out, runner_str, (18, panel_y + 98), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (135, 150, 170), 1)

        # Baris 4: Ketajaman Sensor
        sharp_str = f"Sensor: {live_sharpness:.0f} (Fokus Tajam)"
        cv2.putText(out, sharp_str, (18, panel_y + 128), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 120), 1)
    else:
        # Tampilan saat kartu belum pas / belum terdeteksi
        status_msg = "Mencari kartu Pokemon..."
        guide_sub = "Arahkan kartu pas di dalam kotak"
        if live_sharpness < SHARPNESS_MIN:
            status_msg = "Sensor Kurang Fokus / Goyang"
            guide_sub = "Tahan HP lebih tenang atau tekan 'F'"

        cv2.putText(out, status_msg, (18, panel_y + 42), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 215, 255), 2)
        cv2.putText(out, guide_sub, (18, panel_y + 78), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 195, 210), 1)
        sharp_col = (0, 220, 120) if live_sharpness >= SHARPNESS_MIN else (0, 120, 255)
        cv2.putText(out, f"Ketajaman Sensor: {live_sharpness:.0f} (Min: {SHARPNESS_MIN:.0f})", (18, panel_y + 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, sharp_col, 1)

    # 6. Bar Petunjuk Kontrol Paling Bawah (Dedicated Background, tidak pernah overlap)
    cv2.rectangle(out, (0, h - footer_h), (w, h), (12, 13, 18), -1)
    cv2.line(out, (0, h - footer_h), (w, h - footer_h), (35, 40, 50), 1)
    controls_text = f"[Spasi] Pause | [R] Rotasi:{current_rotation} deg | [F] Fokus | [L] Flash | [Q] Keluar"
    cv2.putText(out, controls_text, (15, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 165, 185), 1)

    return out


def main():
    print("=================================================================")
    print("Regokemon - Pemindai Kartu Pokemon Real-Time (Live Computer Vision)")
    print("=================================================================")
    print("Memuat AI Engine (CLIP ViT-B-32 + FAISS + Realtime ORB)...")

    try:
        identifier = CardIdentifier(use_tta=False, use_orb_rerank=True,
                                     orb_rerank_pool_size=REALTIME_ORB_POOL)
        print("[OK] AI Engine berhasil dimuat!")
    except Exception as e:
        print(f"[ERROR] Gagal memuat AI Engine: {e}")
        return

    # Inisialisasi background inference worker
    worker = RealtimeInferenceWorker(identifier)
    worker.start()
    print("[OK] Background Inference Worker aktif.")

    print(f"\n[INFO] Menghubungkan ke kamera: {CAMERA_SOURCE}")
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"[ERROR] Tidak dapat membuka sumber kamera: {CAMERA_SOURCE}")
        return

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[OK] Kamera terhubung! Resolusi Sensor: {actual_w}x{actual_h}")

    WINDOW_NAME = "Regokemon - Real-Time Pokemon Card Scanner"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    # Tampilkan jendela proporsional dan nyaman di layar laptop
    cv2.resizeWindow(WINDOW_NAME, 560, 920)

    is_phone_stream = isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.startswith("http")
    default_rot = 90 if is_phone_stream else 0
    current_rotation = int(os.getenv("CAMERA_ROTATION", str(default_rot)))

    is_torch_on = False
    is_paused = False
    paused_frame = None

    fps_tracker = []
    t_prev = time.time()
    scan_phase = 0.0

    print("\n-----------------------------------------------------------------")
    print("SISTEM REAL-TIME SIAP!")
    print("• Arahkan kartu ke dalam kotak panduan.")
    print("• Program akan mengenali kartu secara langsung dan kontinu.")
    print("• [Spasi] : Freeze/Pause tampilan untuk menunjukkan hasil ke dosen.")
    print("• [R]     : Putar Orientasi Layar (0° / 90° / 180° / 270°).")
    print("• [F]     : Memicu Auto-Focus kamera HP.")
    print("• [L]     : Toggle Flash HP.")
    print("• [Q]     : Keluar.")
    print("-----------------------------------------------------------------\n")

    try:
        while True:
            t_now = time.time()
            dt = t_now - t_prev
            t_prev = t_now
            if dt > 0:
                fps_tracker.append(1.0 / dt)
                if len(fps_tracker) > 20:
                    fps_tracker.pop(0)
            current_cam_fps = float(np.mean(fps_tracker)) if fps_tracker else 30.0

            if not is_paused:
                ret, frame = cap.read()
                if not ret:
                    print("Gagal membaca frame kamera.")
                    break
                if current_rotation != 0:
                    frame = apply_camera_rotation(frame, current_rotation)
                active_frame = frame
            else:
                active_frame = paused_frame

            h, w, _ = active_frame.shape

            # Ruang vertikal antara Header (70px) dan Panel Bawah (185px)
            top_margin = 75
            bottom_margin = 195
            available_h = h - top_margin - bottom_margin

            # Hitung proporsi kotak kartu adaptif terhadap portrait/landscape (63:88)
            card_aspect = 63.0 / 88.0
            if h > w:
                # Mode Portrait (HP dipegang tegak)
                CARD_WIDTH = int(w * 0.74)
                CARD_HEIGHT = int(CARD_WIDTH / card_aspect)
                if CARD_HEIGHT > available_h:
                    CARD_HEIGHT = int(available_h * 0.92)
                    CARD_WIDTH = int(CARD_HEIGHT * card_aspect)
            else:
                # Mode Landscape
                CARD_HEIGHT = int(available_h * 0.85)
                CARD_WIDTH = int(CARD_HEIGHT * card_aspect)

            x1 = int((w - CARD_WIDTH) / 2)
            y1 = int(top_margin + (available_h - CARD_HEIGHT) / 2)
            x2 = x1 + CARD_WIDTH
            y2 = y1 + CARD_HEIGHT

            card_crop = active_frame[y1:y2, x1:x2]
            gray_crop = cv2.cvtColor(card_crop, cv2.COLOR_BGR2GRAY)
            live_sharp = sharpness_score(gray_crop)

            # Kirim frame ke background worker jika tidak di-pause dan gambar cukup fokus
            if not is_paused and live_sharp >= (SHARPNESS_MIN * 0.5):
                worker.update_frame(card_crop)

            # Ambil hasil prediksi asinkron terbaru
            prediction, latency_ms = worker.get_result()

            # Hitung posisi animasi laser beam (bolak-balik atas-bawah)
            scan_phase = (scan_phase + dt * 1.3) % (2 * math.pi)
            scan_ratio = (math.sin(scan_phase) + 1.0) / 2.0

            hud_frame = draw_hud(active_frame, x1, y1, x2, y2, scan_ratio,
                                 prediction, latency_ms, current_cam_fps, live_sharp, is_paused, current_rotation)

            cv2.imshow(WINDOW_NAME, hud_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                is_paused = not is_paused
                paused_frame = active_frame.copy() if is_paused else None
                status_str = "PAUSED" if is_paused else "RESUMED"
                print(f"[info] Video {status_str}")
            elif key == ord('r'):
                current_rotation = (current_rotation + 90) % 360
                print(f"[kamera] Rotasi layar diubah ke: {current_rotation}°")
            elif key == ord('f'):
                print("[remote] Mengirim Auto-Focus ke HP...")
                send_ipwebcam_cmd("focus")
            elif key == ord('l'):
                is_torch_on = not is_torch_on
                ep = "enabletorch" if is_torch_on else "disabletorch"
                send_ipwebcam_cmd(ep)
                print(f"[remote] Lampu Flash HP: {'ON' if is_torch_on else 'OFF'}")

    finally:
        worker.running = False
        cap.release()
        cv2.destroyAllWindows()
        print("\nProgram Real-Time selesai ditutup.")


if __name__ == "__main__":
    main()
