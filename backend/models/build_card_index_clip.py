"""
=============================================================================
Pokemon Card Value Analytic Tool — Index Builder (varian CLIP)
=============================================================================
Versi eksperimental dari build_card_index.py yang memakai CLIP (ViT-B-32,
bobot "openai") sebagai pengganti MobileNetV3 untuk ekstraksi fitur visual.

INI FILE TERPISAH -- TIDAK menimpa build_card_index.py atau
card_embeddings.index / card_id_map.json yang sudah ada dan terbukti jalan.
Menjalankan skrip ini membuat index & mapping BARU dengan nama berbeda:
    card_embeddings_clip.index
    card_id_map_clip.json
supaya versi MobileNet tetap aman sebagai cadangan kalau hasil CLIP kurang
memuaskan.

Cara pakai:
    pip install open_clip_torch
    python build_card_index_clip.py

CATATAN PENTING:
- Proses ini mengekstrak ulang fitur dari SEMUA (~19.926) gambar di
  dataset/compressed_images -- ini SEKALI JALAN, tapi bisa makan waktu lama
  di CPU (perkiraan kasar: 1-3 jam tergantung spesifikasi komputer; jauh
  lebih cepat dengan GPU NVIDIA + CUDA, PyTorch akan otomatis memakainya
  kalau tersedia). Skrip ini mencetak estimasi sisa waktu setiap 500 gambar.
- Bobot model CLIP (~350MB) akan diunduh otomatis saat pertama kali
  dijalankan (butuh koneksi internet sekali itu saja, lalu tersimpan di
  cache lokal buat pemakaian berikutnya).
- Konvensi nama file & card_id PERSIS SAMA dengan build_card_index.py asli
  (card_id diambil dari nama file gambar, bukan dari CSV) -- supaya hasilnya
  tetap kompatibel dengan sisa sistem (metadata CSV, ORB re-rank, dst).
=============================================================================
"""

import os
import json
import time
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np
import faiss
import open_clip
from tqdm import tqdm

# Configuration Paths -- IDENTIK dengan build_card_index.py asli, cuma output
# index/map-nya diberi akhiran "_clip" supaya tidak menimpa yang sudah ada.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "dataset", "compressed_images")
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_OUTPUT_PATH = os.path.join(MODEL_DIR, "card_embeddings_clip.index")
MAP_OUTPUT_PATH = os.path.join(MODEL_DIR, "card_id_map_clip.json")

CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"  # bisa dicoba ganti ke "laion2b_s34b_b79k" (dilatih data lebih banyak,
                             # kadang lebih tajam, tapi belum tentu -- worth dicoba dibandingkan
                             # kalau versi "openai" ini hasilnya masih kurang memuaskan)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class PokemonCardDataset(Dataset):
    """PyTorch Dataset untuk pembacaan gambar multi-threaded cepat -- struktur
    IDENTIK dengan build_card_index.py asli."""
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
            # Fallback tensor nol kalau ada error baca gambar
            return torch.zeros((3, 224, 224)), idx, card_id


def build_index(batch_size=64, num_workers=0):
    """
    v1.1: num_workers default diubah ke 0 (bukan multiprocessing), dan
    pin_memory dikondisikan hanya nyala kalau ada GPU (CUDA). Ini perbaikan
    dari error "not enough memory" untuk alokasi kecil (~600KB) yang muncul
    di Windows -- itu BUKAN benar-benar kehabisan RAM, tapi gejala klasik
    worker process DataLoader Windows yang crash/corrupt secara acak saat
    num_workers>0, terutama kalau dikombinasikan pin_memory=True padahal
    jalan di CPU (pin_memory cuma berguna untuk transfer CPU->GPU).

    Kalau proses ini terasa lambat & komputer kamu punya banyak core CPU
    nganggur, boleh coba naikkan num_workers ke 2 -- tapi kalau muncul error
    "not enough memory" lagi, turunkan lagi ke 0.
    """
    start_time = time.time()

    print(f"1. Memuat model CLIP ({CLIP_MODEL_NAME}/{CLIP_PRETRAINED}) ke {DEVICE}...")
    print("   (unduhan bobot ~350MB terjadi otomatis kalau ini pertama kali dijalankan)")
    model, _, preprocess = open_clip.create_model_and_transforms(
        CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED, device=DEVICE
    )
    model.eval()

    if not os.path.exists(IMAGE_DIR):
        raise FileNotFoundError(f"Folder gambar tidak ditemukan di: {IMAGE_DIR}")

    image_files = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])
    total_images = len(image_files)
    print(f"2. Ditemukan {total_images:,} berkas gambar di {IMAGE_DIR}")

    dataset = PokemonCardDataset(IMAGE_DIR, image_files, transform=preprocess)
    use_pin_memory = torch.cuda.is_available()  # cuma berguna kalau ada GPU
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=use_pin_memory)

    card_id_map = {}
    embeddings_list = []

    print("3. Memulai ekstraksi fitur visual (CLIP)...")

    with torch.no_grad():
        for batch_tensors, indices, card_ids in tqdm(dataloader, desc="Extracting CLIP Features"):
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
    print("5. Membangun FAISS Vector Index (IndexFlatIP)...")

    index = faiss.IndexFlatIP(dimension)
    index.add(all_embeddings)

    faiss.write_index(index, INDEX_OUTPUT_PATH)
    with open(MAP_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(card_id_map, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\n============================================================")
    print(f"SUCCESS: PROSES INDEXING (CLIP) SELESAI DALAM {elapsed/60:.1f} MENIT!")
    print(f"* FAISS Index Saved  : {INDEX_OUTPUT_PATH} ({os.path.getsize(INDEX_OUTPUT_PATH)/(1024*1024):.2f} MB)")
    print(f"* ID Map Saved       : {MAP_OUTPUT_PATH}")
    print(f"============================================================")
    print("\nSelanjutnya, gunakan card_identifier_clip.py (bukan card_identifier.py)")
    print("untuk mencoba identifikasi kartu dengan index CLIP yang baru ini.")


if __name__ == "__main__":
    build_index()