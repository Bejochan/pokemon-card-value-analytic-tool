import os
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 1. Menentukan path direktori secara dinamis
current_dir = os.path.dirname(os.path.abspath(__file__))
input_dir = os.path.join(current_dir, "dataset", "raw_images")
output_dir = os.path.join(current_dir, "dataset", "compressed_images")

os.makedirs(output_dir, exist_ok=True)

if not os.path.exists(input_dir):
    raise FileNotFoundError(f"Folder gambar mentah tidak ditemukan di: {input_dir}")

# Mendapatkan daftar file gambar PNG
image_files = [f for f in os.listdir(input_dir) if f.endswith('.png')]
total_images = len(image_files)

print(f"Total gambar ditemukan untuk dikompres ke JPG: {total_images}")
print(f"Target folder penyimpanan: {output_dir}")

# 2. Fungsi untuk mengompres dan mengubah format ke JPG (640x640, quality=85)
def compress_single_image(filename):
    input_path = os.path.join(input_dir, filename)
    # Mengubah ekstensi target dari .png menjadi .jpg
    jpg_filename = filename.replace('.png', '.jpg')
    output_path = os.path.join(output_dir, jpg_filename)
    
    # Jika file JPG hasil kompresi sudah pernah ada, lewati
    if os.path.exists(output_path):
        return "skipped"
    
    try:
        with Image.open(input_path) as img:
            # Konversi ke RGB (format JPEG tidak mendukung transparansi RGBA/Palette)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Melakukan resize ke 640x640 piksel menggunakan LANCZOS
            img = img.resize((640, 640), Image.Resampling.LANCZOS)
            
            # Simpan dalam format JPEG dengan kualitas 85 dan optimasi aktif
            img.save(output_path, "JPEG", quality=85, optimize=True)
        return "success"
    except Exception:
        return "failed"

# 3. Menjalankan proses multithreading agar kompresi berjalan sangat cepat
success_count = 0
skipped_count = 0
failed_count = 0
max_workers = 16  # Memanfaatkan multi-core CPU secara paralel

print("Memulai proses kompresi, resizing, dan konversi ke JPG...")
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(compress_single_image, filename): filename for filename in image_files}
    
    with tqdm(total=total_images, desc="Compressing to JPG", unit="img") as pbar:
        for future in as_completed(futures):
            result = future.result()
            if result == "success":
                success_count += 1
            elif result == "skipped":
                skipped_count += 1
            else:
                failed_count += 1
            pbar.update(1)

print("\n--- RINGKASAN KOMPRESI JPG ---")
print(f"Berhasil dikompres : {success_count} gambar")
print(f"Sudah ada (Lewat)  : {skipped_count} gambar")
print(f"Gagal dikompres    : {failed_count} gambar")
print(f"Hasil tersimpan di : {output_dir}")