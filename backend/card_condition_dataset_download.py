import os
import shutil
import requests
import zipfile
from io import BytesIO
from dotenv import load_dotenv

# 1. Memuat file .env untuk mengambil API key secara aman
load_dotenv()
API_KEY = os.getenv("ROBOFLOW_API_KEY")

if not API_KEY:
    raise ValueError("API Key belum diset di file .env!")

print("Menghubungkan ke Roboflow Cloud via REST API...")

# 2. Format URL endpoint resmi Roboflow
workspace = "group-6-major-project"
project_name = "card-grader"
version = 4
format_type = "yolov8"

export_url = f"https://api.roboflow.com/{workspace}/{project_name}/{version}/{format_type}?api_key={API_KEY}"

print("Mengunduh dataset citra secara otomatis...")
response = requests.get(export_url)

if response.status_code == 200:
    data = response.json()
    download_url = data.get("export", {}).get("link")
    
    if download_url:
        print("Mengunduh file arsip dataset...")
        zip_response = requests.get(download_url)
        
        # 3. Tentukan folder khusus di dalam backend/dataset/card-condition-dataset/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_folder = os.path.join(current_dir, "dataset/card-condition-dataset")
        
        # Bersihkan folder target jika sebelumnya sudah ada
        if os.path.exists(target_folder):
            shutil.rmtree(target_folder)
        os.makedirs(target_folder, exist_ok=True)
        
        # Ekstrak ZIP langsung ke dalam folder khusus tersebut
        with zipfile.ZipFile(BytesIO(zip_response.content)) as z:
            z.extractall(target_folder)
            
        # 4. Hapus file data.yaml bawaan Roboflow agar folder murni berisi train, val, test
        yaml_in_subfolder = os.path.join(target_folder, "data.yaml")
        if os.path.exists(yaml_in_subfolder):
            os.remove(yaml_in_subfolder)
            
        print(f"Berhasil! Dataset citra tersimpan rapi di: {target_folder}")
    else:
        print("Gagal mendapatkan link download dari respons JSON.")
        print(data)
else:
    print(f"Gagal mengakses API. Status code: {response.status_code}")
    print(response.text)