#!/usr/bin/env python3
"""Resumable downloader for Pokémon TCG reference images."""

import argparse
import csv
import hashlib
import io
import os
import time
from pathlib import Path

import pandas as pd
import requests
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR / "dataset"
DEFAULT_INPUT = DATASET_DIR / "pokemon_cards_dataset.csv"
DEFAULT_IMAGE_DIR = DATASET_DIR / "pokemon-cards-dataset"
DEFAULT_MANIFEST = DEFAULT_IMAGE_DIR / "image_manifest.csv"
MANIFEST_FIELDS = [
    "card_id",
    "image_url",
    "local_path",
    "status",
    "http_status",
    "width",
    "height",
    "file_size",
    "sha256",
    "error",
]


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["card_id"]: row for row in csv.DictReader(handle)}


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(manifest.values())
    os.replace(temporary, path)


def download_one(row: pd.Series, image_dir: Path, retries: int) -> dict:
    card_id = str(row["card_id"])
    image_url = str(row["images.large"])
    target = image_dir / f"{card_id}.png"
    result = {field: "" for field in MANIFEST_FIELDS}
    result.update({"card_id": card_id, "image_url": image_url, "local_path": str(target)})

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(image_url, timeout=30)
            result["http_status"] = str(response.status_code)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            image.verify()
            image = Image.open(io.BytesIO(response.content))
            result["width"], result["height"] = map(str, image.size)
            result["file_size"] = str(len(response.content))
            result["sha256"] = hashlib.sha256(response.content).hexdigest()
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(response.content)
            os.replace(temporary, target)
            result["status"] = "downloaded"
            return result
        except (requests.RequestException, OSError, ValueError) as exc:
            result["error"] = str(exc)
            if attempt < retries:
                time.sleep(2**(attempt - 1))

    result["status"] = "failed"
    return result


def is_valid_download(record: dict, image_dir: Path) -> bool:
    path = Path(record.get("local_path", ""))
    if not path.is_absolute():
        path = image_dir / path.name
    return record.get("status") == "downloaded" and path.exists() and path.stat().st_size > 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--limit", type=int, default=0, help="Maksimum file baru per run; 0 berarti semua.")
    parser.add_argument("--start-index", type=int, default=0, help="Index CSV mulai dari 0.")
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    if args.limit < 0 or args.start_index < 0 or args.retries < 1:
        parser.error("--limit, --start-index, dan --retries harus valid.")

    data = pd.read_csv(args.input)
    required = {"card_id", "images.large"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ada: {', '.join(sorted(missing))}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(args.manifest)
    attempted = 0
    skipped = 0

    for _, row in data.iloc[args.start_index:].iterrows():
        card_id = str(row["card_id"])
        existing = manifest.get(card_id, {})
        if is_valid_download(existing, args.output_dir):
            skipped += 1
            continue
        if args.limit and attempted >= args.limit:
            break
        result = download_one(row, args.output_dir, args.retries)
        manifest[card_id] = result
        save_manifest(args.manifest, manifest)
        attempted += 1
        print(f"[{attempted}] {card_id}: {result['status']}")

    print(f"Selesai. Download dicoba: {attempted}; dilewati karena sudah valid: {skipped}.")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()