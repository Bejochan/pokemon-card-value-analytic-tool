"""
Image Card Condition Tester (with Preprocessing)
================================================
Menguji API Roboflow card-grader menggunakan file gambar statis.
Dilengkapi dengan fitur Image Preprocessing (Smart Resize & CLAHE) 
untuk meningkatkan akurasi deteksi defect sebelum dikirim ke API.

Cara pakai:
  python image_card_condition_test.py
"""

import os
import sys
import base64
import argparse
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
    sys.exit(1)

API_URL = f"https://detect.roboflow.com/card-grader/4?api_key={ROBOFLOW_API_KEY}"

ALL_CLASSES = ["Card", "Corner Wear", "Edge Wear", "Scratch"]

CLASS_COLORS = {
    "Card":        (0, 255, 0),    # Hijau
    "Corner Wear": (0, 0, 255),    # Merah
    "Edge Wear":   (0, 165, 255),  # Oranye
    "Scratch":     (255, 0, 255),  # Magenta
}
DEFAULT_COLOR = (255, 255, 0)      # Cyan


# ── FUNGSI IMAGE PREPROCESSING ───────────────────────────────────────────────
def preprocess_image(image: np.ndarray, max_size=1280) -> np.ndarray:
    """Melakukan preprocessing pada gambar sebelum dikirim ke API."""
    # 1. Smart Resize: Batasi dimensi maksimal agar upload cepat namun tetap tajam
    h, w = image.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Konversi ke ruang warna LAB agar manipulasi kontras tidak merusak warna RGB
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Aplikasikan algoritma CLAHE ke Lightness channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    
    # Gabungkan kembali dan konversi ke BGR
    merged = cv2.merge((cl, a_channel, b_channel))
    enhanced_image = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    
    return enhanced_image
# ────────────────────────────────────────────────────────────────────────────


def send_frame_to_roboflow(image: np.ndarray) -> dict | None:
    """Mengubah numpy array image ke JPEG memory dan mengirimnya ke API."""
    try:
        # Encode ke JPEG (Kualitas 95 - Sangat Tinggi)
        success, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not success:
            print("[!] ERROR: Gagal melakukan encode gambar ke JPEG.")
            return None

        # Konversi byte stream ke Base64
        image_data = base64.b64encode(buffer.tobytes()).decode("utf-8")

        print(f"[*] Mengirim gambar ke API Roboflow...")
        response = requests.post(
            API_URL,
            data=image_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"[!] Request gagal: {e}")
        return None


def draw_detections(frame: np.ndarray, result: dict) -> np.ndarray:
    """Menggambar bounding box di atas gambar."""
    overlay = frame.copy()
    predictions = result.get("predictions", [])

    height, width = overlay.shape[:2]
    scale_factor = max(width, height) / 1000.0
    line_thick = max(2, int(2 * scale_factor))
    font_scale = max(0.6, 0.6 * scale_factor)

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

        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, line_thick)
        text = f"{label} {confidence:.1%}"
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thick)
        cv2.rectangle(overlay, (x1, y1 - th - baseline - 10), (x1 + tw + 10, y1), color, -1)
        cv2.putText(overlay, text, (x1 + 5, y1 - baseline - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), line_thick)

    return overlay


def print_summary(result: dict):
    """Mencetak ringkasan hasil prediksi ke terminal."""
    predictions = result.get("predictions", [])
    print(f"\n[+] Analisis selesai — {len(predictions)} prediksi ditemukan")

    conf = {label: 0.0 for label in ALL_CLASSES}
    for pred in predictions:
        label = pred.get("class")
        c = float(pred.get("confidence", 0.0))
        if label in conf:
            conf[label] = max(conf[label], c)

    print(f"\n    -----------------------------------")
    for label in ALL_CLASSES:
        c = conf[label]
        status = f"{c:.1%}" if c > 0 else "tidak terdeteksi"
        print(f"    {label:<12s} : {status}")
    print(f"    -----------------------------------")

    defects = [p for p in predictions if p.get("class") != "Card"]
    print("\nKESIMPULAN:")
    if defects:
        print(f"[!] Ditemukan {len(defects)} defect pada kartu ini.")
        for d in defects:
            print(f"    - {d['class']} ({d['confidence']:.1%})")
    else:
        print("[✓] Kartu dalam kondisi baik (Tidak ada defect terdeteksi).")


def main():
    parser = argparse.ArgumentParser(description="Test Card Grader dengan gambar statis")
    parser.add_argument("image_path", nargs="?", help="Path ke file gambar (opsional)")
    args = parser.parse_args()

    image_path = args.image_path
    if not image_path:
        print("=" * 60)
        print("  Image Card Condition Tester (with Preprocessing)")
        print("=" * 60)
        image_path = input("Masukkan path file gambar (misal: C:/Users/gambar.jpg): ").strip()
        image_path = image_path.replace('"', '').replace("'", "")

    if not image_path:
        print("Path gambar tidak boleh kosong.")
        sys.exit(1)

    if not os.path.exists(image_path):
        print(f"ERROR: File tidak ditemukan di -> {image_path}")
        sys.exit(1)

    print(f"\n[*] Membaca gambar asli: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print("ERROR: Tidak dapat membaca gambar. Pastikan format file didukung (JPG, PNG).")
        sys.exit(1)
        
    orig_h, orig_w = image.shape[:2]
    print(f"[*] Resolusi asli: {orig_w}x{orig_h} piksel")

    # ----- PROSES PREPROCESSING -----
    print("[*] Mengaplikasikan Image Preprocessing (Smart Resize & CLAHE)...")
    processed_image = preprocess_image(image)
    proc_h, proc_w = processed_image.shape[:2]
    print(f"[*] Resolusi pasca-processing: {proc_w}x{proc_h} piksel")
    # --------------------------------

    # Kirim gambar hasil preprocess ke API (bukan gambar asli)
    result = send_frame_to_roboflow(processed_image)

    if result is not None:
        print_summary(result)
        
        # Gambar deteksi di atas gambar yang sudah dipreprocess agar kita melihat apa yang AI lihat
        annotated_image = draw_detections(processed_image, result)
        
        # Simpan output
        filename = Path(image_path).stem
        save_path = _script_dir / f"{filename}_preprocessed_result.jpg"
        cv2.imwrite(str(save_path), annotated_image)
        print(f"\n[+] Gambar hasil deteksi disimpan ke: {save_path}")

        # Tampilkan di layar
        display_img = annotated_image.copy()
        max_display_height = 800
        if proc_h > max_display_height:
            scale = max_display_height / proc_h
            display_img = cv2.resize(display_img, (int(proc_w * scale), max_display_height))
        
        print("\n[*] Menampilkan gambar... Tekan sembarang tombol pada jendela gambar untuk keluar.")
        window_name = f"Hasil Deteksi: {filename} (PREPROCESSED)"
        cv2.imshow(window_name, display_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
