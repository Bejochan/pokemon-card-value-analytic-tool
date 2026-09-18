"""
Image Card Condition Tester
============================
Upload foto tampak depan & belakang kartu. Guide frame/crop otomatis
(deteksi kontur), tidak perlu drag manual.

Cara pakai:
  python image_card_condition_test.py kartu_depan.jpg kartu_belakang.jpg
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
SHARPNESS_THRESHOLD = 70.0

CARD_ASPECT_RATIO = 63.0 / 88.0
CARD_OUT_SIZE = (600, 837)
CROP_MARGIN_RATIO = 0.08


def sharpness_score(gray_frame: np.ndarray) -> float:
    return cv2.Laplacian(gray_frame, cv2.CV_64F).var()


# ── Alignment: porting dari CardIdentifier v2.5/v2.6 (murni OpenCV, tanpa model) ──
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
        return None
    ratio = w / h
    if abs(ratio - CARD_ASPECT_RATIO) / CARD_ASPECT_RATIO < tol:
        return "portrait"
    if abs(ratio - (1.0 / CARD_ASPECT_RATIO)) / (1.0 / CARD_ASPECT_RATIO) < tol:
        return "landscape"
    return None


def _expand_rect(rect, ratio=CROP_MARGIN_RATIO):
    center = rect.mean(axis=0)
    return (center + (rect - center) * (1 + ratio)).astype("float32")


def auto_detect_card(image_np: np.ndarray, out_size=CARD_OUT_SIZE) -> np.ndarray | None:
    h_img, w_img = image_np.shape[:2]
    frame_area = h_img * w_img
    min_area = 0.05 * frame_area
    max_area = 0.92 * frame_area
    border_margin = 2
    max_sides_touch = 3
    solidity_thresh = 0.50
    extent_thresh = 0.80

    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    smooth = cv2.bilateralFilter(gray, d=9, sigmaColor=60, sigmaSpace=60)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_eq = clahe.apply(smooth)
    edges_base = cv2.Canny(gray_eq, 40, 120)

    best = None  # (area, rect, orientation)

    for ksize, iters in [(5, 2), (7, 2), (9, 3), (11, 3), (13, 4)]:
        kernel = np.ones((ksize, ksize), np.uint8)
        edges = cv2.morphologyEx(edges_base, cv2.MORPH_CLOSE, kernel, iterations=iters)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            sides_touched = sum([
                x <= border_margin, y <= border_margin,
                x + w >= w_img - border_margin, y + h >= h_img - border_margin
            ])
            if sides_touched > max_sides_touch:
                continue
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            if solidity < solidity_thresh:
                continue
            candidates.append((area, c))

        if not candidates:
            continue
        candidates.sort(key=lambda t: t[0], reverse=True)

        for area, c in candidates[:5]:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            rect = None
            if len(approx) == 4 and cv2.isContourConvex(approx):
                rect = _order_points(approx)
            else:
                hull = cv2.convexHull(c)
                hull_peri = cv2.arcLength(hull, True)
                for eps_factor in (0.02, 0.03, 0.05):
                    hull_approx = cv2.approxPolyDP(hull, eps_factor * hull_peri, True)
                    if len(hull_approx) == 4 and cv2.isContourConvex(hull_approx):
                        rect = _order_points(hull_approx)
                        break

            if rect is None:
                min_rect = cv2.minAreaRect(c)
                (rw, rh) = min_rect[1]
                rect_area = rw * rh
                extent = (area / rect_area) if rect_area > 0 else 0
                if extent < extent_thresh:
                    continue
                box = cv2.boxPoints(min_rect)
                rect = _order_points(box)

            orientation = _aspect_ok(rect)
            if orientation is None:
                continue

            if best is None or area > best[0]:
                best = (area, rect, orientation)

    if best is None:
        return None

    _, rect, orientation = best
    rect = _expand_rect(rect)
    width, height = out_size

    if orientation == "landscape":
        dst = np.array([[0, 0], [height - 1, 0], [height - 1, width - 1], [0, width - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image_np, M, (height, width), flags=cv2.INTER_CUBIC)

        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
        return warped

    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image_np, M, (width, height), flags=cv2.INTER_CUBIC)


def send_frame_to_roboflow(image: np.ndarray) -> dict | None:
    try:
        success, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not success:
            print("[!] ERROR: Gagal melakukan encode gambar ke JPEG.")
            return None
        image_data = base64.b64encode(buffer.tobytes()).decode("utf-8")
        response = requests.post(
            API_URL, data=image_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[!] Request gagal: {e}")
        return None


def classify_defect_severity(predictions: list[dict],
                              low_thresh=LOW_THRESH, high_thresh=HIGH_THRESH) -> list[dict]:
    results = []
    for pred in predictions:
        if pred.get("class") == "Card":
            continue
        conf = float(pred.get("confidence", 0.0))
        if conf < low_thresh:
            continue
        certainty = "Terindikasi (perlu verifikasi ulang)" if conf < high_thresh else "Terdeteksi"
        results.append({
            "class": pred["class"], "confidence": conf, "certainty": certainty,
            "x": pred.get("x"), "y": pred.get("y"),
            "width": pred.get("width"), "height": pred.get("height"),
        })
    return results


def draw_detections(frame: np.ndarray, detections: list[dict]) -> np.ndarray:
    overlay = frame.copy()
    height, width = overlay.shape[:2]
    scale_factor = max(width, height) / 1000.0
    line_thick = max(2, int(2 * scale_factor))
    font_scale = max(0.6, 0.6 * scale_factor)

    for det in detections:
        label, confidence, certainty = det["class"], det["confidence"], det["certainty"]
        cx, cy = int(det["x"]), int(det["y"])
        w, h = int(det["width"]), int(det["height"])
        x1, y1, x2, y2 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2

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


def print_side_summary(side_label: str, detections: list[dict]):
    print(f"\n[+] {side_label} — {len(detections)} defect terklasifikasi\n")
    print("    -----------------------------------")
    for cls in ["Corner Wear", "Edge Wear", "Scratch"]:
        matches = [d for d in detections if d["class"] == cls]
        if matches:
            best = max(matches, key=lambda d: d["confidence"])
            print(f"    {cls:<12s} : {best['confidence']:.1%}  [{best['certainty']}]")
        else:
            print(f"    {cls:<12s} : tidak terdeteksi")
    print("    -----------------------------------")


def process_side(image_path: str, side_label: str,
                  low_thresh: float, high_thresh: float) -> list[dict] | None:
    print(f"\n[*] Membaca gambar {side_label}: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print("ERROR: Tidak dapat membaca gambar. Pastikan format file didukung (JPG, PNG).")
        return None

    cropped_card = auto_detect_card(image)
    if cropped_card is None:
        print(f"[!] Deteksi kartu otomatis gagal untuk {side_label}. Coba foto dengan background lebih kontras/rata.")
        return None

    gray = cv2.cvtColor(cropped_card, cv2.COLOR_BGR2GRAY)
    score = sharpness_score(gray)
    print(f"[*] Skor ketajaman: {score:.1f} (ambang: {SHARPNESS_THRESHOLD:.0f})")
    if score < SHARPNESS_THRESHOLD:
        print(f"[!] Gambar {side_label} terlalu blur, hasil defect detection mungkin tidak akurat.")

    print(f"[*] Mengirim {side_label} ke API...")
    result = send_frame_to_roboflow(cropped_card)
    if result is None:
        return None

    detections = classify_defect_severity(result.get("predictions", []), low_thresh, high_thresh)
    print_side_summary(side_label, detections)

    annotated = draw_detections(cropped_card, detections)
    filename = Path(image_path).stem
    save_path = _script_dir / f"{filename}_result.jpg"
    cv2.imwrite(str(save_path), annotated)
    print(f"[+] Gambar hasil deteksi disimpan ke: {save_path}")

    return detections


def print_combined_conclusion(front_detections: list[dict] | None, back_detections: list[dict] | None):
    all_detections = (front_detections or []) + (back_detections or [])
    solid = [d for d in all_detections if d["certainty"] == "Terdeteksi"]
    indicated = [d for d in all_detections if d["certainty"] != "Terdeteksi"]

    print("\n" + "=" * 40)
    print("KESIMPULAN GABUNGAN (DEPAN + BELAKANG)")
    print("=" * 40)
    if solid:
        print(f"[!] {len(solid)} defect terkonfirmasi solid:")
        for d in solid:
            print(f"    - {d['class']} ({d['confidence']:.1%})")
    if indicated:
        print(f"[?] {len(indicated)} defect di zona abu-abu:")
        for d in indicated:
            print(f"    - {d['class']} ({d['confidence']:.1%})")
    if not solid and not indicated:
        print("[✓] Kartu dalam kondisi baik (tidak ada indikasi defect di kedua sisi).")


def main():
    parser = argparse.ArgumentParser(description="Test Card Grader dengan foto depan & belakang")
    parser.add_argument("front_path", nargs="?", help="Path ke foto tampak depan")
    parser.add_argument("back_path", nargs="?", help="Path ke foto tampak belakang")
    parser.add_argument("--low-thresh", type=float, default=LOW_THRESH)
    parser.add_argument("--high-thresh", type=float, default=HIGH_THRESH)
    args = parser.parse_args()

    front_path, back_path = args.front_path, args.back_path
    if not front_path or not back_path:
        print("=" * 60)
        print("  Image Card Condition Tester (Depan & Belakang)")
        print("=" * 60)
        front_path = input("Masukkan path foto tampak depan: ").strip().strip('"').strip("'")
        back_path = input("Masukkan path foto tampak belakang: ").strip().strip('"').strip("'")

    for label, p in [("depan", front_path), ("belakang", back_path)]:
        if not p or not os.path.exists(p):
            print(f"ERROR: File {label} tidak ditemukan di -> {p}")
            sys.exit(1)

    front_detections = process_side(front_path, "TAMPAK DEPAN", args.low_thresh, args.high_thresh)
    back_detections = process_side(back_path, "TAMPAK BELAKANG", args.low_thresh, args.high_thresh)

    print_combined_conclusion(front_detections, back_detections)


if __name__ == "__main__":
    main()