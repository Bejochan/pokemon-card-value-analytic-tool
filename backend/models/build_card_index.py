"""
=============================================================================
Pokemon Card Value Analytic Tool — Model 1: Index Builder
=============================================================================
Skrip pembuat indeks vektor resmi (Default: CLIP ViT-B-32 + FAISS IndexFlatIP):
- Mengekstrak representasi visual berdimensi 512 untuk seluruh kartu Pokemon di
  `backend/dataset/compressed_images`.
- Membangun indeks pencarian cepat sub-milidetik FAISS IndexFlatIP (Cosine Similarity).
- Menyimpan hasil ke berkas resmi:
    * `card_embeddings.index`
    * `card_id_map.json`
  serta menyelaraskan ke `card_embeddings_clip.index` untuk kompatibilitas penuh.

(Catatan: Implementasi alternatif pembuat indeks MobileNetV3 tersimpan di
folder `backend/models/legacy_mobilenet/build_card_index.py`).

Cara Penggunaan:
    python backend/models/build_card_index.py
=============================================================================
"""

import os
import json
import time
import shutil
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np
import faiss
import open_clip
from tqdm import tqdm

# Path Konfigurasi
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "dataset", "compressed_images")
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

INDEX_OUTPUT_PATH = os.path.join(MODEL_DIR, "card_embeddings.index")
MAP_OUTPUT_PATH = os.path.join(MODEL_DIR, "card_id_map.json")

CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class PokemonCardDataset(Dataset):
    """PyTorch Dataset untuk pembacaan batch citra kartu secara efisien."""
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
            return torch.zeros((3, 224, 224)), idx, card_id


def build_index(batch_size=64, num_workers=0):
    start_time = time.time()

    print(f"1. Memuat model CLIP ({CLIP_MODEL_NAME}/{CLIP_PRETRAINED}) ke {DEVICE}...")
    model, _, preprocess = open_clip.create_model_and_transforms(
        CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED, device=DEVICE
    )
    model.eval()

    if not os.path.exists(IMAGE_DIR):
        raise FileNotFoundError(f"Folder dataset gambar tidak ditemukan: {IMAGE_DIR}")

    image_files = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])
    total_images = len(image_files)
    print(f"2. Terdeteksi {total_images:,} berkas gambar di {IMAGE_DIR}")

    dataset = PokemonCardDataset(IMAGE_DIR, image_files, transform=preprocess)
    use_pin_memory = torch.cuda.is_available()
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=use_pin_memory)

    card_id_map = {}
    embeddings_list = []

    print("3. Mengekstrak representasi visual CLIP (512-dim)...")
    with torch.no_grad():
        for batch_tensors, indices, card_ids in tqdm(dataloader, desc="Ekstraksi Fitur CLIP"):
            batch_tensors = batch_tensors.to(DEVICE)
            feats = model.encode_image(batch_tensors)

            feats_np = feats.cpu().numpy().astype("float32")
            faiss.normalize_L2(feats_np)
            embeddings_list.append(feats_np)

            for idx_val, cid in zip(indices.numpy(), card_ids):
                card_id_map[str(idx_val)] = cid

    all_embeddings = np.vstack(embeddings_list)
    dimension = all_embeddings.shape[1]

    print(f"4. Selesai mengekstrak {all_embeddings.shape[0]:,} vektor (Dimensi: {dimension})")
    print("5. Membangun indeks FAISS IndexFlatIP (Cosine Similarity)...")

    index = faiss.IndexFlatIP(dimension)
    index.add(all_embeddings)

    # Simpan indeks utama
    faiss.write_index(index, INDEX_OUTPUT_PATH)
    with open(MAP_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(card_id_map, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\n============================================================")
    print(f"BERHASIL: INDEKS RESMI CLIP SELESAI DALAM {elapsed/60:.1f} MENIT!")
    print(f"* FAISS Index : {INDEX_OUTPUT_PATH} ({os.path.getsize(INDEX_OUTPUT_PATH)/(1024*1024):.2f} MB)")
    print(f"* ID Mapping  : {MAP_OUTPUT_PATH}")
    print(f"============================================================")


if __name__ == "__main__":
    build_index()
