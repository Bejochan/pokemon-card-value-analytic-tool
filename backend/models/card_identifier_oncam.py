import cv2
from card_identifier import CardIdentifier  # Sesuaikan dengan nama file engine kamu

def main():
    print("Memuat AI Engine dan Index (Mohon tunggu sebentar)...")
    try:
        identifier = CardIdentifier()
    except Exception as e:
        print(f"Gagal memuat engine: {e}")
        return

    # Inisialisasi Webcam (0 adalah ID default untuk kamera laptop)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Kamera tidak dapat diakses atau sedang digunakan aplikasi lain.")
        return

    print("\n=======================================================")
    print("✅ Kamera menyala!")
    print("👉 Tekan 's' pada keyboard untuk SCAN kartu di layar.")
    print("👉 Tekan 'q' pada keyboard untuk KELUAR dari program.")
    print("=======================================================\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal mengambil gambar dari kamera.")
            break

        # Tampilkan panduan visual di layar kamera
        cv2.putText(frame, "Tekan 'S' untuk Scan | 'Q' untuk Keluar", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Tampilkan frame
        cv2.imshow("Pemindai Kartu Pokemon", frame)

        # Deteksi tombol keyboard (delay 1 ms)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('s'):
            print("\nMemindai kartu... 🔍")
            # Oper frame NumPy Array langsung ke engine
            result = identifier.identify_card(frame, top_k=1)
            
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

    # Bersihkan memori kamera dan tutup jendela
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()