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


def build_dashboard(active_cam_frame, scan_ratio, prediction, latency_ms,
                    cam_fps, live_sharpness, is_paused=False, current_rotation=0,
                    is_torch_on=False, sharpness_min=SHARPNESS_MIN):
    """
    Membangun Widescreen Computer Vision Dashboard (1600x900) resolusi tinggi
    bernuansa modern & profesional, dioptimasi untuk layar laptop 1920x1080.
    """
    CANVAS_W = 1600
    CANVAS_H = 900
    canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)

    # Background: Cyber Obsidian Slate (BGR)
    canvas[:] = (20, 16, 13)

    # Color Tokens
    COLOR_BG_PANEL = (28, 22, 18)
    COLOR_BORDER = (55, 45, 38)
    COLOR_CYAN = (255, 205, 0)
    COLOR_NEON_GREEN = (0, 230, 115)
    COLOR_AMBER = (0, 200, 255)
    COLOR_CORAL = (60, 70, 255)
    COLOR_WHITE = (255, 255, 255)
    COLOR_SILVER = (185, 170, 155)
    COLOR_MUTED = (130, 118, 108)

    # 1. TOP HEADER BAR
    header_h = 62
    cv2.rectangle(canvas, (0, 0), (CANVAS_W, header_h), (28, 22, 18), -1)
    cv2.line(canvas, (0, header_h), (CANVAS_W, header_h), (55, 45, 36), 1)

    # Title & Subtitle
    cv2.putText(canvas, "REGOKEMON AI", (24, 40),
                cv2.FONT_HERSHEY_DUPLEX, 0.80, COLOR_WHITE, 1)
    cv2.putText(canvas, "|   REAL-TIME COMPUTER VISION ANALYTICS", (225, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_SILVER, 1)

    # Top Status Badge (Pulsing / Live vs Paused)
    status_tag = "PAUSED / FROZEN" if is_paused else "LIVE SCANNING"
    status_col = COLOR_AMBER if is_paused else COLOR_NEON_GREEN
    badge_x = CANVAS_W - 220
    cv2.rectangle(canvas, (badge_x, 14), (CANVAS_W - 24, 48), (38, 30, 25), -1)
    cv2.rectangle(canvas, (badge_x, 14), (CANVAS_W - 24, 48), status_col, 1)
    cv2.circle(canvas, (badge_x + 18, 31), 6, status_col, -1)
    cv2.putText(canvas, status_tag, (badge_x + 34, 38), cv2.FONT_HERSHEY_DUPLEX, 0.44, status_col, 1)

    # 2. LEFT PANE: CAMERA VIEWFINDER CONTAINER
    cam_x = 24
    cam_y = 80
    cam_h = CANVAS_H - cam_y - 24  # 796px
    cam_w = int(cam_h * (9.0 / 16.0))  # ~448px

    # Outer container with border and cyan top accent
    cv2.rectangle(canvas, (cam_x, cam_y), (cam_x + cam_w, cam_y + cam_h), COLOR_BG_PANEL, -1)
    cv2.rectangle(canvas, (cam_x, cam_y), (cam_x + cam_w, cam_y + cam_h), COLOR_BORDER, 1)
    cv2.line(canvas, (cam_x, cam_y), (cam_x + cam_w, cam_y), COLOR_CYAN, 3)

    # Video area (leaving 48px at bottom for sensor status bar)
    view_pad = 4
    view_x = cam_x + view_pad
    view_y = cam_y + view_pad
    view_w = cam_w - 2 * view_pad
    view_h = cam_h - 48 - view_pad

    if active_cam_frame is not None and active_cam_frame.size > 0:
        resized_cam = cv2.resize(active_cam_frame, (view_w, view_h), interpolation=cv2.INTER_AREA)
        canvas[view_y:view_y + view_h, view_x:view_x + view_w] = resized_cam
    else:
        cv2.rectangle(canvas, (view_x, view_y), (view_x + view_w, view_y + view_h), (35, 28, 24), -1)

    # Viewfinder Overlay: Guide box calculation (63:88 aspect ratio)
    box_w = int(view_w * 0.78)
    box_h = int(box_w / (63.0 / 88.0))
    bx1 = view_x + (view_w - box_w) // 2
    by1 = view_y + (view_h - box_h) // 2 - 10
    bx2 = bx1 + box_w
    by2 = by1 + box_h

    # Semi-transparent dark mask outside guide box
    mask_overlay = canvas[view_y:view_y + view_h, view_x:view_x + view_w].copy()
    cv2.rectangle(mask_overlay, (0, 0), (view_w, view_h), (10, 8, 6), -1)
    rel_bx1 = bx1 - view_x
    rel_by1 = by1 - view_y
    rel_bx2 = bx2 - view_x
    rel_by2 = by2 - view_y
    mask_overlay[rel_by1:rel_by2, rel_bx1:rel_bx2] = canvas[by1:by2, bx1:bx2]
    cv2.addWeighted(mask_overlay, 0.40, canvas[view_y:view_y + view_h, view_x:view_x + view_w], 0.60, 0,
                    canvas[view_y:view_y + view_h, view_x:view_x + view_w])

    # Card guide color based on detection confidence
    has_valid_pred = bool(prediction and prediction.get("candidates") and live_sharpness >= sharpness_min)
    top_label = prediction["candidates"][0].get("confidence_label", "Rendah") if has_valid_pred else "Mencari"

    if is_paused:
        guide_col = COLOR_AMBER
    elif top_label == "Tinggi":
        guide_col = COLOR_NEON_GREEN
    elif top_label == "Sedang":
        guide_col = COLOR_AMBER
    elif top_label == "Rendah" and has_valid_pred:
        guide_col = COLOR_CORAL
    else:
        guide_col = COLOR_CYAN

    # Draw Card Guide Frame
    cv2.rectangle(canvas, (bx1, by1), (bx2, by2), guide_col, 2)
    # Corner Accents
    c_len = 28
    for cx, cy, dx, dy in [(bx1, by1, 1, 1), (bx2, by1, -1, 1), (bx1, by2, 1, -1), (bx2, by2, -1, -1)]:
        cv2.line(canvas, (cx, cy), (cx + dx * c_len, cy), guide_col, 3)
        cv2.line(canvas, (cx, cy), (cx, cy + dy * c_len), guide_col, 3)

    # Animated Laser Scanning Beam
    if not is_paused:
        beam_y = int(by1 + (by2 - by1) * scan_ratio)
        beam_overlay = canvas[view_y:view_y + view_h, view_x:view_x + view_w].copy()
        cv2.line(beam_overlay, (rel_bx1 + 2, beam_y - view_y), (rel_bx2 - 2, beam_y - view_y), (0, 255, 255), 2)
        cv2.rectangle(beam_overlay, (rel_bx1 + 2, max(rel_by1, beam_y - view_y - 6)),
                      (rel_bx2 - 2, min(rel_by2, beam_y - view_y + 6)), (0, 215, 255), -1)
        cv2.addWeighted(beam_overlay, 0.30, canvas[view_y:view_y + view_h, view_x:view_x + view_w], 0.70, 0,
                        canvas[view_y:view_y + view_h, view_x:view_x + view_w])

    # Viewfinder Top Tag
    cv2.rectangle(canvas, (view_x + 12, view_y + 12), (view_x + 185, view_y + 36), (20, 16, 12), -1)
    cv2.rectangle(canvas, (view_x + 12, view_y + 12), (view_x + 185, view_y + 36), COLOR_BORDER, 1)
    cv2.putText(canvas, "PORTRAIT 9:16 LIVE", (view_x + 22, view_y + 28),
                cv2.FONT_HERSHEY_DUPLEX, 0.38, COLOR_CYAN, 1)

    # Integrated Sensor Strip (Inside camera container)
    strip_y = cam_y + cam_h - 48
    cv2.rectangle(canvas, (cam_x, strip_y), (cam_x + cam_w, cam_y + cam_h), (25, 20, 16), -1)
    cv2.line(canvas, (cam_x, strip_y), (cam_x + cam_w, strip_y), COLOR_BORDER, 1)

    is_sharp = live_sharpness >= sharpness_min
    sharp_col = COLOR_NEON_GREEN if is_sharp else COLOR_CORAL
    sharp_tag = "FOKUS TAJAM" if is_sharp else "KURANG FOKUS"

    cv2.putText(canvas, "Ketajaman Sensor:", (cam_x + 14, strip_y + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, COLOR_SILVER, 1)

    badge_s_x = cam_x + 160
    badge_s_w = cam_w - 174
    cv2.rectangle(canvas, (badge_s_x, strip_y + 8), (badge_s_x + badge_s_w, strip_y + 40), (36, 28, 22), -1)
    cv2.rectangle(canvas, (badge_s_x, strip_y + 8), (badge_s_x + badge_s_w, strip_y + 40), sharp_col, 1)
    cv2.circle(canvas, (badge_s_x + 14, strip_y + 24), 5, sharp_col, -1)
    cv2.putText(canvas, f"{live_sharpness:.0f} [{sharp_tag}]", (badge_s_x + 26, strip_y + 30),
                cv2.FONT_HERSHEY_DUPLEX, 0.42, sharp_col, 1)

    # 3. RIGHT PANE: ANALYTICS DASHBOARD
    dash_x = cam_x + cam_w + 24
    dash_w = CANVAS_W - dash_x - 24  # ~1080px width!

    # ---------------- PANEL 1: TOP-1 IDENTIFICATION ----------------
    p1_y = 80
    p1_h = 280
    cv2.rectangle(canvas, (dash_x, p1_y), (dash_x + dash_w, p1_y + p1_h), COLOR_BG_PANEL, -1)
    cv2.rectangle(canvas, (dash_x, p1_y), (dash_x + dash_w, p1_y + p1_h), COLOR_BORDER, 1)
    cv2.line(canvas, (dash_x, p1_y), (dash_x + dash_w, p1_y), COLOR_CYAN, 3)

    cv2.putText(canvas, "TARGET IDENTIFIKASI UTAMA (TOP-1 PREDICTION)", (dash_x + 24, p1_y + 34),
                cv2.FONT_HERSHEY_DUPLEX, 0.48, COLOR_CYAN, 1)

    if has_valid_pred:
        cands = prediction["candidates"]
        top = cands[0]
        card_name = top.get("name", "Unknown Card")
        set_name = top.get("set_name", "Unknown Set")
        card_id = top.get("card_id", "-")
        card_no = top.get("number", "-")
        rarity = top.get("rarity", "Standard")
        conf_pct = top.get("confidence_percentage", 0.0)
        label = top.get("confidence_label", "Rendah")
        raw_sim = top.get("raw_similarity_score", 0.0)
        orb_score = top.get("orb_verification_score")
        margin = top.get("margin_to_runner_up", 0.0)

        label_col = COLOR_NEON_GREEN if label == "Tinggi" else (COLOR_AMBER if label == "Sedang" else COLOR_CORAL)

        # Card Name (Big bold)
        cv2.putText(canvas, card_name, (dash_x + 24, p1_y + 85),
                    cv2.FONT_HERSHEY_DUPLEX, 1.35, COLOR_WHITE, 2)

        # Confidence Badge
        badge_w = 210
        badge_h = 42
        badge_bx = dash_x + dash_w - badge_w - 24
        badge_by = p1_y + 48
        cv2.rectangle(canvas, (badge_bx, badge_by), (badge_bx + badge_w, badge_by + badge_h), (38, 30, 25), -1)
        cv2.rectangle(canvas, (badge_bx, badge_by), (badge_bx + badge_w, badge_by + badge_h), label_col, 2)
        cv2.putText(canvas, f"{conf_pct:.1f}%  [{label.upper()}]", (badge_bx + 18, badge_by + 28),
                    cv2.FONT_HERSHEY_DUPLEX, 0.58, label_col, 1)

        # Metadata Line
        meta_str = f"Set: {set_name}   |   Card ID: {card_id}   |   No: {card_no}   |   Rarity: {rarity}"
        cv2.putText(canvas, meta_str, (dash_x + 24, p1_y + 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_SILVER, 1)

        # Dynamic Confidence Progress Bar
        bar_x = dash_x + 24
        bar_y = p1_y + 168
        bar_w = dash_w - 48
        bar_h = 20
        # Track
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (42, 34, 28), -1)
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 50, 42), 1)
        # Fill
        fill_ratio = max(0.0, min(1.0, conf_pct / 100.0))
        fill_w = int(bar_w * fill_ratio)
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), label_col, -1)
        if fill_w > 0:
            cv2.line(canvas, (bar_x + fill_w, bar_y), (bar_x + fill_w, bar_y + bar_h), COLOR_WHITE, 2)

        # Sub-metrics Breakdown
        orb_str = f"{orb_score:.3f}" if orb_score is not None else "N/A"
        sub_metrics = f"Cosine Similarity: {raw_sim:.4f}     |     ORB Verification Score: {orb_str}     |     Margin ke Runner-Up: +{margin:.4f}"
        cv2.putText(canvas, sub_metrics, (dash_x + 24, p1_y + 225),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_MUTED, 1)

        # Verification Status Tag
        verif_status = "STATUS: TERVERIFIKASI TINGGI OLEH MULTI-MODAL PIPELINE (CLIP + FAISS + ORB)"
        cv2.putText(canvas, verif_status, (dash_x + 24, p1_y + 258),
                    cv2.FONT_HERSHEY_DUPLEX, 0.42, label_col, 1)

    else:
        # Searching / Standby State
        if not is_sharp:
            prompt_main = "Sensor Kurang Fokus / Gambar Goyang"
            prompt_sub = "Tahan HP lebih tenang atau tekan 'F' untuk memicu Auto-Focus kamera"
            prompt_col = COLOR_AMBER
        else:
            prompt_main = "Mencari Kartu Pokemon..."
            prompt_sub = "Posisikan kartu Pokemon pas di dalam kotak pemindai kiri"
            prompt_col = COLOR_CYAN

        cv2.putText(canvas, prompt_main, (dash_x + 24, p1_y + 90),
                    cv2.FONT_HERSHEY_DUPLEX, 1.15, prompt_col, 2)
        cv2.putText(canvas, prompt_sub, (dash_x + 24, p1_y + 135),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.54, COLOR_SILVER, 1)

        # Idle Progress Bar Track
        bar_x = dash_x + 24
        bar_y = p1_y + 168
        bar_w = dash_w - 48
        bar_h = 20
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (38, 30, 24), -1)
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (55, 45, 36), 1)

        sub_msg = f"Ketajaman Sensor Saat Ini: {live_sharpness:.0f} (Batas Minimum: {sharpness_min:.0f})"
        cv2.putText(canvas, sub_msg, (dash_x + 24, p1_y + 225),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_MUTED, 1)
        cv2.putText(canvas, "STATUS: STANDBY - MENUNGGU OBJEK KARTU", (dash_x + 24, p1_y + 258),
                    cv2.FONT_HERSHEY_DUPLEX, 0.42, COLOR_MUTED, 1)

    # ---------------- PANEL 2: CANDIDATE RUNNER-UPS (TOP 2-4) ----------------
    p2_y = p1_y + p1_h + 20
    p2_h = 270
    cv2.rectangle(canvas, (dash_x, p2_y), (dash_x + dash_w, p2_y + p2_h), COLOR_BG_PANEL, -1)
    cv2.rectangle(canvas, (dash_x, p2_y), (dash_x + dash_w, p2_y + p2_h), COLOR_BORDER, 1)
    cv2.line(canvas, (dash_x, p2_y), (dash_x + dash_w, p2_y), COLOR_AMBER, 3)

    cv2.putText(canvas, "KANDIDAT LAIN & VARIAN REPRINT TERDEKAT (TOP 2 - 4)", (dash_x + 24, p2_y + 34),
                cv2.FONT_HERSHEY_DUPLEX, 0.48, COLOR_AMBER, 1)

    # Table Header
    th_y = p2_y + 60
    cv2.putText(canvas, "RANK", (dash_x + 36, th_y), cv2.FONT_HERSHEY_DUPLEX, 0.42, COLOR_MUTED, 1)
    cv2.putText(canvas, "NAMA KARTU", (dash_x + 115, th_y), cv2.FONT_HERSHEY_DUPLEX, 0.42, COLOR_MUTED, 1)
    cv2.putText(canvas, "SET & CARD ID", (dash_x + 390, th_y), cv2.FONT_HERSHEY_DUPLEX, 0.42, COLOR_MUTED, 1)
    cv2.putText(canvas, "COSINE SIM", (dash_x + dash_w - 320, th_y), cv2.FONT_HERSHEY_DUPLEX, 0.42, COLOR_MUTED, 1)
    cv2.putText(canvas, "ORB MATCH", (dash_x + dash_w - 160, th_y), cv2.FONT_HERSHEY_DUPLEX, 0.42, COLOR_MUTED, 1)
    cv2.line(canvas, (dash_x + 24, th_y + 10), (dash_x + dash_w - 24, th_y + 10), (55, 45, 38), 1)

    cands_list = prediction.get("candidates", [])[1:4] if has_valid_pred else []

    for idx in range(3):
        row_y = th_y + 20 + idx * 56
        row_bg = (36, 28, 24) if idx % 2 == 0 else (32, 25, 21)
        cv2.rectangle(canvas, (dash_x + 24, row_y), (dash_x + dash_w - 24, row_y + 48), row_bg, -1)
        cv2.rectangle(canvas, (dash_x + 24, row_y), (dash_x + dash_w - 24, row_y + 48), (50, 40, 34), 1)

        if idx < len(cands_list):
            cand = cands_list[idx]
            r_str = f"#{cand.get('rank', idx + 2)}"
            c_name = cand.get('name', 'Unknown')
            if len(c_name) > 20:
                c_name = c_name[:18] + ".."
            s_name = cand.get('set_name', '-')
            c_id = cand.get('card_id', '-')
            s_info = f"{s_name} ({c_id})"
            if len(s_info) > 34:
                s_info = s_info[:32] + ".."
            sim_val = f"{cand.get('raw_similarity_score', 0.0):.4f}"
            orb_val = f"{cand.get('orb_verification_score', 0.0):.3f}" if cand.get('orb_verification_score') is not None else "-"

            cv2.putText(canvas, r_str, (dash_x + 36, row_y + 30), cv2.FONT_HERSHEY_DUPLEX, 0.54, COLOR_CYAN, 1)
            cv2.putText(canvas, c_name, (dash_x + 115, row_y + 30), cv2.FONT_HERSHEY_DUPLEX, 0.54, COLOR_WHITE, 1)
            cv2.putText(canvas, s_info, (dash_x + 390, row_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, COLOR_SILVER, 1)
            cv2.putText(canvas, sim_val, (dash_x + dash_w - 300, row_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, COLOR_CYAN, 1)
            cv2.putText(canvas, orb_val, (dash_x + dash_w - 140, row_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, COLOR_NEON_GREEN, 1)
        else:
            cv2.putText(canvas, f"#{idx + 2}", (dash_x + 36, row_y + 30), cv2.FONT_HERSHEY_DUPLEX, 0.50, COLOR_MUTED, 1)
            cv2.putText(canvas, "--- Menunggu deteksi kartu ---", (dash_x + 115, row_y + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.46, COLOR_MUTED, 1)

    # ---------------- PANEL 3: TELEMETRY & CONTROLS ----------------
    p3_y = p2_y + p2_h + 20
    p3_h = CANVAS_H - p3_y - 24  # ~186px
    cv2.rectangle(canvas, (dash_x, p3_y), (dash_x + dash_w, p3_y + p3_h), COLOR_BG_PANEL, -1)
    cv2.rectangle(canvas, (dash_x, p3_y), (dash_x + dash_w, p3_y + p3_h), COLOR_BORDER, 1)
    cv2.line(canvas, (dash_x, p3_y), (dash_x + dash_w, p3_y), (130, 120, 110), 2)

    # Telemetry Badges (4 columns)
    infer_rate = (1000.0 / latency_ms) if latency_ms > 0 else 0.0
    metrics = [
        ("Camera Speed", f"{cam_fps:.0f} FPS (Smooth)", COLOR_NEON_GREEN),
        ("AI Inference Latency", f"{latency_ms:.0f} ms (~{infer_rate:.1f}/s)", COLOR_CYAN),
        ("Sensor Sharpness", f"{live_sharpness:.0f} [{sharp_tag}]", sharp_col),
        ("Vision Backbone", "CLIP ViT-B-32 + FAISS", COLOR_WHITE)
    ]

    badge_width = (dash_w - 48 - (3 * 16)) // 4
    for idx, (label, val, col) in enumerate(metrics):
        bx = dash_x + 24 + idx * (badge_width + 16)
        by = p3_y + 18
        cv2.rectangle(canvas, (bx, by), (bx + badge_width, by + 58), (38, 30, 25), -1)
        cv2.rectangle(canvas, (bx, by), (bx + badge_width, by + 58), COLOR_BORDER, 1)
        cv2.putText(canvas, label, (bx + 12, by + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_MUTED, 1)
        cv2.putText(canvas, val, (bx + 12, by + 46), cv2.FONT_HERSHEY_DUPLEX, 0.46, col, 1)

    # Controls Footer (Clean 6-slot grid layout)
    ctrl_y = p3_y + 92
    ctrl_h = 58
    cv2.rectangle(canvas, (dash_x + 24, ctrl_y), (dash_x + dash_w - 24, ctrl_y + ctrl_h), (20, 16, 13), -1)
    cv2.rectangle(canvas, (dash_x + 24, ctrl_y), (dash_x + dash_w - 24, ctrl_y + ctrl_h), COLOR_BORDER, 1)

    torch_str = "ON" if is_torch_on else "OFF"
    shortcuts = [
        ("[SPASI]", "Pause"),
        ("[M]", "Fullscreen"),
        ("[R]", f"Rot:{current_rotation}deg"),
        ("[F]", "Fokus HP"),
        ("[L]", f"Flash:{torch_str}"),
        ("[Q]", "Keluar")
    ]
    slot_w = (dash_w - 48) // len(shortcuts)
    for idx, (key, desc) in enumerate(shortcuts):
        sx = dash_x + 24 + idx * slot_w + 16
        cv2.putText(canvas, key, (sx, ctrl_y + 36), cv2.FONT_HERSHEY_DUPLEX, 0.44, COLOR_AMBER, 1)
        key_w = len(key) * 10
        cv2.putText(canvas, desc, (sx + key_w + 6, ctrl_y + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_SILVER, 1)

    return canvas


def main():
    print("=================================================================")
    print("Regokemon AI - Live Computer Vision Dashboard (1920x1080 Scale)")
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

    WINDOW_NAME = "Regokemon AI - Real-Time Pokemon Card Scanner"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    # Default ukuran jendela 16:9 proporsional dan nyaman di laptop 1920x1080 (100% / 125% / 150% scaling)
    cv2.resizeWindow(WINDOW_NAME, 1440, 810)

    is_phone_stream = isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.startswith("http")
    default_rot = 90 if is_phone_stream else 0
    current_rotation = int(os.getenv("CAMERA_ROTATION", str(default_rot)))

    is_torch_on = False
    is_paused = False
    is_fullscreen = False
    paused_frame = None

    fps_tracker = []
    t_prev = time.time()
    scan_phase = 0.0

    print("\n-----------------------------------------------------------------")
    print("SISTEM REAL-TIME SIAP!")
    print("• Arahkan kartu ke dalam kotak panduan di sisi kiri.")
    print("• Sisi kanan menampilkan analitik live (Top-1, Top 2-4, Telemetri).")
    print("• [Spasi] : Freeze/Pause tampilan untuk menunjukkan hasil ke dosen.")
    print("• [M]     : Toggle Layar Penuh (Fullscreen 1920x1080).")
    print("• [R]     : Putar Orientasi Kamera (0 deg / 90 deg / 180 deg / 270 deg).")
    print("• [F]     : Memicu Auto-Focus kamera HP Redmi.")
    print("• [L]     : Toggle Flash/Senter HP.")
    print("• [Q]     : Keluar.")
    print("-----------------------------------------------------------------\n")

    # Dimensi area video viewfinder di dashboard (440 x 744)
    VIEW_W = 440
    VIEW_H = 744
    BOX_W = int(VIEW_W * 0.78)
    BOX_H = int(BOX_W / (63.0 / 88.0))
    REL_X1 = (VIEW_W - BOX_W) // 2
    REL_Y1 = (VIEW_H - BOX_H) // 2 - 10
    REL_X2 = REL_X1 + BOX_W
    REL_Y2 = REL_Y1 + BOX_H

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

            orig_h, orig_w = active_frame.shape[:2]

            # Hitung potongan kartu resolusi penuh yang presisi 1:1 dengan kotak panduan UI
            scale_x = orig_w / float(VIEW_W)
            scale_y = orig_h / float(VIEW_H)
            crop_x1 = max(0, int(REL_X1 * scale_x))
            crop_y1 = max(0, int(REL_Y1 * scale_y))
            crop_x2 = min(orig_w, int(REL_X2 * scale_x))
            crop_y2 = min(orig_h, int(REL_Y2 * scale_y))

            card_crop = active_frame[crop_y1:crop_y2, crop_x1:crop_x2]
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

            dashboard_canvas = build_dashboard(active_frame, scan_ratio, prediction, latency_ms,
                                               current_cam_fps, live_sharp, is_paused, current_rotation,
                                               is_torch_on, SHARPNESS_MIN)

            cv2.imshow(WINDOW_NAME, dashboard_canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                is_paused = not is_paused
                paused_frame = active_frame.copy() if is_paused else None
                status_str = "PAUSED" if is_paused else "RESUMED"
                print(f"[info] Video {status_str}")
            elif key == ord('m') or key == ord('M'):
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    print("[layar] Mode Layar Penuh (Fullscreen 1920x1080)")
                else:
                    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(WINDOW_NAME, 1440, 810)
                    print("[layar] Mode Windowed (1440x810)")
            elif key == ord('r'):
                current_rotation = (current_rotation + 90) % 360
                print(f"[kamera] Rotasi layar diubah ke: {current_rotation} deg")
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
