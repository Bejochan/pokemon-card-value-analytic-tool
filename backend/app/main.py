from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import cv2
import numpy as np
import json
import os

from models.card_identifier import CardIdentifier

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 1. FASE PEMANASAN DATABASE JSON
# ---------------------------------------------------------
print("Memuat dataset JSON...")
json_path = os.path.join(os.path.dirname(__file__), "../dataset/pokemon_cards_dataset_cleaned.json")
try:
    with open(json_path, "r", encoding="utf-8") as f:
        pokemon_db = json.load(f)
    print(f"SUKSES: {len(pokemon_db)} data kartu berhasil dimuat ke memori!")
except FileNotFoundError:
    print(f"ERROR: File JSON tidak ditemukan di {json_path}")
    pokemon_db = []

# ---------------------------------------------------------
# 2. FASE INISIALISASI AI (Ini yang tadi terhapus)
# ---------------------------------------------------------
print("Menghidupkan Mesin AI Pokemai...")
ai_engine = CardIdentifier(use_orb_rerank=False)
print("Mesin AI siap digunakan!")

# ---------------------------------------------------------
# 3. FORMAT DATA DARI REACT
# ---------------------------------------------------------
class ImageData(BaseModel):
    image: str 

# ---------------------------------------------------------
# 4. FASE PENERIMAAN REQUEST DARI WEB
# ---------------------------------------------------------
@app.post("/analyze")
async def analyze_card(data: ImageData):
    try:
        print("Menerima foto dari web...")

        # 1. Membersihkan teks Base64
        image_b64 = data.image.split(",")[1] if "," in data.image else data.image
        img_bytes = base64.b64decode(image_b64)
        img_arr = np.frombuffer(img_bytes, np.uint8)
        
        # 2. Biarkan dalam format BGR (OpenCV bawaan)
        img_cv2_bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

        # 3. Masukkan langsung ke AI (AI akan mengubahnya ke RGB secara internal)
        ai_result = ai_engine.identify_card(
            image_input=img_cv2_bgr, 
            top_k=1, 
            debug=True, 
            debug_save_path="debug_gambar_dari_web.jpg"
        )
        
        if ai_result["status"] == "success" and ai_result["top_match"]:
            kartu_tebakan_ai = ai_result["top_match"]
            ai_detected_id = kartu_tebakan_ai.get("id")
            
            # Cari di JSON
            found_card = next((card for card in pokemon_db if card.get("id") == ai_detected_id), None)
            
            if found_card:
                nama_kartu = found_card.get("name", "Tidak Diketahui")
                official_image = found_card.get("images", {}).get("large", "") 
                
                # Ambil Harga
                price_usd = found_card.get("tcgplayer", {}).get("prices", {}).get("normal", {}).get("market", 0)
                if price_usd == 0:
                    price_usd = kartu_tebakan_ai.get("effective_market_price", 0)
                price_idr = int(price_usd * 15500) 
                
                return {
                    "status": "success",
                    "message": f"Berhasil mendeteksi: {nama_kartu}",
                    "estimated_price": price_idr,
                    "card_condition": "Menunggu Deteksi Kondisi", 
                    "official_image_url": official_image 
                }
            else:
                return {"status": "error", "message": "Data tidak ada di JSON lokal."}
        else:
            return {"status": "error", "message": "AI gagal mengenali kartu."}

    except Exception as e:
        print(f"Error pada server: {e}")
        return {"status": "error", "message": str(e)}