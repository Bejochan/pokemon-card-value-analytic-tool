"""
=============================================================================
Pokemon Card Value Analytic Tool — Model 1: Card Index Builder (High Speed)
=============================================================================
Skrip ini mengekstrak 512-dimensi vektor fitur visual dari 19.926 gambar kartu
menggunakan PyTorch DataLoader (Multi-threaded I/O) & MobileNetV3.

Output:
1. backend/models/card_embeddings.index (Indeks FAISS)
2. backend/models/card_id_map.json (Pemetaan urutan vektor ke card_id)
=============================================================================
"""

import os
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np
import faiss
from tqdm import tqdm

# Configuration Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "dataset", "compressed_images")
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_OUTPUT_PATH = os.path.join(MODEL_DIR, "card_embeddings.index")
MAP_OUTPUT_PATH = os.path.join(MODEL_DIR, "card_id_map.json")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class PokemonCardDataset(Dataset):
    """PyTorch Dataset untuk pembacaan gambar multi-threaded cepat."""
    def __init__(self, image_dir, image_files, transform=None):
        self.image_dir = image_dir
        self.image_files = image_files
        self.transform = transform

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        filename = self.image_files[idx]
        fname = os.path.splitext(filename)[0]
        card_id = "ex10-?" if fname == "question_hires" else fname
        
        img_path = os.path.join(self.image_dir, filename)
        try:
            with Image.open(img_path) as img:
                img_rgb = img.convert("RGB")
                if self.transform:
                    tensor_img = self.transform(img_rgb)
                return tensor_img, idx, card_id
        except Exception:
            # Fallback zero tensor jika ada error
            return torch.zeros((3, 224, 224)), idx, card_id


def build_index(batch_size=128, num_workers=2):
    start_time = time.time()
    
    print("1. Memuat model backbone Neural Network (MobileNetV3)...")
    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    backbone = models.mobilenet_v3_small(weights=weights)
    feature_extractor = nn.Sequential(*list(backbone.children())[:-1], nn.Flatten())
    feature_extractor.to(DEVICE)
    feature_extractor.eval()
    
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    if not os.path.exists(IMAGE_DIR):
        raise FileNotFoundError(f"Folder gambar tidak ditemukan di: {IMAGE_DIR}")
    
    image_files = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])
    total_images = len(image_files)
    print(f"2. Ditemukan {total_images:,} berkas gambar di {IMAGE_DIR}")
    
    dataset = PokemonCardDataset(IMAGE_DIR, image_files, transform=transform)
    # Gunakan num_workers=0 jika di Windows subprocess bermasalah, atau num_workers=2
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    
    card_id_map = {}
    embeddings_list = []
    
    print("3. Memulai ekstraksi fitur visual berkecepatan tinggi (DataLoader)...")
    
    with torch.no_grad():
        for batch_tensors, indices, card_ids in tqdm(dataloader, desc="Extracting Features"):
            batch_tensors = batch_tensors.to(DEVICE)
            feats = feature_extractor(batch_tensors)
            
            feats_np = feats.cpu().numpy().astype('float32')
            faiss.normalize_L2(feats_np)
            embeddings_list.append(feats_np)
            
            for idx_val, cid in zip(indices.numpy(), card_ids):
                card_id_map[str(idx_val)] = cid

    all_embeddings = np.vstack(embeddings_list)
    dimension = all_embeddings.shape[1]
    
    print(f"4. Selesai mengekstrak {all_embeddings.shape[0]:,} vektor (Dimensi: {dimension})")
    print("5. Membangun FAISS Vector Index (IndexFlatIP)...")
    
    index = faiss.IndexFlatIP(dimension)
    index.add(all_embeddings)
    
    faiss.write_index(index, INDEX_OUTPUT_PATH)
    with open(MAP_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(card_id_map, f, indent=2)
        
    elapsed = time.time() - start_time
    print(f"\n============================================================")
    print(f"✨ PROSES INDEXING SELESAI DALAM {elapsed:.2f} DETIK!")
    print(f"• FAISS Index Saved  : {INDEX_OUTPUT_PATH} ({os.path.getsize(INDEX_OUTPUT_PATH)/(1024*1024):.2f} MB)")
    print(f"• ID Map Saved       : {MAP_OUTPUT_PATH}")
    print(f"============================================================")


if __name__ == "__main__":
    build_index()
