"""
Live Card Condition Tester
==========================
Menguji API Roboflow card-grader menggunakan webcam secara real-time.
Tampilkan guide frame di tengah layar untuk memposisikan kartu,
lalu crop area tersebut dan kirim ke API.

Kontrol:
  SPASI  - Freeze frame → crop area kartu → kirim ke API
  SPASI  - (saat freeze) Kembali ke live camera
  S      - Simpan screenshot
  Q/ESC  - Keluar

Cara pakai:
  cd backend/models
  python live_card_condition_test.py
"""

import os
import sys
import base64
import time
from pathlib import Path

import cv2
import requests
import numpy as np
from dotenv import load_dotenv

# ── Konfigurasi ──────────────────────────────────────────────────────────────
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
load_dotenv(_project_root / ".env")

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not ROBOFLOW_API_KEY:
    print("ERROR: ROBOFLOW_API_KEY tidak ditemukan di file .env!")
    print(f"Pastikan file .env ada di: {_project_root / '.env'}")
    sys.exit(1)

API_URL = f"https://detect.roboflow.com/card-grader/4?api_key={ROBOFLOW_API_KEY}"

CAMERA_INDEX = 0

# Rasio kartu standar (2.5 x 3.5 inci) ≈ 5:7
CARD_RATIO = 5 / 7  # width / height

# Seberapa besar guide frame relatif terhadap tinggi kamera (0.0 - 1.0).
# Nilai 0.75 membuat kartu lebih besar di dalam area panduan.
GUIDE_SCALE = 0.75

# Warna
CLASS_COLORS = {
    "Card":        (0, 255, 0),
    "Corner Wear": (0, 0, 255),
    "Edge Wear":   (0, 165, 255),
    "Scratch":     (255, 0, 255),
}
DEFAULT_COLOR = (255, 255, 0)
GUIDE_COLOR = (0, 255, 255)        # Kuning/cyan untuk guide frame
GUIDE_COLOR_FROZEN = (0, 200, 0)   # Hijau saat frozen


# ── Fungsi Utilitas ──────────────────────────────────────────────────────────
def get_guide_rect(frame_h: int, frame_w: int) -> tuple[int, int, int, int]:
    """Hitung koordinat guide rectangle (x1, y1, x2, y2) di tengah frame."""
    guide_h = int(frame_h * GUIDE_SCALE)
    guide_w = int(guide_h * CARD_RATIO)

    # Jika guide terlalu lebar untuk frame, batasi berdasarkan width
    if guide_w > frame_w * 0.85:
        guide_w = int(frame_w * 0.85)
        guide_h = int(guide_w / CARD_RATIO)

    cx = frame_w // 2
    cy = frame_h // 2

    x1 = cx - guide_w // 2
    y1 = cy - guide_h // 2
    x2 = cx + guide_w // 2
    y2 = cy + guide_h // 2

    return x1, y1, x2, y2


def draw_guide_frame(frame: np.ndarray, frozen: bool = False) -> np.ndarray:
    """Gambar guide frame di tengah + area luar di-dim."""
    overlay = frame.copy()
    fh, fw = frame.shape[:2]
    x1, y1, x2, y2 = get_guide_rect(fh, fw)

    # Dim area di luar guide (semi-transparent dark overlay)
    mask = np.zeros_like(frame, dtype=np.uint8)
    mask[:] = (0, 0, 0)
    # Buat mask: gelap di luar, transparan di dalam
    dark_overlay = frame.copy()
    cv2.rectangle(dark_overlay, (0, 0), (fw, fh), (0, 0, 0), -1)
    # Blend: area luar guide jadi gelap
    alpha = 0.5
    overlay = cv2.addWeighted(frame, 1, dark_overlay, 0, 0)
    # Restore area dalam guide ke asli
    # Caranya: buat full dark overlay, lalu copy inner rect dari frame asli
    dark = np.zeros_like(frame)
    blended = cv2.addWeighted(frame, 1 - alpha, dark, alpha, 0)
    blended[y1:y2, x1:x2] = frame[y1:y2, x1:x2]  # Area dalam tetap terang
    overlay = blended

    color = GUIDE_COLOR_FROZEN if frozen else GUIDE_COLOR
    thickness = 3 if frozen else 2

    # Gambar border guide
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)

    # Corner accents (garis kecil di 4 sudut)
    corner_len = 20
    # Top-left
    cv2.line(overlay, (x1, y1), (x1 + corner_len, y1), color, thickness + 2)
    cv2.line(overlay, (x1, y1), (x1, y1 + corner_len), color, thickness + 2)
    # Top-right
    cv2.line(overlay, (x2, y1), (x2 - corner_len, y1), color, thickness + 2)
    cv2.line(overlay, (x2, y1), (x2, y1 + corner_len), color, thickness + 2)
    # Bottom-left
    cv2.line(overlay, (x1, y2), (x1 + corner_len, y2), color, thickness + 2)
    cv2.line(overlay, (x1, y2), (x1, y2 - corner_len), color, thickness + 2)
    # Bottom-right
    cv2.line(overlay, (x2, y2), (x2 - corner_len, y2), color, thickness + 2)
    cv2.line(overlay, (x2, y2), (x2, y2 - corner_len), color, thickness + 2)

    # Label
    if not frozen:
        label = "Posisikan kartu di dalam frame"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        lx = (fw - tw) // 2
        ly = y1 - 12
        if ly < 20:
            ly = y2 + th + 12
        cv2.putText(overlay, label, (lx, ly),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return overlay


def crop_guide_area(frame: np.ndarray) -> np.ndarray:
    """Crop frame ke area guide rectangle saja."""
    fh, fw = frame.shape[:2]
    x1, y1, x2, y2 = get_guide_rect(fh, fw)
    return frame[y1:y2, x1:x2].copy()


def send_frame_to_roboflow(frame: np.ndarray) -> dict | None:
    """Encode frame OpenCV menjadi JPEG, kirim ke Roboflow, kembalikan JSON."""
    try:
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            print("[!] Gagal encode frame ke JPEG")
            return None

        image_data = base64.b64encode(buffer.tobytes()).decode("utf-8")

        response = requests.post(
            API_URL,
            data=image_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        print("[!] Request timeout — coba lagi")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[!] Request gagal: {e}")
        return None


def draw_detections(frame: np.ndarray, result: dict) -> np.ndarray:
    """Gambar bounding box dan label pada frame (cropped) berdasarkan hasil deteksi."""
    overlay = frame.copy()
    predictions = result.get("predictions", [])

    for pred in predictions:
        label = pred.get("class", "unknown")
        confidence = pred.get("confidence", 0)
        cx = int(pred["x"])
        cy = int(pred["y"])
        w = int(pred["width"])
        h = int(pred["height"])

        x1 = cx - w // 2
        y1 = cy - h // 2
        x2 = cx + w // 2
        y2 = cy + h // 2

        color = CLASS_COLORS.get(label, DEFAULT_COLOR)

        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)

        text = f"{label} {confidence:.1%}"
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(overlay, (x1, y1 - th - baseline - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(overlay, text, (x1 + 2, y1 - baseline - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return overlay


ALL_CLASSES = ["Card", "Corner Wear", "Edge Wear", "Scratch"]


def get_confidence_per_class(result: dict) -> dict[str, float]:
    """Ambil confidence maksimum per kelas dari hasil API."""
    conf = {label: 0.0 for label in ALL_CLASSES}
    for pred in result.get("predictions", []):
        label = pred.get("class")
        c = float(pred.get("confidence", 0.0))
        if label in conf:
            conf[label] = max(conf[label], c)
    return conf


def draw_status_bar(frame: np.ndarray, result: dict | None, analyzing: bool,
                    is_cropped: bool = False) -> np.ndarray:
    """Tambahkan status bar di bagian bawah frame dengan confidence semua kelas."""
    h, w = frame.shape[:2]
    bar_height = 140 if result is not None else 80
    canvas = np.zeros((h + bar_height, w, 3), dtype=np.uint8)
    canvas[:h, :w] = frame

    cv2.rectangle(canvas, (0, h), (w, h + bar_height), (40, 40, 40), -1)

    if analyzing:
        cv2.putText(canvas, "Menganalisis kartu...", (10, h + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(canvas, "Mengirim cropped image ke Roboflow API", (10, h + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    elif result is not None:
        conf = get_confidence_per_class(result)

        # Baris 1: header
        crop_tag = " [CROPPED]" if is_cropped else ""
        cv2.putText(canvas, f"Confidence Score per Kelas{crop_tag}", (10, h + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Baris 2-3: confidence tiap kelas dengan warna
        y_offset = h + 55
        x_pos = 10
        for i, label in enumerate(ALL_CLASSES):
            c = conf[label]
            color = CLASS_COLORS.get(label, DEFAULT_COLOR)

            if c > 0:
                text = f"{label}: {c:.1%}"
            else:
                text = f"{label}: -"
                color = (100, 100, 100)  # Abu-abu untuk yang tidak terdeteksi

            cv2.putText(canvas, text, (x_pos, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Pindah ke kolom berikutnya atau baris baru
            if i == 1:  # Setelah 2 item, pindah ke baris baru
                y_offset += 28
                x_pos = 10
            else:
                x_pos += w // 2

        # Baris 4: status defect
        defects = [p for p in result.get("predictions", []) if p.get("class") != "Card"]
        y_status = y_offset + 28
        if defects:
            cv2.putText(canvas, f"DEFECT TERDETEKSI: {len(defects)}", (10, y_status),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        else:
            cv2.putText(canvas, "Tidak ada defect terdeteksi", (10, y_status),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
    else:
        cv2.putText(canvas, "SPASI = Freeze & Analisis | Q = Keluar", (10, h + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        cv2.putText(canvas, "Posisikan kartu di dalam guide frame", (10, h + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    return canvas


# ── Main Loop ────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Live Card Condition Tester — Roboflow API")
    print("=" * 60)
    print(f"  Kamera     : index {CAMERA_INDEX}")
    print(f"  Model      : card-grader/4")
    print(f"  Guide Rasio: {CARD_RATIO:.3f} (kartu standar 2.5 x 3.5 in)")
    print(f"  Guide Scale: {GUIDE_SCALE:.0%} dari tinggi kamera")
    print("-" * 60)
    print("  SPASI = Freeze & Analisis / Kembali ke Live")
    print("  S     = Screenshot | Q/ESC = Keluar")
    print("=" * 60)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[!] Tidak bisa membuka kamera index {CAMERA_INDEX}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  Resolusi kamera: {actual_w}x{actual_h}")

    gx1, gy1, gx2, gy2 = get_guide_rect(actual_h, actual_w)
    print(f"  Guide frame   : ({gx1},{gy1}) -> ({gx2},{gy2})")
    print(f"  Crop size     : {gx2 - gx1}x{gy2 - gy1} piksel")

    frozen = False
    frozen_frame = None
    cropped_frame = None
    last_result = None
    window_name = "Live Card Condition Tester"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 800, 600)

    try:
        while True:
            # ── Mode LIVE ──
            if not frozen:
                ret, frame = cap.read()
                if not ret:
                    print("[!] Gagal membaca frame dari kamera")
                    break

                display = draw_guide_frame(frame, frozen=False)
                display = draw_status_bar(display, None, analyzing=False)
                cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF

            # ── SPASI ──
            if key == ord(" "):
                if not frozen:
                    # === FREEZE → CROP → KIRIM API ===
                    frozen = True
                    frozen_frame = frame.copy()

                    # Crop area guide
                    cropped_frame = crop_guide_area(frozen_frame)
                    crop_h, crop_w = cropped_frame.shape[:2]
                    print(f"\n[*] Frame di-freeze")
                    print(f"    Crop area: {crop_w}x{crop_h} piksel")
                    print(f"    Mengirim ke Roboflow...")

                    # Tampilkan freeze + status analyzing
                    freeze_display = draw_guide_frame(frozen_frame, frozen=True)
                    freeze_display = draw_status_bar(freeze_display, None, analyzing=True)
                    cv2.imshow(window_name, freeze_display)
                    cv2.waitKey(1)

                    # Kirim cropped image ke API
                    start_time = time.time()
                    result = send_frame_to_roboflow(cropped_frame)
                    elapsed = time.time() - start_time

                    if result is not None:
                        last_result = result
                        predictions = result.get("predictions", [])
                        print(f"[+] Selesai dalam {elapsed:.2f}s — {len(predictions)} prediksi")

                        # Confidence per kelas
                        conf = get_confidence_per_class(result)
                        print(f"    ┌─────────────────────────────────┐")
                        for label in ALL_CLASSES:
                            c = conf[label]
                            bar = "█" * int(c * 20)
                            status = f"{c:.1%}" if c > 0 else "tidak terdeteksi"
                            print(f"    │ {label:<12s} : {status:<18s} {bar}")
                        print(f"    └─────────────────────────────────┘")

                        defects = [p for p in predictions if p.get("class") != "Card"]
                        if defects:
                            print(f"[!] Defect terdeteksi: {len(defects)}")
                        else:
                            print("[✓] Tidak ada defect — kartu dalam kondisi baik!")

                        # Tampilkan hasil: cropped image + bounding box
                        result_display = draw_detections(cropped_frame, last_result)
                        result_display = draw_status_bar(result_display, last_result,
                                                         analyzing=False, is_cropped=True)
                        cv2.imshow(window_name, result_display)
                    else:
                        print("[!] Gagal mendapatkan hasil dari API")
                        fail_display = draw_status_bar(cropped_frame, None, analyzing=False)
                        cv2.imshow(window_name, fail_display)

                else:
                    # === UNFREEZE: kembali ke live ===
                    frozen = False
                    frozen_frame = None
                    cropped_frame = None
                    last_result = None
                    print("[*] Kembali ke live camera\n")

            # ── S: Screenshot ──
            elif key == ord("s") or key == ord("S"):
                if frozen and cropped_frame is not None:
                    screenshot = cropped_frame.copy()
                    if last_result is not None:
                        screenshot = draw_detections(screenshot, last_result)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"card_capture_{timestamp}.jpg"
                    save_path = _script_dir / filename
                    cv2.imwrite(str(save_path), screenshot)
                    print(f"[+] Screenshot disimpan: {save_path}")
                else:
                    print("[!] Tekan SPASI dulu untuk freeze & analisis")

            # ── Q / ESC ──
            elif key == ord("q") or key == ord("Q") or key == 27:
                print("\n[*] Keluar...")
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
