import os
import glob
import argparse
import numpy as np
from card_identifier import CardIdentifier

def load_validation_set(val_dir):
    samples = []
    for path in sorted(glob.glob(os.path.join(val_dir, "*"))):
        fname = os.path.basename(path)
        if "__" not in fname:
            print(f"[dilewati] '{fname}' tidak mengikuti pola <card_id>__apa_saja.ext")
            continue
        card_id = fname.split("__")[0]
        samples.append((path, card_id))
    return samples


def evaluate_at_temperature(identifier, samples, temperature, top_k=5):
    identifier.confidence_temperature = temperature
    records = []
    for path, true_card_id in samples:
        try:
            result = identifier.identify_card(path, top_k=top_k)
        except Exception as e:
            print(f"[error] gagal proses {path}: {e}")
            continue
        candidates = result.get("candidates", [])
        if not candidates:
            continue
        top1 = candidates[0]
        records.append({
            "path": path,
            "true_card_id": true_card_id,
            "pred_card_id": top1["card_id"],
            "confidence_pct": top1["confidence_percentage"],
            "correct_top1": top1["card_id"] == true_card_id,
            "correct_topk": any(c["card_id"] == true_card_id for c in candidates),
        })
    return records


def summarize(records, temperature, top_k):
    if not records:
        print("Tidak ada data valid untuk dievaluasi.")
        return None

    n = len(records)
    acc1 = sum(r["correct_top1"] for r in records) / n
    acck = sum(r["correct_topk"] for r in records) / n

    conf_correct = [r["confidence_pct"] for r in records if r["correct_top1"]]
    conf_wrong = [r["confidence_pct"] for r in records if not r["correct_top1"]]

    mean_c = float(np.mean(conf_correct)) if conf_correct else float("nan")
    mean_w = float(np.mean(conf_wrong)) if conf_wrong else float("nan")
    separation = (mean_c - mean_w) if (conf_correct and conf_wrong) else float("-inf")

    print(f"\n--- Temperature = {temperature} ---")
    print(f"Jumlah sampel             : {n}")
    print(f"Akurasi top-1             : {acc1*100:.1f}%")
    print(f"Akurasi top-{top_k}              : {acck*100:.1f}%")
    print(f"Confidence rata2 (BENAR)  : {mean_c:.1f}%")
    print(f"Confidence rata2 (SALAH)  : {mean_w:.1f}%")
    print(f"Selisih (makin besar makin baik): {separation:.1f}")

    return separation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--val_dir", required=True,
                         help="Folder berisi foto validasi, nama file: <card_id>__apa_saja.ext")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--temperatures", nargs="+", type=float,
                         default=[0.03, 0.05, 0.06, 0.08, 0.10, 0.15, 0.20])
    args = parser.parse_args()

    samples = load_validation_set(args.val_dir)
    if not samples:
        print("Tidak ada foto valid ditemukan. Cek nama file & folder.")
        return

    print(f"Ditemukan {len(samples)} foto validasi di '{args.val_dir}'.")
    identifier = CardIdentifier()

    best_temp, best_sep = None, float("-inf")
    for T in args.temperatures:
        records = evaluate_at_temperature(identifier, samples, T, top_k=args.top_k)
        sep = summarize(records, T, args.top_k)
        if sep is not None and sep > best_sep:
            best_sep, best_temp = sep, T

    if best_temp is not None and best_sep > float("-inf"):
        print("\n=== Rekomendasi ===")
        print(f"confidence_temperature = {best_temp} memberi pemisahan confidence")
        print("BENAR vs SALAH paling jelas dari data validasi Anda.")
        print(f"Pakai di kode: CardIdentifier(confidence_temperature={best_temp})")
    else:
        print("\nBelum bisa menentukan rekomendasi -- coba tambah jumlah & variasi foto validasi.")


if __name__ == "__main__":
    main()