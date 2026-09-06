import os
import requests
from dotenv import load_dotenv

# 1. Memuat variabel lingkungan dari file .env terdekat
load_dotenv()

# 2. Mengambil API Key dengan aman
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

if not ROBOFLOW_API_KEY:
    raise ValueError("ERROR: ROBOFLOW_API_KEY tidak ditemukan! Pastikan sudah diset di file .env")

# 3. Membuat fungsi agar mudah dipanggil oleh file/aplikasi lain
def detect_card_defects(image_path):
    """
    Fungsi untuk mendeteksi cacat fisik pada kartu menembak API Roboflow secara langsung via HTTP.
    Tidak memerlukan inference-sdk sehingga aman dari bentrok dependensi.
    """
    try:
        # Membaca file gambar menjadi bentuk binary
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()

        # URL Endpoint API Roboflow
        # Ganti "card-grader/4" jika kamu menggunakan versi model yang lain
        api_url = f"https://detect.roboflow.com/card-grader/4?api_key={ROBOFLOW_API_KEY}"

        # Mengirim POST request membawa data gambar
        response = requests.post(
            api_url,
            data=image_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Mengembalikan hasil berupa JSON (dictionary)
        return response.json()
    
    except Exception as e:
        print(f"Gagal memproses gambar: {e}")
        return None

# ==========================================
# Bagian ini hanya untuk testing lokal
# ==========================================
if __name__ == "__main__":
    # Ganti string di bawah dengan path gambar contoh milikmu
    test_image = "../dataset/test_gambar.jpg" 
    
    if os.path.exists(test_image):
        print(f"Menganalisis gambar: {test_image}...\n")
        hasil_deteksi = detect_card_defects(test_image)
        
        # Menampilkan hasil deteksi koordinat
        print(hasil_deteksi)
    else:
        print(f"Gambar {test_image} tidak ditemukan untuk di-test.")