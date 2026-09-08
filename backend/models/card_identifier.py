"""
=============================================================================
Pokemon Card Value Analytic Tool — Model 1: Card Identifier Engine
=============================================================================
Engine pencocokan visual kartu Pokémon secara instan (< 5 ms) menggunakan
FAISS Vector Search & PyTorch MobileNetV3 Deep Feature Embedding.

Fungsi Utama:
- Pre-processing & Perspective Transform (Meluruskan foto dari kamera HP)
- Feature Extraction & L2 Normalized Vector Search
- Joining Metadata dari pokemon_cards_dataset_cleaned.csv
=============================================================================
"""

import os
import json
import time
import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import faiss

# Configuration Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(MODEL_DIR, "card_embeddings.index")
MAP_PATH = os.path.join(MODEL_DIR, "card_id_map.json")
CSV_PATH = os.path.join(BASE_DIR, "dataset", "pokemon_cards_dataset_cleaned.csv")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class CardIdentifier:
    """
    Engine Inferensi Model 1 untuk Pengenal Jenis Kartu Pokémon.
    """
    
    def __init__(self, index_path=INDEX_PATH, map_path=MAP_PATH, csv_path=CSV_PATH):
        self.index_path = index_path
        self.map_path = map_path
        self.csv_path = csv_path
        
        self.index = None
        self.card_id_map = {}
        self.df_metadata = None
        self.feature_extractor = None
        self.transform = None
        
        self._load_resources()

    def _load_resources(self):
        """Memuat berkas indeks, pemetaan, metadata CSV, dan Neural Network Model."""
        # 1. Memuat FAISS Index & Map
        if not os.path.exists(self.index_path) or not os.path.exists(self.map_path):
            raise FileNotFoundError(
                f"Berkas model FAISS belum dibuat! Silakan jalankan `python backend/models/build_card_index.py` terlebih dahulu."
            )
            
        self.index = faiss.read_index(self.index_path)
        with open(self.map_path, "r", encoding="utf-8") as f:
            self.card_id_map = json.load(f)
            
        # 2. Memuat Metadata CSV
        if os.path.exists(self.csv_path):
            self.df_metadata = pd.read_csv(self.csv_path).set_index("card_id", drop=False)
            
        # 3. Memuat Model PyTorch Feature Extractor
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        backbone = models.mobilenet_v3_small(weights=weights)
        self.feature_extractor = nn.Sequential(*list(backbone.children())[:-1], nn.Flatten())
        self.feature_extractor.to(DEVICE)
        self.feature_extractor.eval()
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def align_card_image(self, image_np):
        """
        Gunakan OpenCV Contour Detection & Perspective Transform untuk meluruskan
        foto kartu miring dari kamera HP ke rasio standar 63:88.
        """
        try:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 50, 150)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return image_np
                
            # Cari kontur terbesar (asumsi objek kartu)
            largest = max(contours, key=cv2.contourArea)
            peri = cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
            
            if len(approx) == 4:
                # Ordering points: top-left, top-right, bottom-right, bottom-left
                pts = approx.reshape(4, 2)
                rect = np.zeros((4, 2), dtype="float32")
                s = pts.sum(axis=1)
                rect[0] = pts[np.argmin(s)]
                rect[2] = pts[np.argmax(s)]
                diff = np.diff(pts, axis=1)
                rect[1] = pts[np.argmin(diff)]
                rect[3] = pts[np.argmax(diff)]
                
                # Target ukuran rasio kartu standar (448 x 625)
                width, height = 448, 625
                dst = np.array([
                    [0, 0],
                    [width - 1, 0],
                    [width - 1, height - 1],
                    [0, height - 1]
                ], dtype="float32")
                
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image_np, M, (width, height))
                return warped
        except Exception:
            pass
            
        return image_np

    def identify_card(self, image_input, top_k=3):
        """
        Mencocokkan foto input pengguna ke indeks 19.926 kartu.
        
        Param:
        - image_input: File path (str), PIL.Image, atau OpenCV BGR numpy array.
        - top_k: Jumlah kandidat kartu teratas yang ingin dikembalikan (default: 3).
        
        Returns:
        - Dictionary hasil pencocokan visual + metadata kartu + persentase confidence.
        """
        t0 = time.time()
        
        # 1. Konversi input ke PIL Image RGB
        if isinstance(image_input, str):
            image_np = cv2.imread(image_input)
            aligned_np = self.align_card_image(image_np)
            pil_img = Image.fromarray(cv2.cvtColor(aligned_np, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, np.ndarray):
            aligned_np = self.align_card_image(image_input)
            pil_img = Image.fromarray(cv2.cvtColor(aligned_np, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        else:
            raise ValueError("Format image_input tidak valid! Gunakan path str, PIL Image, atau np.ndarray.")
            
        # 2. Ekstrak Vektor Feature Embedding
        tensor_img = self.transform(pil_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            feat = self.feature_extractor(tensor_img).cpu().numpy().astype('float32')
            
        faiss.normalize_L2(feat)
        
        # 3. Query FAISS Vector Index
        distances, indices = self.index.search(feat, top_k)
        
        candidates = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            str_idx = str(idx)
            card_id = self.card_id_map.get(str_idx, "Unknown")
            
            # Confidence score dari Inner Product (Cosine Similarity -1 s/d 1)
            # Konversi Cosine Similarity ke Persentase (0 - 100%)
            confidence_pct = float(np.clip(dist, 0, 1) * 100.0)
            
            card_info = {
                "rank": rank + 1,
                "card_id": card_id,
                "confidence_percentage": round(confidence_pct, 2),
                "similarity_score": float(dist)
            }
            
            # Join metadata dari CSV jika tersedia
            if self.df_metadata is not None and card_id in self.df_metadata.index:
                row = self.df_metadata.loc[card_id]
                card_info.update({
                    "name": str(row.get("name", "")),
                    "supertype": str(row.get("supertype", "")),
                    "subtypes": str(row.get("subtypes", "")),
                    "types": str(row.get("types", "")) if pd.notnull(row.get("types")) else None,
                    "hp": float(row.get("hp")) if pd.notnull(row.get("hp")) else None,
                    "number": str(row.get("number", "")),
                    "rarity": str(row.get("rarity", "")) if pd.notnull(row.get("rarity")) else None,
                    "artist": str(row.get("artist", "")) if pd.notnull(row.get("artist")) else None,
                    "set_id": str(row.get("set.id", "")),
                    "set_name": str(row.get("set.name", "")),
                    "set_series": str(row.get("set.series", "")),
                    "release_year": int(row.get("release_year")) if pd.notnull(row.get("release_year")) else None,
                    "effective_market_price": float(row.get("effective_market_price")) if pd.notnull(row.get("effective_market_price")) else None,
                    "image_url_large": str(row.get("images.large", ""))
                })
                
            candidates.append(card_info)
            
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        
        top_match = candidates[0] if candidates else None
        
        return {
            "status": "success",
            "execution_time_ms": elapsed_ms,
            "top_match": top_match,
            "candidates": candidates
        }


# Quick test interface
if __name__ == "__main__":
    print("Testing CardIdentifier engine initialization...")
    identifier = CardIdentifier()
    print("✅ Model 1 CardIdentifier Engine siap digunakan!")
