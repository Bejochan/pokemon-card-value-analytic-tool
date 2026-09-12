import os
import sys
import argparse
import cv2
import numpy as np
from PIL import Image
import faiss

from card_identifier import CardIdentifier

def pick_file_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("[error] Modul tkinter tidak tersedia di instalasi Python kamu.")
        print("        Ketik path file secara manual sebagai gantinya.")
        return input("Masukkan path ke file foto kartu: ").strip('"').strip()

    root = tk.Tk()
    root.withdraw()          # sembunyikan window utama tkinter, cuma tampilkan dialog file
    root.attributes('-topmost', True)   # pastikan dialog muncul di depan jendela lain
    file_path = filedialog.askopenfilename(
        title="Pilih foto kartu Pokemon",
        filetypes=[("Gambar", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Semua file", "*.*")]
    )
    root.destroy()
    return file_path


def find_full_rank_from_aligned(identifier, aligned_image_path, expected_card_id, use_tta=False):
    aligned_bgr = cv2.imread(aligned_image_path)
    if aligned_bgr is None:
        print(f"[error] Tidak bisa membaca file gambar: {aligned_image_path}")
        return None, None

    pil_img = Image.fromarray(cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB))
    feat = identifier._extract_embedding_tta(pil_img) if use_tta else identifier._extract_embedding(pil_img)
    faiss.normalize_L2(feat)

    n_total = identifier.index.ntotal
    distances, indices = identifier.index.search(feat, n_total)  # ranking penuh, index-nya flat jadi tetap cepat

    sims = distances[0]
    ids = indices[0]

    found_rank, found_sim = None, None
    for rank, idx in enumerate(ids):
        card_id = identifier.card_id_map.get(str(idx))
        if card_id == expected_card_id:
            found_rank = rank + 1
            found_sim = float(sims[rank])
            break

    print(f"\n=== PENELUSURAN PENUH untuk card_id='{expected_card_id}' (dari {n_total} total kartu) ===")
    if found_rank is None:
        print(f"[!] card_id '{expected_card_id}' TIDAK DITEMUKAN di card_id_map / index sama sekali.")
        print("    Cek lagi ejaan card_id, atau pastikan kartu ini benar-benar sudah")
        print("    ikut di-proses saat build_card_index.py dijalankan.")
        return None, None

    top1_id = identifier.card_id_map.get(str(ids[0]))
    print(f"Kartu yang BENAR ada di RANKING #{found_rank} dari {n_total}.")
    print(f"Similarity kartu yang benar   : {found_sim:.4f}")
    print(f"Similarity top-1 (tebakan)    : {sims[0]:.4f}  (card_id={top1_id})")
    print(f"Selisih similarity (top1 - yang benar): {sims[0] - found_sim:.4f}")

    if found_rank == 1:
        print("-> Tebakan top-1 SUDAH BENAR.")
    elif found_rank <= 20:
        print("-> Kartu yang benar dekat top (<=20) tapi kalah tipis: ini soal RANKING/")
        print("   diskriminasi pada kandidat yang mirip -- coba aktifkan --use_orb_rerank,")
        print("   atau kalibrasi ulang confidence_temperature.")
    else:
        print("-> Kartu yang benar ranking-nya JAUH dari top. Ini indikasi kuat bahwa")
        print("   fitur/embedding TIDAK CUKUP DISKRIMINATIF untuk kartu ini -- bukan lagi")
        print("   soal kalibrasi confidence, tapi soal backbone/feature extraction.")

    return found_rank, found_sim


def process_one(identifier, image_path, top_k, expected_card_id, use_tta, full_rank_search):
    if not os.path.exists(image_path):
        print(f"[error] File tidak ditemukan: {image_path}")
        return

    debug_path = "debug_manual_aligned.jpg"
    result = identifier.identify_card(image_path, top_k=top_k, debug=True, debug_save_path=debug_path)

    print(f"\n[debug] Gambar hasil alignment disimpan di: {os.path.abspath(debug_path)}")
    print("        (buka file ini untuk cek apakah crop/perataan kartunya sudah benar)")

    print(f"\n=== HASIL IDENTIFIKASI (top-{top_k}) ===")
    for c in result["candidates"]:
        name = c.get("name", "?")
        set_name = c.get("set_name", "?")
        print(f"#{c['rank']} {name:20s} ({set_name:20s}) card_id={c['card_id']:10s} "
              f"raw={c['raw_similarity_score']:.4f}  conf={c['confidence_percentage']}% ({c['confidence_label']})")

    top1 = result["candidates"][0] if result["candidates"] else None
    if top1:
        print(f"\nWaktu inferensi     : {result['execution_time_ms']} ms")
        print(f"Margin top1 vs top2 : {top1.get('margin_to_runner_up')}")

    pool = result.get("debug_similarity_pool", [])
    print(f"\n[debug] pool similarity (top-{len(pool)}): {pool}")

    if not expected_card_id:
        # Kalau tidak dikasih lewat argumen CLI, tawarkan input interaktif (boleh dikosongkan)
        expected_card_id = input("\nCard ID yang BENAR (opsional, Enter untuk lewati): ").strip() or None

    if expected_card_id:
        is_correct = top1 is not None and top1["card_id"] == expected_card_id
        in_topk = any(c["card_id"] == expected_card_id for c in result["candidates"])

        print("\n=== VALIDASI ===")
        print(f"Expected card_id : {expected_card_id}")
        print(f"Tebakan top-1    : {top1['card_id'] if top1 else None}  "
              f"{'BENAR' if is_correct else 'SALAH'}")
        print(f"Ada di top-{top_k}      : {'Ya' if in_topk else 'Tidak'}")

        if full_rank_search or not in_topk:
            find_full_rank_from_aligned(identifier, debug_path, expected_card_id, use_tta=use_tta)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image_path", nargs="?",
                         help="Path ke file foto kartu (opsional -- kalau kosong, jendela pilih file akan terbuka).")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--use_tta", action="store_true", help="Aktifkan Test-Time Augmentation.")
    parser.add_argument("--use_orb_rerank", action="store_true", help="Aktifkan re-ranking ORB.")
    parser.add_argument("--expected_card_id", type=str, default=None,
                         help="card_id yang BENAR (kalau tahu), untuk validasi otomatis.")
    parser.add_argument("--full_rank_search", action="store_true",
                         help="Paksa cari ranking penuh meski expected_card_id ada di top-k.")
    args = parser.parse_args()

    print("Memuat AI Engine dan Index (mohon tunggu)...")
    identifier = CardIdentifier(use_tta=args.use_tta, use_orb_rerank=args.use_orb_rerank)
    print(f"[debug] use_tta={args.use_tta}  use_orb_rerank={args.use_orb_rerank}  "
          f"confidence_temperature={identifier.confidence_temperature}")

    if args.image_path:
        # Path dikasih langsung lewat argumen CLI -- proses sekali lalu selesai.
        process_one(identifier, args.image_path, args.top_k, args.expected_card_id,
                    args.use_tta, args.full_rank_search)
        return

    # Tidak ada argumen -- buka jendela pilih file berulang kali, mirip upload gambar di chat.
    print("\nJendela pilih file akan terbuka. Pilih foto kartu, atau tekan Cancel untuk keluar.")
    while True:
        image_path = pick_file_dialog()
        if not image_path:
            print("\nTidak ada file dipilih. Selesai.")
            break
        process_one(identifier, image_path, args.top_k, args.expected_card_id,
                    args.use_tta, args.full_rank_search)
        print("\n--- Pilih file lain untuk scan berikutnya, atau Cancel untuk keluar ---")


if __name__ == "__main__":
    main()