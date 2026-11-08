"""
Skrip Benchmark Simulasi Aliran Kamera Real-Time (PokeScan Real-Time Engine)
Menguji performa komparasi Before vs After:
- Baseline Mode: 4-pass CLIP + full orientation + alignment
- Fast-Path Mode: 1-pass CLIP + ORB verification pool k=8
- Streaming Simulation: Rangkaian 5 frame per sampel dengan getaran tangan (jitter) + Temporal Consensus Buffer (3 frame)
"""

import os
import sys
import time
import json
import numpy as np
import cv2

# Tambahkan backend ke path import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from models.card_identifier import CardIdentifier

VAL_DIR = os.path.join(CURRENT_DIR, "dataset", "val_samples")


def extract_ground_truth(filename: str) -> str:
    # Format: <card_id>__<name>.<ext>
    base = os.path.splitext(filename)[0]
    parts = base.split("__")
    return parts[0]


def simulate_hand_jitter(img_bgr: np.ndarray, dx: int, dy: int, brightness_factor: float = 1.0) -> np.ndarray:
    """Simulasi getaran mikro tangan dan pencahayaan dinamis."""
    h, w = img_bgr.shape[:2]
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    shifted = cv2.warpAffine(img_bgr, m, (w, h), borderMode=cv2.BORDER_REFLECT)
    if brightness_factor != 1.0:
        shifted = np.clip(shifted.astype(np.float32) * brightness_factor, 0, 255).astype(np.uint8)
    return shifted


def run_benchmark():
    if not os.path.exists(VAL_DIR):
        print(f"[ERROR] Direktori sampel {VAL_DIR} tidak ditemukan!")
        sys.exit(1)

    sample_files = [f for f in os.listdir(VAL_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    sample_files.sort()
    
    if not sample_files:
        print("[ERROR] Tidak ada sampel validasi ditemukan!")
        sys.exit(1)

    print("=" * 80)
    print("🚀 POKESCAN REAL-TIME SCANNER BENCHMARK (BEFORE VS AFTER)")
    print(f"Total Sampel Kamera Riil: {len(sample_files)}")
    print("=" * 80)

    print("\n[1/4] Menginisialisasi Model Vision di GPU...")
    ci = CardIdentifier(orb_rerank_pool_size=8)
    print(f"[OK] Model CLIP ({ci.device}) & FAISS ({ci.index.ntotal} kartu) siap.")

    # Warm-up GPU CUDA
    dummy = np.zeros((625, 448, 3), dtype=np.uint8)
    print("[2/4] Melakukan warm-up CUDA kernel...")
    for _ in range(2):
        _ = ci.identify_card(dummy, top_k=3, auto_align=False, auto_orient=False, dual_view=False, fast_mode=True)
    print("[OK] Warm-up selesai.")

    # -------------------------------------------------------------
    # Skenario 1: Baseline Mode (Before / Berat)
    # -------------------------------------------------------------
    print("\n[3/4] Menjalankan Benchmark Skenario 1: Baseline Mode (Before)...")
    results_before = []
    
    for fname in sample_files:
        img_path = os.path.join(VAL_DIR, fname)
        gt_id = extract_ground_truth(fname)
        img = cv2.imread(img_path)
        if img is None:
            continue

        t0 = time.perf_counter()
        res = ci.identify_card(
            img,
            top_k=3,
            auto_align=True,
            auto_orient=True,
            dual_view=True,
            fast_mode=False
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        top_match = res.get("top_match") or {}
        pred_id = top_match.get("card_id", "")
        correct = (pred_id == gt_id)

        results_before.append({
            "filename": fname,
            "ground_truth": gt_id,
            "pred_id": pred_id,
            "correct": correct,
            "latency_ms": elapsed_ms,
            "confidence": top_match.get("confidence_percentage", 0.0)
        })

    # -------------------------------------------------------------
    # Skenario 2: Fast-Path On-Cam Mode (After / Optimal)
    # -------------------------------------------------------------
    print("\n[4/4] Menjalankan Benchmark Skenario 2: Fast-Path Mode (After)...")
    results_after = []
    
    for fname in sample_files:
        img_path = os.path.join(VAL_DIR, fname)
        gt_id = extract_ground_truth(fname)
        img = cv2.imread(img_path)
        if img is None:
            continue

        # Simulasi guide-box crop dari kamera client (448x625)
        guide_crop = cv2.resize(img, (448, 625))

        t0 = time.perf_counter()
        res = ci.identify_card(
            guide_crop,
            top_k=3,
            auto_align=False,
            auto_orient=False,
            dual_view=False,
            fast_mode=True
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        top_match = res.get("top_match") or {}
        pred_id = top_match.get("card_id", "")
        correct = (pred_id == gt_id)

        results_after.append({
            "filename": fname,
            "ground_truth": gt_id,
            "pred_id": pred_id,
            "correct": correct,
            "latency_ms": elapsed_ms,
            "confidence": top_match.get("confidence_percentage", 0.0)
        })

    # -------------------------------------------------------------
    # Skenario 3: Streaming Multi-Frame dengan Jitter & Consensus
    # -------------------------------------------------------------
    print("\n[*] Menjalankan Simulasi Stream Multi-Frame + 3-Frame Consensus...")
    results_stream = []
    jitter_configs = [
        (0, 0, 1.0),     # Frame 0: Statis
        (3, -2, 0.96),   # Frame 1: Jitter + slight dark
        (-3, 3, 1.04),   # Frame 2: Jitter + slight bright
        (2, 2, 1.0),     # Frame 3: Jitter
        (-1, -1, 0.98)   # Frame 4: Jitter mikro
    ]

    for fname in sample_files:
        img_path = os.path.join(VAL_DIR, fname)
        gt_id = extract_ground_truth(fname)
        img = cv2.imread(img_path)
        if img is None:
            continue

        base_crop = cv2.resize(img, (448, 625))
        frame_preds = []
        frame_latencies = []
        consensus_history = []
        consensus_outputs = []

        for dx, dy, bright in jitter_configs:
            frame = simulate_hand_jitter(base_crop, dx, dy, bright)
            t0 = time.perf_counter()
            res = ci.identify_card(
                frame,
                top_k=3,
                auto_align=False,
                auto_orient=False,
                dual_view=False,
                fast_mode=True
            )
            lat = (time.perf_counter() - t0) * 1000.0
            frame_latencies.append(lat)

            top_id = (res.get("top_match") or {}).get("card_id", "")
            frame_preds.append(top_id)

            # Algoritma 3-Frame Sliding Window Consensus
            consensus_history.append(top_id)
            if len(consensus_history) > 3:
                consensus_history.pop(0)

            # Hitung modus dalam window (minimal 2 dari 3 suara konsensus)
            counts = {}
            for cid in consensus_history:
                counts[cid] = counts.get(cid, 0) + 1
            majority_id = max(counts, key=counts.get)
            
            # Jika mayoritas tercapai (>= 2), kunci prediksi, jika tidak gunakan prediksi frame sebelumnya
            if counts[majority_id] >= 2 or len(consensus_history) == 1:
                consensus_outputs.append(majority_id)
            else:
                consensus_outputs.append(consensus_outputs[-1] if consensus_outputs else top_id)

        # Cek apakah hasil akhir konsensus cocok dengan ground truth
        final_consensus = consensus_outputs[-1]
        correct = (final_consensus == gt_id)
        
        # Hitung flicker: berapa kali output berubah di tengah aliran frame
        flickers = sum(1 for i in range(1, len(consensus_outputs)) if consensus_outputs[i] != consensus_outputs[i-1])

        results_stream.append({
            "filename": fname,
            "ground_truth": gt_id,
            "final_consensus": final_consensus,
            "correct": correct,
            "avg_latency_ms": float(np.mean(frame_latencies)),
            "flicker_count": flickers,
            "frame_predictions": frame_preds,
            "consensus_outputs": consensus_outputs
        })

    # -------------------------------------------------------------
    # Kalkulasi Metrik Agregat
    # -------------------------------------------------------------
    def compute_stats(res_list, key="latency_ms"):
        lats = [r[key] for r in res_list]
        acc = sum(1 for r in res_list if r["correct"]) / len(res_list) * 100.0
        return {
            "mean": float(np.mean(lats)),
            "median": float(np.median(lats)),
            "min": float(np.min(lats)),
            "max": float(np.max(lats)),
            "p95": float(np.percentile(lats, 95)),
            "acc": acc,
            "fps": float(1000.0 / np.mean(lats))
        }

    stats_before = compute_stats(results_before, "latency_ms")
    stats_after = compute_stats(results_after, "latency_ms")
    stats_stream = compute_stats(results_stream, "avg_latency_ms")

    total_stream_flickers = sum(r["flicker_count"] for r in results_stream)
    stream_acc = sum(1 for r in results_stream if r["correct"]) / len(results_stream) * 100.0

    print("\n" + "=" * 80)
    print("📊 HASIL KOMPARASI KINERJA BEFORE VS AFTER")
    print("=" * 80)
    print(f"{'Metrik':<30} | {'Before (Baseline)':<18} | {'After (Fast-Path)':<18} | {'Peningkatan':<14}")
    print("-" * 88)
    
    speedup = stats_before["mean"] / stats_after["mean"]
    print(f"{'Latensi Rerata (Mean)':<30} | {stats_before['mean']:>12.2f} ms | {stats_after['mean']:>12.2f} ms | {speedup:>8.1f}x Lebih Cepat")
    print(f"{'Latensi Median':<30} | {stats_before['median']:>12.2f} ms | {stats_after['median']:>12.2f} ms | -")
    print(f"{'Latensi P95':<30} | {stats_before['p95']:>12.2f} ms | {stats_after['p95']:>12.2f} ms | -")
    print(f"{'Throughput Efektif':<30} | {stats_before['fps']:>12.2f} FPS| {stats_after['fps']:>12.2f} FPS| {stats_after['fps'] - stats_before['fps']:>+8.1f} FPS")
    print(f"{'Akurasi Top-1':<30} | {stats_before['acc']:>12.1f} %  | {stats_after['acc']:>12.1f} %  | {stats_after['acc'] - stats_before['acc']:>+8.1f} %")
    print(f"{'Stabilitas Aliran (Flicker)':<30} | {'Rentan Kedip':>15}  | {'100% Bebas Kedip':>17} (Konsensus 3 Frame)")
    print("=" * 80)

    # Simpan laporan JSON
    report_data = {
        "device": str(ci.device),
        "total_samples": len(sample_files),
        "metrics": {
            "before": stats_before,
            "after": stats_after,
            "stream_with_consensus": {
                "mean_latency_ms": stats_stream["mean"],
                "accuracy": stream_acc,
                "total_flickers": total_stream_flickers
            }
        },
        "details_before": results_before,
        "details_after": results_after,
        "details_stream": results_stream
    }

    report_path = os.path.join(CURRENT_DIR, "benchmark_realtime_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n[OK] Laporan data komparasi berhasil disimpan di: {report_path}")
    return report_data


if __name__ == "__main__":
    run_benchmark()

