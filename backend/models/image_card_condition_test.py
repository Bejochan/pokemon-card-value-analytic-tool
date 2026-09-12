import os
import sys
import base64
import argparse
from pathlib import Path

import cv2
import requests
import numpy as np
from dotenv import load_dotenv

_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
load_dotenv(_project_root / ".env")

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not ROBOFLOW_API_KEY:
    print("ERROR: ROBOFLOW_API_KEY tidak ditemukan di file .env!")
    sys.exit(1)

API_URL = f"https://detect.roboflow.com/card-grader/4?api_key={ROBOFLOW_API_KEY}&confidence=0"

CLASS_COLORS = {
    "Card":        (0, 255, 0),
    "Corner Wear": (0, 0, 255),
    "Edge Wear":   (0, 165, 255),
    "Scratch":     (255, 0, 255),
}
DEFAULT_COLOR = (255, 255, 0)

LOW_THRESH = 0.25
HIGH_THRESH = 0.55

CARD_ASPECT_RATIO = 63.0 / 88.0
CARD_OUT_SIZE = (600, 837)
CROP_MARGIN_RATIO = 0.08


def _order_points(pts):
    pts = pts.reshape(4, 2).astype("float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _aspect_ok(rect, tol=0.20):
    (tl, tr, br, bl) = rect
    w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2.0
    h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2.0
    if h == 0:
        return False
    return abs((w / h) - CARD_ASPECT_RATIO) / CARD_ASPECT_RATIO < tol


def _expand_rect(rect, ratio=CROP_MARGIN_RATIO):
    center = rect.mean(axis=0)
    return (center + (rect - center) * (1 + ratio)).astype("float32")


def auto_detect_card(image_np: np.ndarray, out_size=CARD_OUT_SIZE) -> np.ndarray | None:
    """Coba deteksi kontur kartu otomatis. Return None kalau gagal."""
    h_img, w_img = image_np.shape[:2]
    frame_area = h_img * w_img
    min_area = 0.05 * frame_area
    max_area = 0.95 * frame_area

    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    smooth = cv2.bilateralFilter(gray, d=9, sigmaColor=60, sigmaSpace=60)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_eq = clahe.apply(smooth)
    edges_base = cv2.Canny(gray_eq, 40, 120)

    for ksize, iters in [(5, 2), (7, 2), (9, 3), (11, 3), (13, 4)]:
        kernel = np.ones((ksize, ksize), np.uint8)
        edges = cv2.morphologyEx(edges_base, cv2.MORPH_CLOSE, kernel, iterations=iters)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        candidates = [c for c in contours if min_area < cv2.contourArea(c) < max_area]
        if not candidates:
            continue
        candidates.sort(key=cv2.contourArea, reverse=True)

        for c in candidates[:5]:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            if len(approx) == 4 and cv2.isContourConvex(approx):
                rect = _order_points(approx)
            else:
                min_rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(min_rect)
                rect = _order_points(box)

            if not _aspect_ok(rect):
                continue

            rect = _expand_rect(rect)
            width, height = out_size
            dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            return cv2.warpPerspective(image_np, M, (width, height), flags=cv2.INTER_CUBIC)

    return None


def manual_crop_card(image_np: np.ndarray, out_size=CARD_OUT_SIZE, margin_ratio=CROP_MARGIN_RATIO) -> np.ndarray | None:
    display = image_np.copy()
    h, w = display.shape[:2]
    max_display_height = 800
    scale = max_display_height / h if h > max_display_height else 1.0
    if scale != 1.0:
        display = cv2.resize(display, (int(w * scale), int(h * scale)))

    print("[*] Drag kotak di sekeliling kartu, lalu tekan ENTER.")
    print("    Tekan ESC untuk skip dan pakai deteksi otomatis.")
    roi = cv2.selectROI("Pilih area kartu", display, showCrosshair=True)
    cv2.destroyWindow("Pilih area kartu")

    x, y, w_roi, h_roi = roi
    if w_roi == 0 or h_roi == 0:
        return None

    x, y, w_roi, h_roi = [v / scale for v in (x, y, w_roi, h_roi)]

    # tambahkan margin di semua sisi, clamp supaya tidak keluar batas gambar asli
    img_h, img_w = image_np.shape[:2]
    mx, my = w_roi * margin_ratio, h_roi * margin_ratio
    x1 = max(0, int(x - mx))
    y1 = max(0, int(y - my))
    x2 = min(img_w, int(x + w_roi + mx))
    y2 = min(img_h, int(y + h_roi + my))

    cropped = image_np[y1:y2, x1:x2]
    return cv2.resize(cropped, out_size, interpolation=cv2.INTER_CUBIC)


def get_card_crop(image_np: np.ndarray, out_size=CARD_OUT_SIZE) -> np.ndarray:
    cropped = manual_crop_card(image_np, out_size)
    if cropped is not None:
        return cropped

    print("[*] Mencoba deteksi otomatis...")
    cropped = auto_detect_card(image_np, out_size)
    if cropped is not None:
        return cropped

    print("[!] Deteksi otomatis gagal, memakai resize seadanya.")
    return cv2.resize(image_np, out_size, interpolation=cv2.INTER_AREA)


def send_frame_to_roboflow(image: np.ndarray) -> dict | None:
    try:
        success, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not success:
            print("[!] ERROR: Gagal melakukan encode gambar ke JPEG.")
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

    except requests.exceptions.RequestException as e:
        print(f"[!] Request gagal: {e}")
        return None


def classify_defect_severity(predictions: list[dict],
                              low_thresh=LOW_THRESH,
                              high_thresh=HIGH_THRESH) -> list[dict]:
    results = []
    for pred in predictions:
        if pred.get("class") == "Card":
            continue

        conf = float(pred.get("confidence", 0.0))
        if conf < low_thresh:
            continue

        certainty = "Terindikasi (perlu verifikasi ulang)" if conf < high_thresh else "Terdeteksi"

        results.append({
            "class": pred["class"],
            "confidence": conf,
            "certainty": certainty,
            "x": pred.get("x"),
            "y": pred.get("y"),
            "width": pred.get("width"),
            "height": pred.get("height"),
        })
    return results


def draw_detections(frame: np.ndarray, detections: list[dict]) -> np.ndarray:
    overlay = frame.copy()
    height, width = overlay.shape[:2]
    scale_factor = max(width, height) / 1000.0
    line_thick = max(2, int(2 * scale_factor))
    font_scale = max(0.6, 0.6 * scale_factor)

    for det in detections:
        label = det["class"]
        confidence = det["confidence"]
        certainty = det["certainty"]

        cx, cy = int(det["x"]), int(det["y"])
        w, h = int(det["width"]), int(det["height"])
        x1, y1 = cx - w // 2, cy - h // 2
        x2, y2 = cx + w // 2, cy + h // 2

        color = CLASS_COLORS.get(label, DEFAULT_COLOR)
        thickness = line_thick if certainty == "Terdeteksi" else max(1, line_thick - 1)

        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)
        tag = "✓" if certainty == "Terdeteksi" else "?"
        text = f"{label} {confidence:.1%} {tag}"
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thick)
        cv2.rectangle(overlay, (x1, y1 - th - baseline - 10), (x1 + tw + 10, y1), color, -1)
        cv2.putText(overlay, text, (x1 + 5, y1 - baseline - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), line_thick)

    return overlay


def print_summary(detections: list[dict]):
    print(f"\n[+] Analisis selesai — {len(detections)} defect terklasifikasi\n")
    print("    -----------------------------------")
    for cls in ["Corner Wear", "Edge Wear", "Scratch"]:
        matches = [d for d in detections if d["class"] == cls]
        if matches:
            best = max(matches, key=lambda d: d["confidence"])
            print(f"    {cls:<12s} : {best['confidence']:.1%}  [{best['certainty']}]")
        else:
            print(f"    {cls:<12s} : tidak terdeteksi")
    print("    -----------------------------------")

    solid = [d for d in detections if d["certainty"] == "Terdeteksi"]
    indicated = [d for d in detections if d["certainty"] != "Terdeteksi"]

    print("\nKESIMPULAN:")
    if solid:
        print(f"[!] {len(solid)} defect terkonfirmasi solid:")
        for d in solid:
            print(f"    - {d['class']} ({d['confidence']:.1%})")
    if indicated:
        print(f"[?] {len(indicated)} defect di zona abu-abu:")
        for d in indicated:
            print(f"    - {d['class']} ({d['confidence']:.1%})")
    if not solid and not indicated:
        print("[✓] Kartu dalam kondisi baik (tidak ada indikasi defect).")


def main():
    parser = argparse.ArgumentParser(description="Test Card Grader dengan gambar statis")
    parser.add_argument("image_path", nargs="?", help="Path ke file gambar")
    parser.add_argument("--low-thresh", type=float, default=LOW_THRESH)
    parser.add_argument("--high-thresh", type=float, default=HIGH_THRESH)
    args = parser.parse_args()

    image_path = args.image_path
    if not image_path:
        print("=" * 60)
        print("  Image Card Condition Tester")
        print("=" * 60)
        image_path = input("Masukkan path file gambar: ").strip().strip('"').strip("'")

    if not image_path or not os.path.exists(image_path):
        print(f"ERROR: File tidak ditemukan di -> {image_path}")
        sys.exit(1)

    print(f"\n[*] Membaca gambar: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print("ERROR: Tidak dapat membaca gambar. Pastikan format file didukung (JPG, PNG).")
        sys.exit(1)

    cropped_card = get_card_crop(image)
    print("[*] Mengirim ke API dengan confidence=0 (ambil semua raw score)...")

    result = send_frame_to_roboflow(cropped_card)
    if result is None:
        sys.exit(1)

    detections = classify_defect_severity(
        result.get("predictions", []),
        args.low_thresh, args.high_thresh
    )
    print_summary(detections)

    annotated_image = draw_detections(cropped_card, detections)
    filename = Path(image_path).stem
    save_path = _script_dir / f"{filename}_result.jpg"
    cv2.imwrite(str(save_path), annotated_image)
    print(f"\n[+] Gambar hasil deteksi disimpan ke: {save_path}")

    display_img = annotated_image.copy()
    proc_h, proc_w = display_img.shape[:2]
    max_display_height = 800
    if proc_h > max_display_height:
        scale = max_display_height / proc_h
        display_img = cv2.resize(display_img, (int(proc_w * scale), max_display_height))

    print("\n[*] Menampilkan gambar... Tekan sembarang tombol pada jendela gambar untuk keluar.")
    cv2.imshow(f"Hasil Deteksi: {filename}", display_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()