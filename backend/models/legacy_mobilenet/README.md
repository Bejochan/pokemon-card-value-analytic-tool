# Legacy / Alternative Baseline: MobileNetV3 Card Identifier

Folder ini berisi implementasi **arsitektur alternatif / baseline awal (MobileNetV3-Large)** dari Model 1 (Card Identification Engine).

---

## 📌 Status & Posisi dalam Proyek

- **Model Produksi Resmi (Default):**
  Model utama Regokemon menggunakan **OpenAI CLIP (Vision Transformer ViT-B-32)** yang berada di folder induk (`backend/models/card_identifier.py`). CLIP terbukti jauh lebih akurat pada visual 2D ilustrasi kartu Pokémon, tahan terhadap variasi pencahayaan, dan dilengkapi fitur **4-Way Smart Auto-Orientation**.
  
- **Tujuan Folder Ini (Alternative Baseline):**
  Folder ini dipertahankan sebagai **komparasi akademik (Ablation Study / Baseline Comparison)** untuk laporan proyek analitika data & computer vision:
  - Membuktikan secara empiris kelemahan model klasifikasi umum (MobileNet ImageNet) terhadap domain ilustrasi kartu.
  - Membandingkan metrik akurasi Top-1, Top-5, dan Mean Reciprocal Rank (MRR) antara MobileNetV3 vs CLIP ViT-B-32.

---

## 📁 Berkas di Folder Ini

1. `card_identifier.py` — Engine inferensi menggunakan MobileNetV3-Large + FAISS Index (dimensi 960).
2. `card_identifier_oncam.py` — Pemindai langsung kamera berbasis MobileNetV3.
3. `card_identifier_manual.py` — Pemindai foto kartu manual berbasis MobileNetV3.
4. `build_card_index.py` — Skrip pembuat indeks vektor MobileNetV3.
5. `card_id_map.json` — Pemetaan indeks numerik ke `card_id` kartu.
6. `card_embeddings.index` — File binary indeks FAISS MobileNet (di-ignore oleh git karena ukuran ~46MB).

---

## 🚀 Cara Menjalankan Baseline (Untuk Pengujian Komparasi)

Jika ingin menguji baseline MobileNet untuk bahan laporan/grafik perbandingan:

```bash
# Pengujian foto manual dengan MobileNet:
python backend/models/legacy_mobilenet/card_identifier_manual.py path/ke/foto.jpg --expected_card_id sv8pt5-77

# Pemindaian live on-cam dengan MobileNet:
python backend/models/legacy_mobilenet/card_identifier_oncam.py
```
