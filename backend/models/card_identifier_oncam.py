import cv2
import numpy as np
from card_identifier import CardIdentifier

# Ambang batas ketajaman (variance of Laplacian). Nilai wajar untuk webcam biasa
# ada di kisaran 60-150 tergantung resolusi & lensa -- kalibrasi ulang sesuai
# kamera Anda kalau terlalu sering "kurang tajam" padahal fotonya sudah jelas.
SHARPNESS_THRESHOLD = 80.0
BURST_FRAMES = 5

USE_TTA = False
DEBUG_MODE = True
DEBUG_TOP_K = 5

LABEL_COLOR = {
    "Tinggi": (0, 200, 0),      # hijau (BGR)
    "Sedang": (0, 200, 255),    # kuning
    "Rendah": (0, 0, 255),      # merah
}


def sharpness_score(gray_frame):
    """Variance of Laplacian -- makin tinggi, makin tajam (tidak blur)."""
    return cv2.Laplacian(gray_frame, cv2.CV_64F).var()

def capture_best_of_burst(cap, x1, y1, x2, y2, n_frames=BURST_FRAMES):
    """Ambil beberapa frame berturut-turut, kembalikan crop yang paling tajam."""
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


def main():
    print("Memuat AI Engine dan Index (Mohon tunggu sebentar)...")
    try:
        identifier = CardIdentifier(use_tta=USE_TTA)
        print(f"[debug] use_tta={USE_TTA}  confidence_temperature={identifier.confidence_temperature}")
    except Exception as e:
        print(f"Gagal memuat engine: {e}")
        return

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Kamera tidak dapat diakses atau sedang digunakan aplikasi lain.")
        return

    print("\n=======================================================")
    print("Kamera menyala!")
    print("Posisikan kartu TEPAT di dalam kotak hijau di layar.")
    print("Tekan 's' pada keyboard untuk SCAN kartu di layar.")
    print("Tekan 'q' pada keyboard untuk KELUAR dari program.")
    print("=======================================================\n")

    CARD_WIDTH = 315
    CARD_HEIGHT = 440

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

        display_frame = frame.copy()
        overlay = display_frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, display_frame, 0.5, 0, display_frame)
        display_frame[y1:y2, x1:x2] = frame[y1:y2, x1:x2]

        guide_color = (0, 255, 0) if is_sharp_enough else (0, 165, 255)
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), guide_color, 2)

        guide_text = "Posisikan kartu di dalam kotak" if is_sharp_enough else "Gambar kurang tajam - dekatkan/stabilkan"
        cv2.putText(display_frame, guide_text, (x1 - 10, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, guide_color, 2)
        cv2.putText(display_frame, "[S] Scan | [Q] Keluar", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(display_frame, f"Ketajaman: {live_sharpness:.0f}", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, guide_color, 1)

        if last_result_text:
            cv2.putText(display_frame, last_result_text, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, last_result_color, 2)

        cv2.imshow("Pemindai Kartu Pokemon", display_frame)
        cv2.imshow("Debug: Hasil Crop Kartu (Input AI)", cropped_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            print("\nMengambil beberapa frame untuk memilih yang paling tajam...")
            best_crop, best_score = capture_best_of_burst(cap, x1, y1, x2, y2)

            if best_crop is None or best_score < SHARPNESS_THRESHOLD * 0.6:
                print("Gambar terlalu blur untuk dipindai. Stabilkan kamera & coba lagi.")
                last_result_text = "Terlalu blur, coba lagi"
                last_result_color = (0, 0, 255)
                continue

            print(f"Memindai kartu (ketajaman terbaik: {best_score:.0f})... 🔍")
            result = identifier.identify_card(best_crop, top_k=DEBUG_TOP_K, debug=DEBUG_MODE)

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
                    print(f"[debug] {DEBUG_TOP_K} kandidat teratas (nama - raw_sim - confidence):")
                    for c in result['candidates']:
                        print(f"         #{c['rank']} {c.get('name','?'):20s} raw={c['raw_similarity_score']:.4f}  conf={c['confidence_percentage']}%")
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