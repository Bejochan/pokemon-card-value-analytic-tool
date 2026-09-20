"""
=============================================================================
Pokemon Card Value Analytic Tool — Model 1: Card Identifier Engine
=============================================================================
Arsitektur Utama: OpenAI CLIP (Vision Transformer ViT-B-32) + FAISS Index
+ ORB Keypoint Verification + 4-Way Smart Auto-Orientation.

Engine ini adalah model resmi Model 1 untuk Regokemon:
- Backbone: CLIP ViT-B-32 (openai pre-trained) untuk semantic visual retrieval.
- Database: FAISS IndexFlatIP (20.426 kartu) dengan pencarian sub-milidetik.
- Verifikasi: ORB local feature re-ranking untuk diskriminasi kartu varian mirip.
- Ketahanan: 4-Way Auto-Orientation (0°, 90°, 180°, 270°) agar kartu selalu
  dianalisis dalam posisi tegak lurus terlepas dari sudut pemotretan pengguna.
=============================================================================
"""

import os
import json
import time
import cv2
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageEnhance
import faiss
import open_clip

# Configuration Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(MODEL_DIR, "card_embeddings.index")
MAP_PATH = os.path.join(MODEL_DIR, "card_id_map.json")
CSV_PATH = os.path.join(BASE_DIR, "dataset", "pokemon_cards_dataset_cleaned.csv")
IMAGE_DIR = os.path.join(BASE_DIR, "dataset", "compressed_images")

# Arsitektur CLIP Default
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "openai"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CARD_ASPECT_RATIO = 63.0 / 88.0  # 0.7159


class CardIdentifier:
    def __init__(self, index_path=INDEX_PATH, map_path=MAP_PATH, csv_path=CSV_PATH,
                 image_dir=IMAGE_DIR, confidence_temperature=0.03,
                 calibration_pool_size=20, use_tta=False, use_orb_rerank=True,
                 orb_rerank_pool_size=50):
        self.index_path = index_path
        self.map_path = map_path
        self.csv_path = csv_path
        self.image_dir = image_dir

        self.confidence_temperature = max(confidence_temperature, 1e-6)
        self.calibration_pool_size = calibration_pool_size
        self.use_tta = use_tta
        self.use_orb_rerank = use_orb_rerank
        self.orb_rerank_pool_size = orb_rerank_pool_size

        self.index = None
        self.card_id_map = {}
        self.df_metadata = None
        self.clip_model = None
        self.transform = None
        self._orb = None

        self._load_resources()

    def _load_resources(self):
        if not os.path.exists(self.index_path) or not os.path.exists(self.map_path):
            raise FileNotFoundError(
                f"Berkas index tidak ditemukan di {self.index_path}! "
                "Silakan jalankan `python backend/models/build_card_index.py` terlebih dahulu."
            )

        self.index = faiss.read_index(self.index_path)
        with open(self.map_path, "r", encoding="utf-8") as f:
            self.card_id_map = json.load(f)

        if os.path.exists(self.csv_path):
            self.df_metadata = pd.read_csv(self.csv_path).set_index("card_id", drop=False)

        print(f"Memuat model CLIP ({CLIP_MODEL_NAME}/{CLIP_PRETRAINED}) ke {DEVICE}...")
        model, _, preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED, device=DEVICE
        )
        model.eval()
        self.clip_model = model
        self.transform = preprocess

    # ------------------------------------------------------------------
    # ALIGNMENT & GEOMETRI
    # ------------------------------------------------------------------
    @staticmethod
    def _order_points(pts):
        pts = pts.reshape(4, 2).astype("float32")
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]        # top-left
        rect[2] = pts[np.argmax(s)]        # bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]     # top-right
        rect[3] = pts[np.argmax(diff)]     # bottom-left
        return rect

    @staticmethod
    def _aspect_ok(rect, tol=0.20):
        (tl, tr, br, bl) = rect
        w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2.0
        h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2.0
        if h == 0:
            return None
        ratio = w / h
        if abs(ratio - CARD_ASPECT_RATIO) / CARD_ASPECT_RATIO < tol:
            return "portrait"
        if abs(ratio - (1.0 / CARD_ASPECT_RATIO)) / (1.0 / CARD_ASPECT_RATIO) < tol:
            return "landscape"
        return None

    def _align_card_image_debug(self, image_np, out_size=(448, 625)):
        h_img, w_img = image_np.shape[:2]
        frame_area = h_img * w_img
        min_area = 0.05 * frame_area
        max_area = 0.92 * frame_area
        border_margin = 2
        max_sides_touch = 3
        solidity_thresh = 0.50
        extent_thresh = 0.80

        try:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            smooth = cv2.bilateralFilter(gray, d=9, sigmaColor=60, sigmaSpace=60)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray_eq = clahe.apply(smooth)
            edges_base = cv2.Canny(gray_eq, 40, 120)

            best = None

            for ksize, iters in [(5, 2), (7, 2), (9, 3), (11, 3), (13, 4)]:
                kernel = np.ones((ksize, ksize), np.uint8)
                edges = cv2.morphologyEx(edges_base, cv2.MORPH_CLOSE, kernel, iterations=iters)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    continue

                candidates = []
                for c in contours:
                    area = cv2.contourArea(c)
                    if area < min_area or area > max_area:
                        continue

                    x, y, w, h = cv2.boundingRect(c)
                    sides_touched = sum([
                        x <= border_margin, y <= border_margin,
                        x + w >= w_img - border_margin, y + h >= h_img - border_margin
                    ])
                    if sides_touched > max_sides_touch:
                        continue

                    hull = cv2.convexHull(c)
                    hull_area = cv2.contourArea(hull)
                    solidity = area / hull_area if hull_area > 0 else 0
                    if solidity < solidity_thresh:
                        continue

                    candidates.append((area, c))

                if not candidates:
                    continue
                candidates.sort(key=lambda t: t[0], reverse=True)

                for area, c in candidates[:5]:
                    peri = cv2.arcLength(c, True)
                    approx = cv2.approxPolyDP(c, 0.02 * peri, True)

                    rect = None
                    if len(approx) == 4 and cv2.isContourConvex(approx):
                        rect = self._order_points(approx)
                        local_status = f"ALIGNED_4PT_k{ksize}"
                    else:
                        hull = cv2.convexHull(c)
                        hull_peri = cv2.arcLength(hull, True)
                        for eps_factor in (0.02, 0.03, 0.05):
                            hull_approx = cv2.approxPolyDP(hull, eps_factor * hull_peri, True)
                            if len(hull_approx) == 4 and cv2.isContourConvex(hull_approx):
                                rect = self._order_points(hull_approx)
                                local_status = f"ALIGNED_HULL4PT_k{ksize}"
                                break

                    if rect is None:
                        min_rect = cv2.minAreaRect(c)
                        (rw, rh) = min_rect[1]
                        rect_area = rw * rh
                        extent = (area / rect_area) if rect_area > 0 else 0
                        if extent < extent_thresh:
                            continue
                        box = cv2.boxPoints(min_rect)
                        rect = self._order_points(box)
                        local_status = f"ALIGNED_MINAREARECT_k{ksize}"

                    orientation = self._aspect_ok(rect)
                    if orientation is None:
                        continue

                    if best is None or area > best[0]:
                        best = (area, rect, local_status, orientation)

            if best is None:
                return image_np, "NO_VALID_CANDIDATE"

            _, rect, local_status, orientation = best
            width, height = out_size

            if orientation == "landscape":
                dst = np.array([
                    [0, 0], [height - 1, 0], [height - 1, width - 1], [0, width - 1]
                ], dtype="float32")
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image_np, M, (height, width))
                local_status += "_LANDSCAPE"
            else:
                dst = np.array([
                    [0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]
                ], dtype="float32")
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image_np, M, (width, height))

            return warped, local_status
        except Exception as e:
            return image_np, f"EXCEPTION:{e}"

    def align_card_image(self, image_np):
        warped, _status = self._align_card_image_debug(image_np)
        return warped

    # ------------------------------------------------------------------
    # FEATURE EXTRACTION (CLIP)
    # ------------------------------------------------------------------
    def _extract_embedding(self, pil_img):
        tensor_img = self.transform(pil_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            feat = self.clip_model.encode_image(tensor_img)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().numpy().astype("float32")

    def _extract_embedding_tta(self, pil_img):
        variants = [pil_img]
        for factor in (0.88, 1.12):
            variants.append(ImageEnhance.Brightness(pil_img).enhance(factor))
        for angle in (-2, 2):
            variants.append(pil_img.rotate(angle, resample=Image.Resampling.BILINEAR))

        feats = [self._extract_embedding(v) for v in variants]
        avg_feat = np.mean(feats, axis=0)
        faiss.normalize_L2(avg_feat)
        return avg_feat

    # ------------------------------------------------------------------
    # 4-WAY SMART AUTO-ORIENTATION (0°, 90°, 180°, 270°)
    # ------------------------------------------------------------------
    def _ensure_best_orientation(self, aligned_bgr):
        """
        Memastikan kartu berada dalam orientasi TEGAK LURUS (portrait normal).
        Mengevaluasi varian rotasi dan memilih arah yang menghasilkan
        kemiripan tertinggi ke database FAISS.
        """
        h, w = aligned_bgr.shape[:2]
        candidates = []

        if w > h:
            # Gambar berformat landscape -> uji putar 90° CW dan 90° CCW
            rot_cw = cv2.rotate(aligned_bgr, cv2.ROTATE_90_CLOCKWISE)
            rot_ccw = cv2.rotate(aligned_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            candidates = [rot_cw, rot_ccw]
        else:
            # Gambar berformat portrait -> uji tegak normal (0°) dan terbalik (180°)
            rot_0 = aligned_bgr
            rot_180 = cv2.rotate(aligned_bgr, cv2.ROTATE_180)
            candidates = [rot_0, rot_180]

            # Kasus kartu landscape di dalam kotak portrait (misal Hoothoot):
            # jika rasio kartu tampak tertekan, siapkan juga varian rotasi 90°
            rot_90 = cv2.resize(cv2.rotate(aligned_bgr, cv2.ROTATE_90_CLOCKWISE), (w, h))
            rot_270 = cv2.resize(cv2.rotate(aligned_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE), (w, h))
            candidates.extend([rot_90, rot_270])

        best_bgr = aligned_bgr
        best_sim = -1.0

        for cand_bgr in candidates:
            cand_pil = Image.fromarray(cv2.cvtColor(cand_bgr, cv2.COLOR_BGR2RGB))
            cand_feat = self._extract_embedding(cand_pil)
            faiss.normalize_L2(cand_feat)
            d, _ = self.index.search(cand_feat, 1)
            sim = float(d[0][0])
            if sim > best_sim:
                best_sim = sim
                best_bgr = cand_bgr

        # Pastikan ukuran akhir presisi portrait (448 x 625)
        if best_bgr.shape[0] != 625 or best_bgr.shape[1] != 448:
            best_bgr = cv2.resize(best_bgr, (448, 625), interpolation=cv2.INTER_AREA)

        return best_bgr

    # ------------------------------------------------------------------
    # CONFIDENCE CALIBRATION
    # ------------------------------------------------------------------
    def _compute_calibrated_confidence(self, sims_pool):
        sims = np.asarray(sims_pool, dtype=np.float64)
        n = len(sims)
        margins = np.zeros(n)
        if n > 1:
            margins[:-1] = sims[:-1] - sims[1:]
            margins[-1] = 0.0
        z = margins / self.confidence_temperature
        probs = 1.0 / (1.0 + np.exp(-z))
        return probs, margins

    @staticmethod
    def _confidence_label(margin):
        if margin >= 0.035:
            return "Tinggi"
        if margin >= 0.010:
            return "Sedang"
        return "Rendah"

    # ------------------------------------------------------------------
    # ORB KEYPOINT VERIFICATION
    # ------------------------------------------------------------------
    def _get_orb(self):
        if self._orb is None:
            self._orb = cv2.ORB_create(nfeatures=500)
        return self._orb

    def _find_reference_image_path(self, card_id):
        for ext in (".jpg", ".jpeg", ".png"):
            p = os.path.join(self.image_dir, f"{card_id}{ext}")
            if os.path.exists(p):
                return p
        return None

    def _orb_match_score(self, query_bgr, card_id, ratio=0.75):
        ref_path = self._find_reference_image_path(card_id)
        if ref_path is None:
            return None
        ref_img = cv2.imread(ref_path)
        if ref_img is None:
            return None

        orb = self._get_orb()
        g1 = cv2.cvtColor(query_bgr, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
        k1, d1 = orb.detectAndCompute(g1, None)
        k2, d2 = orb.detectAndCompute(g2, None)
        if d1 is None or d2 is None or len(k1) < 2 or len(k2) < 2:
            return 0.0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        matches = bf.knnMatch(d1, d2, k=2)
        good = [m for m, n in matches if len(m) == 2 and m[0].distance < ratio * m[1].distance] if isinstance(matches[0], list) and len(matches[0]) == 2 else [m for m, n in matches if m.distance < ratio * n.distance]
        denom = min(len(k1), len(k2))
        return len(good) / denom if denom > 0 else 0.0

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------
    def identify_card(self, image_input, top_k=3, debug=False, debug_save_path=None, auto_align=True):
        t0 = time.time()

        if isinstance(image_input, str):
            image_np = cv2.imread(image_input)
            aligned_bgr = self.align_card_image(image_np) if auto_align else cv2.resize(image_np, (448, 625))
        elif isinstance(image_input, np.ndarray):
            aligned_bgr = self.align_card_image(image_input) if auto_align else cv2.resize(image_input, (448, 625))
        elif isinstance(image_input, Image.Image):
            pil_img_temp = image_input.convert("RGB")
            aligned_bgr = cv2.cvtColor(np.array(pil_img_temp), cv2.COLOR_RGB2BGR)
            if not auto_align:
                aligned_bgr = cv2.resize(aligned_bgr, (448, 625))
        else:
            raise ValueError("Format image_input tidak valid! Gunakan path str, PIL Image, atau np.ndarray.")

        # Lakukan 4-Way Smart Auto-Orientation agar kartu selalu tegak
        aligned_bgr = self._ensure_best_orientation(aligned_bgr)
        pil_img = Image.fromarray(cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB))

        if debug_save_path:
            cv2.imwrite(debug_save_path, aligned_bgr)

        feat = self._extract_embedding_tta(pil_img) if self.use_tta else self._extract_embedding(pil_img)
        faiss.normalize_L2(feat)

        rerank_pool = max(top_k, self.orb_rerank_pool_size) if self.use_orb_rerank else top_k
        pool_k = min(max(rerank_pool, self.calibration_pool_size), self.index.ntotal)

        distances, indices = self.index.search(feat, pool_k)
        sims_pool = distances[0]
        probs, margins = self._compute_calibrated_confidence(sims_pool)

        raw_candidates = []
        n_avail = min(rerank_pool, len(indices[0]))
        for rank in range(n_avail):
            idx = indices[0][rank]
            dist = float(distances[0][rank])
            card_id = self.card_id_map.get(str(idx), "Unknown")
            calibrated_pct = float(probs[rank] * 100)
            margin_r = float(margins[rank])

            entry = {
                "card_id": card_id,
                "raw_similarity_score": dist,
                "calibrated_confidence_pct": calibrated_pct,
                "margin": margin_r,
            }
            if self.use_orb_rerank:
                orb_score = self._orb_match_score(aligned_bgr, card_id)
                entry["orb_verification_score"] = orb_score
                entry["blended_score"] = 0.60 * dist + 0.40 * (orb_score or 0.0)
            else:
                entry["blended_score"] = dist
            raw_candidates.append(entry)

        if self.use_orb_rerank:
            raw_candidates.sort(key=lambda e: e["blended_score"], reverse=True)
            if len(raw_candidates) > 1:
                post_margin = max(raw_candidates[0]["blended_score"] - raw_candidates[1]["blended_score"], 0.0)
                z = post_margin / self.confidence_temperature
                post_conf_pct = 100.0 / (1.0 + np.exp(-z))
                raw_candidates[0]["calibrated_confidence_pct"] = float(post_conf_pct)
                raw_candidates[0]["margin"] = float(post_margin)

        raw_candidates = raw_candidates[:top_k]

        candidates = []
        for rank, entry in enumerate(raw_candidates):
            card_id = entry["card_id"]
            card_info = {
                "rank": rank + 1,
                "card_id": card_id,
                "confidence_percentage": round(entry["calibrated_confidence_pct"], 2),
                "raw_similarity_score": round(entry["raw_similarity_score"], 4),
                "confidence_label": self._confidence_label(entry["margin"]),
            }
            if rank == 0:
                card_info["margin_to_runner_up"] = round(entry["margin"], 4)
            if self.use_orb_rerank:
                orb_score = entry.get("orb_verification_score")
                card_info["orb_verification_score"] = round(orb_score, 3) if orb_score is not None else None

            if self.df_metadata is not None and card_id in self.df_metadata.index:
                meta = self.df_metadata.loc[card_id]
                for col in ["name", "supertype", "subtypes", "types", "hp", "number",
                            "rarity", "artist", "set.id", "set.name", "set.series",
                            "release_year", "effective_market_price", "images.large"]:
                    if col in meta and pd.notna(meta[col]):
                        clean_col = col.replace(".", "_").replace("images_large", "image_url_large")
                        card_info[clean_col] = meta[col]
            candidates.append(card_info)

        t1 = time.time()
        output = {
            "status": "success",
            "execution_time_ms": round((t1 - t0) * 1000, 2),
            "top_match": candidates[0] if candidates else None,
            "candidates": candidates,
        }
        if debug:
            output["debug_similarity_pool"] = [round(float(s), 4) for s in sims_pool]
            output["debug_temperature"] = self.confidence_temperature

        return output
