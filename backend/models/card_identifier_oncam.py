import cv2
import numpy as np
from card_identifier import CardIdentifier  # Sesuaikan dengan nama file engine kamu

def main():
    print("Memuat AI Engine dan Index (Mohon tunggu sebentar)...")
    try:
        identifier = CardIdentifier()
    except Exception as e:
        print(f"Gagal memuat engine: {e}")
        return

    # Inisialisasi Webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Kamera tidak dapat diakses atau sedang digunakan aplikasi lain.")
        return

    print("\n=======================================================")
    print("✅ Kamera menyala!")
    print("👉 Posisikan kartu TEPAT di dalam kotak hijau di layar.")
    print("👉 Tekan 's' pada keyboard untuk SCAN kartu di layar.")
    print("👉 Tekan 'q' pada keyboard untuk KELUAR dari program.")
    print("=======================================================\n")

    # Rasio standar kartu Pokemon (63:88). 
    # Kita buat ukurannya pas untuk resolusi webcam standar.
    CARD_WIDTH = 315
    CARD_HEIGHT = 440

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal mengambil gambar dari kamera.")
            break

        # Ambil resolusi frame kamera saat ini
        h, w, _ = frame.shape

        # Hitung titik tengah untuk menggambar kotak panduan
        x1 = int((w - CARD_WIDTH) / 2)
        y1 = int((h - CARD_HEIGHT) / 2)
        x2 = x1 + CARD_WIDTH
        y2 = y1 + CARD_HEIGHT

        # Lakukan cropping SECARA MANUAL berdasarkan kotak panduan
        # Ini memastikan background ruangan terbuang sempurna
        cropped_frame = frame[y1:y2, x1:x2]

        # --- Visual UI pada jendela utama ---
        display_frame = frame.copy()
        
        # Buat efek gelap di luar kotak agar pengguna fokus ke tengah
        overlay = display_frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, display_frame, 0.5, 0, display_frame)
        
        # Kembalikan warna terang HANYA di dalam kotak
        display_frame[y1:y2, x1:x2] = frame[y1:y2, x1:x2]

        # Gambar kotak hijau sebagai panduan
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Tambahkan teks panduan
        cv2.putText(display_frame, "Posisikan kartu di dalam kotak", (x1 - 10, y1 - 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, "[S] Scan | [Q] Keluar", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Tampilkan frame utama dan frame debug
        cv2.imshow("Pemindai Kartu Pokemon", display_frame)
        cv2.imshow("Debug: Hasil Crop Kartu (Input AI)", cropped_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            print("\nMemindai kartu... 🔍")
            
            # [MODIFIKASI KRUSIAL]
            # Lempar gambar yang SUDAH DI-CROP (cropped_frame) ke engine.
            # Ini akan meningkatkan akurasi secara drastis!
            result = identifier.identify_card(cropped_frame, top_k=1)

            if result['status'] == 'success' and result['candidates']:
                top_match = result['candidates'][0]
                print(f"🎯 Hasil Scan     : {top_match.get('name', 'Unknown')} ({top_match.get('set_name', 'Unknown')})")
                print(f"📊 Confidence     : {top_match['confidence_percentage']}%")
                print(f"⏱️  Waktu Inferensi: {result['execution_time_ms']} ms")
            else:
                print("❌ Kartu tidak dikenali.")

        elif key == ord('q'):
            print("\nMenutup program...")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()