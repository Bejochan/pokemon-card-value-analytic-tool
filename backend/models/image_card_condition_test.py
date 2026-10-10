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
from collections import defaultdict

import cv2
import numpy as np
from dotenv import load_dotenv
from pathlib import Path
from ultralytics import YOLO

# Mendapatkan rute folder 'models' tempat script ini berada
_script_dir = Path(__file__).resolve().parent

# === KONFIGURASI MODEL LOKAL ===
# Sementara langsung pakai path absolut
local_model_path = r"best-model-v5-card-condition.pt"

print(f"[*] Memuat model YOLO dari: {local_model_path}")
try:
    if not os.path.exists(local_model_path):
        print(f"[!] File model tidak ditemukan di path: {local_model_path}")
        sys.exit(1)
        
    defect_model = YOLO(local_model_path)
except Exception as e:
    print(f"[!] Gagal memuat model YOLO. Error: {e}")
    sys.exit(1)

CLASS_COLORS = {
    "Card":        (0, 255, 0),
    "Corner Wear": (0, 0, 255),
    "Edge Wear":   (0, 165, 255),
    "Scratch":     (255, 0, 255),
}
DEFAULT_COLOR = (255, 255, 0)

LOW_THRESH = 0.20   
HIGH_THRESH = 0.55
SHARPNESS_THRESHOLD = 70.0

CARD_ASPECT_RATIO = 63.0 / 88.0
CARD_OUT_SIZE = (600, 837)  # Ukuran kartu asli (belum termasuk margin)

def nms(detections: list[dict], iou_threshold: float = 0.4) -> list[dict]:
    if not detections:
        return []

    def iou(a, b):
        ax1, ay1 = a["x"] - a["width"]/2,  a["y"] - a["height"]/2
        ax2, ay2 = a["x"] + a["width"]/2,  a["y"] + a["height"]/2
        bx1, by1 = b["x"] - b["width"]/2,  b["y"] - b["height"]/2
        bx2, by2 = b["x"] + b["width"]/2,  b["y"] + b["height"]/2
        inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
        inter_h = max(0, min(ay2, by2) - max(ay1, by1))
        inter   = inter_w * inter_h
        union   = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter
        return inter / union if union > 0 else 0

    # Kelompokkan per class, lalu NMS per class
    by_class = defaultdict(list)
    for d in detections:
        by_class[d["class"]].append(d)

    kept = []
    for cls_dets in by_class.values():
        cls_dets.sort(key=lambda d: d["confidence"], reverse=True)
        suppressed = set()
        for i, a in enumerate(cls_dets):
            if i in suppressed:
                continue
            kept.append(a)
            for j, b in enumerate(cls_dets[i+1:], i+1):
                if iou(a, b) > iou_threshold:
                    suppressed.add(j)
    return kept

def filter_edge_detections(detections: list[dict], img_w: int, img_h: int,
                            border_ratio: float = 0.25) -> list[dict]:
    """Buang deteksi Edge Wear / Corner Wear yang posisinya jauh dari tepi kartu."""
    result = []
    for d in detections:
        if d["class"] in ["Scratch", "Card"]:
            result.append(d)  # Scratch dan Card tidak difilter lokasinya
            continue
        
        cx, cy = d["x"], d["y"]
        near_edge = (
            cx < img_w * border_ratio or
            cx > img_w * (1 - border_ratio) or
            cy < img_h * border_ratio or
            cy > img_h * (1 - border_ratio)
        )
        if near_edge:
            result.append(d)
    return result

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


def auto_detect_card(image_np: np.ndarray, out_size=CARD_OUT_SIZE) -> np.ndarray | None:
    h_img, w_img = image_np.shape[:2]
    frame_area = h_img * w_img
    min_area = 0.05 * frame_area
    max_area = 0.92 * frame_area
    border_margin = 2
    max_sides_touch = 3
    solidity_thresh = 0.40
    extent_thresh = 0.75

    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

    # Otsu-based segmentation
    # Blur sangat agresif untuk mematikan total tekstur bg
    blurred = cv2.GaussianBlur(gray, (51, 51), 0)
    # Otsu otomatis cari threshold optimal antara kartu vs bg
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Morphology untuk tutup gap dan buang noise kecil
    kernel_close = np.ones((25, 25), np.uint8)
    kernel_open  = np.ones((15, 15), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close, iterations=3)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel_open,  iterations=2)

    # Pakai binary mask sebagai sumber kontur, bukan edges
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None

    if not contours:
        return None

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
        return None

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
            for eps_factor in (0.02, 0.03, 0.05, 0.08):
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
    width, height = out_size
    margin = 120  # Margin 120 piksel agar background terlihat sangat luas dan tidak mepet

    out_w = width + 2 * margin
    out_h = height + 2 * margin

    if orientation == "landscape":
        dst = np.array([
            [margin, margin], 
            [margin + height - 1, margin], 
            [margin + height - 1, margin + width - 1], 
            [margin, margin + width - 1]
        ], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image_np, M, (out_h, out_w), flags=cv2.INTER_CUBIC)
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
        return warped

    dst = np.array([
        [margin, margin], 
        [margin + width - 1, margin], 
        [margin + width - 1, margin + height - 1], 
        [margin, margin + height - 1]
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image_np, M, (out_w, out_h), flags=cv2.INTER_CUBIC)


def get_yolo_predictions(image: np.ndarray) -> dict | None:
    """Menggunakan model YOLO lokal (didownload dari HF) untuk menggantikan Roboflow API."""
    try:
        # Gunakan conf=0.01 agar filter manual (LOW_THRESH/HIGH_THRESH) di script ini tetap berfungsi sama
        results = defect_model.predict(image, conf=0.01, verbose=False)
        result = results[0]
        
        predictions = []
        for box in result.boxes:
            cx, cy, w, h = box.xywh[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = result.names[cls_id]
            
            predictions.append({
                "class": cls_name,
                "confidence": conf,
                "x": cx,
                "y": cy,
                "width": w,
                "height": h
            })
        return {"predictions": predictions}
    except Exception as e:
        print(f"[!] YOLO prediction error: {e}")
        return None


def classify_defect_severity(predictions: list[dict],
                              low_thresh=LOW_THRESH, high_thresh=HIGH_THRESH) -> list[dict]:
    results = []
    for pred in predictions:
        if pred.get("class") == "Card":
            # Card tidak disaring ketat seperti defect
            results.append({
                "class": pred["class"], "confidence": float(pred.get("confidence", 0)), 
                "certainty": "Terdeteksi", "x": pred.get("x"), "y": pred.get("y"),
                "width": pred.get("width"), "height": pred.get("height")
            })
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

    # Logika ala Kaggle: Cari 1 Card dengan confidence tertinggi
    cards = [d for d in detections if d["class"] == "Card"]
    best_card = max(cards, key=lambda c: c["confidence"]) if cards else None

    for det in detections:
        label, confidence, certainty = det["class"], det["confidence"], det["certainty"]
        
        # Sembunyikan duplikat kotak Card agar UI bersih (hanya gambar 1 yang terbaik)
        if label == "Card" and det != best_card:
            continue

        cx, cy = int(det["x"]), int(det["y"])
        w, h = int(det["width"]), int(det["height"])
        x1, y1, x2, y2 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2

        color = CLASS_COLORS.get(label, DEFAULT_COLOR)
        thickness = line_thick if certainty == "Terdeteksi" else max(1, line_thick - 1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)

        tag = "[V]" if certainty == "Terdeteksi" else "[?]"
        text = f"{label} {confidence:.1%} {tag}"
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thick)
        
        # Smart label placement: Jika label menabrak margin atas, gambar di sebelah dalam/bawah garis
        text_y = y1 - 10
        if text_y - th < 0:
            text_y = y1 + th + 10
            
        cv2.rectangle(overlay, (x1, text_y - th - baseline), (x1 + tw + 10, text_y + baseline), color, -1)
        cv2.putText(overlay, text, (x1 + 5, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), line_thick)
    return overlay


def print_side_summary(side_label: str, detections: list[dict]):
    # Jangan hitung kelas 'Card' sebagai defect
    defects = [d for d in detections if d["class"] != "Card"]
    print(f"\n[+] {side_label} — {len(defects)} defect terklasifikasi\n")
    print("    -----------------------------------")
    for cls in ["Corner Wear", "Edge Wear", "Scratch"]:
        matches = [d for d in defects if d["class"] == cls]
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
        debug_path = _script_dir / f"debug_{side_label.replace(' ', '_')}.jpg"
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        smooth = cv2.bilateralFilter(gray, 9, 60, 60)
        clahe = cv2.createCLAHE(2.0, (8, 8))
        edges = cv2.Canny(clahe.apply(smooth), 40, 120)
        cv2.imwrite(str(debug_path), edges)
        print(f"[DEBUG] Edge map disimpan ke: {debug_path} — cek apakah outline kartu terlihat")
        
        print(f"[!] Deteksi kartu otomatis gagal...")
        return None

    gray = cv2.cvtColor(cropped_card, cv2.COLOR_BGR2GRAY)
    score = sharpness_score(gray)
    print(f"[*] Skor ketajaman: {score:.1f} (ambang: {SHARPNESS_THRESHOLD:.0f})")
    if score < SHARPNESS_THRESHOLD:
        print(f"[!] Gambar {side_label} agak blur — menerapkan preprocessing tambahan...")

    # Terapkan CLAHE untuk meningkatkan kontras sebelum dikirim ke API
    lab = cv2.cvtColor(cropped_card, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = cv2.merge((clahe.apply(l), a, b))
    send_image = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    print(f"[*] Menganalisis {side_label} dengan Model YOLO lokal...")
    result = get_yolo_predictions(send_image)
    if result is None:
        return None

    # ── Filter & deduplikasi ──
    raw_preds = result.get("predictions", [])
    detections = classify_defect_severity(raw_preds, low_thresh, high_thresh)
    detections = nms(detections)
    h, w = cropped_card.shape[:2]
    detections = filter_edge_detections(detections, w, h, border_ratio=0.25)
    print_side_summary(side_label, detections)

    annotated = draw_detections(cropped_card, detections)
    filename = Path(image_path).stem
    save_path = _script_dir / f"{filename}_result.jpg"
    cv2.imwrite(str(save_path), annotated)
    print(f"[+] Gambar hasil deteksi disimpan ke: {save_path}")

    return detections


def print_combined_conclusion(front_detections: list[dict] | None, back_detections: list[dict] | None):
    print("\n" + "=" * 40)
    print("KESIMPULAN GABUNGAN (DEPAN + BELAKANG)")
    print("=" * 40)

    # ← Tambahkan ini
    if front_detections is None and back_detections is None:
        print("[✗] Kedua sisi GAGAL dianalisis — kartu tidak terdeteksi.")
        print("    Coba foto ulang dengan background kontras & pencahayaan merata.")
        return

    if front_detections is None:
        print("[!] PERINGATAN: Sisi DEPAN gagal dianalisis, kesimpulan hanya dari sisi belakang.")
    if back_detections is None:
        print("[!] PERINGATAN: Sisi BELAKANG gagal dianalisis, kesimpulan hanya dari sisi depan.")

    all_detections = (front_detections or []) + (back_detections or [])
    
    # Abaikan kelas 'Card', kita hanya ingin merekap defect yang sebenarnya
    defects_only = [d for d in all_detections if d["class"] != "Card"]

    solid = [d for d in defects_only if d["certainty"] == "Terdeteksi"]
    indicated = [d for d in defects_only if d["certainty"] != "Terdeteksi"]

    if solid:
        print(f"[!] {len(solid)} defect terkonfirmasi solid:")
        for d in solid:
            print(f"    - {d['class']} ({d['confidence']:.1%})")
    if indicated:
        print(f"[?] {len(indicated)} defect di zona abu-abu (perlu cek visual):")
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

    # === MENAMPILKAN UI WINDOW SECARA OTOMATIS ===
    front_save_path = str(_script_dir / f"{Path(front_path).stem}_result.jpg")
    back_save_path = str(_script_dir / f"{Path(back_path).stem}_result.jpg")

    img_front = cv2.imread(front_save_path)
    img_back = cv2.imread(back_save_path)

    if img_front is not None and img_back is not None:
        # Samakan tingginya sebelum digabung
        h1, w1 = img_front.shape[:2]
        h2, w2 = img_back.shape[:2]
        target_h = max(h1, h2)
        
        img_f = cv2.resize(img_front, (int(w1 * target_h / h1), target_h))
        img_b = cv2.resize(img_back, (int(w2 * target_h / h2), target_h))
        
        # Buat pemisah vertikal hitam selebar 20 piksel
        divider = np.zeros((target_h, 20, 3), dtype=np.uint8)
        combined = np.hstack((img_f, divider, img_b))
        
        # Buat area header hitam di bagian atas setinggi 80 piksel
        header_h = 80
        header = np.zeros((header_h, combined.shape[1], 3), dtype=np.uint8)
        
        # Susun UI akhir
        final_ui = np.vstack((header, combined))
        
        def put_centered_text(img, text, center_x, center_y):
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
            cv2.putText(img, text, (center_x - tw // 2, center_y + th // 2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            
        # Tulis label di tengah-tengah bagian gambar masing-masing
        put_centered_text(final_ui, "TAMPAK DEPAN", img_f.shape[1] // 2, header_h // 2)
        put_centered_text(final_ui, "TAMPAK BELAKANG", img_f.shape[1] + 20 + img_b.shape[1] // 2, header_h // 2)

        print("\n[*] Menampilkan UI Window... (Tekan sembarang tombol keyboard atau klik 'X' untuk menutup)")
        cv2.namedWindow("Hasil Deteksi Kartu", cv2.WINDOW_NORMAL)
        cv2.imshow("Hasil Deteksi Kartu", final_ui)
        
        # Loop canggih agar window tidak freeze saat diklik silang (X) atau lewat keyboard
        while cv2.getWindowProperty("Hasil Deteksi Kartu", cv2.WND_PROP_VISIBLE) >= 1:
            key = cv2.waitKey(100) & 0xFF
            if key != 255:  # Artinya ada tombol keyboard yang ditekan
                break
                
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()