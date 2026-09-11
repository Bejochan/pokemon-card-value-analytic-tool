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
from PIL import Image, ImageEnhance
import faiss

# Configuration Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(MODEL_DIR, "card_embeddings.index")
MAP_PATH = os.path.join(MODEL_DIR, "card_id_map.json")
CSV_PATH = os.path.join(BASE_DIR, "dataset", "pokemon_cards_dataset_cleaned.csv")
IMAGE_DIR = os.path.join(BASE_DIR, "dataset", "compressed_images")  # dipakai untuk ORB re-ranking (opsional)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Rasio standar kartu Pokemon (lebar:tinggi = 63mm:88mm)
CARD_ASPECT_RATIO = 63.0 / 88.0


class CardIdentifier:
    def __init__(self, index_path=INDEX_PATH, map_path=MAP_PATH, csv_path=CSV_PATH,
                 image_dir=IMAGE_DIR, confidence_temperature=0.06,
                 calibration_pool_size=20, use_tta=False, use_orb_rerank=False):
        self.index_path = index_path
        self.map_path = map_path
        self.csv_path = csv_path
        self.image_dir = image_dir

        self.confidence_temperature = max(confidence_temperature, 1e-6)
        self.calibration_pool_size = calibration_pool_size
        self.use_tta = use_tta
        self.use_orb_rerank = use_orb_rerank

        self.index = None
        self.card_id_map = {}
        self.df_metadata = None
        self.feature_extractor = None
        self.transform = None
        self._orb = None  # lazy init, cuma dibuat kalau use_orb_rerank dipakai

        self._load_resources()

    def _load_resources(self):
        if not os.path.exists(self.index_path) or not os.path.exists(self.map_path):
            raise FileNotFoundError(
                "Berkas model FAISS belum dibuat! Silakan jalankan "
                "`python backend/models/build_card_index.py` terlebih dahulu."
            )

        self.index = faiss.read_index(self.index_path)
        with open(self.map_path, "r", encoding="utf-8") as f:
            self.card_id_map = json.load(f)

        if os.path.exists(self.csv_path):
            self.df_metadata = pd.read_csv(self.csv_path).set_index("card_id", drop=False)

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

    # ------------------------------------------------------------------
    # ALIGNMENT — deteksi & luruskan kartu (v2: berlapis & ada fallback)
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
    def _aspect_ok(rect, tol=0.18):
        (tl, tr, br, bl) = rect
        w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2.0
        h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2.0
        if h == 0:
            return False
        ratio = w / h
        return (abs(ratio - CARD_ASPECT_RATIO) / CARD_ASPECT_RATIO < tol) or \
               (abs(ratio - (1.0 / CARD_ASPECT_RATIO)) / (1.0 / CARD_ASPECT_RATIO) < tol)

    def _align_card_image_debug(self, image_np, out_size=(448, 625)):
        status = "NO_CONTOUR"
        try:
            h_img, w_img = image_np.shape[:2]
            frame_area = h_img * w_img
            min_area = 0.05 * frame_area
            max_area = 0.92 * frame_area
            border_margin = 2

            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            smooth = cv2.bilateralFilter(gray, d=9, sigmaColor=60, sigmaSpace=60)

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray_eq = clahe.apply(smooth)

            edges = cv2.Canny(gray_eq, 40, 120)
            kernel = np.ones((5, 5), np.uint8)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return image_np, status

            candidates = []
            for c in contours:
                area = cv2.contourArea(c)
                if area < min_area or area > max_area:
                    continue

                x, y, w, h = cv2.boundingRect(c)
                touches_border = (
                    x <= border_margin or y <= border_margin or
                    x + w >= w_img - border_margin or y + h >= h_img - border_margin
                )
                if touches_border:
                    continue

                hull = cv2.convexHull(c)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                if solidity < 0.85:
                    continue

                candidates.append((area, c))

            if not candidates:
                return image_np, "NO_CARD_LIKE_CONTOUR"

            candidates.sort(key=lambda t: t[0], reverse=True)

            for area, c in candidates[:5]:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)

                if len(approx) == 4 and cv2.isContourConvex(approx):
                    rect = self._order_points(approx)
                    local_status = "ALIGNED_4PT"
                else:
                    min_rect = cv2.minAreaRect(c)
                    (rw, rh) = min_rect[1]
                    rect_area = rw * rh
                    extent = (area / rect_area) if rect_area > 0 else 0
                    if extent < 0.85:
                        continue  # kemungkinan gabungan >1 objek, bukan 1 kartu solid
                    box = cv2.boxPoints(min_rect)
                    rect = self._order_points(box)
                    local_status = "ALIGNED_MINAREARECT"

                if not self._aspect_ok(rect):
                    continue

                width, height = out_size
                dst = np.array([
                    [0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]
                ], dtype="float32")

                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image_np, M, (width, height))
                return warped, local_status

            return image_np, "NO_VALID_ASPECT_CANDIDATE"
        except Exception as e:
            return image_np, f"EXCEPTION:{e}"

    def align_card_image(self, image_np):
        warped, _status = self._align_card_image_debug(image_np)
        return warped

    # ------------------------------------------------------------------
    # FEATURE EXTRACTION
    # ------------------------------------------------------------------
    def _extract_embedding(self, pil_img):
        tensor_img = self.transform(pil_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            feat = self.feature_extractor(tensor_img).cpu().numpy().astype("float32")
        return feat

    def _extract_embedding_tta(self, pil_img):
        variants = [pil_img]
        for factor in (0.85, 1.15):
            variants.append(ImageEnhance.Brightness(pil_img).enhance(factor))
        for angle in (3, -3):
            variants.append(pil_img.rotate(angle, resample=Image.BILINEAR,
                                            fillcolor=(128, 128, 128)))
        feats = [self._extract_embedding(v) for v in variants]
        feat = np.mean(np.vstack(feats), axis=0, keepdims=True).astype("float32")
        return feat

    # ------------------------------------------------------------------
    # CONFIDENCE CALIBRATION
    # ------------------------------------------------------------------
    def _compute_calibrated_confidence(self, sims_pool):
        sims = np.asarray(sims_pool, dtype=np.float64)
        scaled = sims / self.confidence_temperature
        scaled -= scaled.max()
        exp = np.exp(scaled)
        probs = exp / exp.sum()
        margin = float(sims[0] - sims[1]) if len(sims) > 1 else float(sims[0])
        return probs, margin

    @staticmethod
    def _confidence_label(calibrated_pct, margin):
        if calibrated_pct >= 70 and margin >= 0.05:
            return "Tinggi"
        if calibrated_pct >= 35:
            return "Sedang"
        return "Rendah"

    # ------------------------------------------------------------------
    # OPSIONAL: RE-RANKING DENGAN ORB LOCAL FEATURE MATCHING
    # ------------------------------------------------------------------
    def _get_orb(self):
        if self._orb is None:
            self._orb = cv2.ORB_create(nfeatures=500)
        return self._orb

    def _find_reference_image_path(self, card_id):
        if not self.image_dir or not os.path.isdir(self.image_dir):
            return None
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
        good = [m for m, n in matches if m.distance < ratio * n.distance]
        denom = min(len(k1), len(k2))
        return len(good) / denom if denom > 0 else 0.0

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------
    def identify_card(self, image_input, top_k=3, debug=False):
        t0 = time.time()

        if isinstance(image_input, str):
            image_np = cv2.imread(image_input)
            aligned_bgr = self.align_card_image(image_np)
            pil_img = Image.fromarray(cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, np.ndarray):
            aligned_bgr = self.align_card_image(image_input)
            pil_img = Image.fromarray(cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
            aligned_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            raise ValueError("Format image_input tidak valid! Gunakan path str, PIL Image, atau np.ndarray.")

        feat = self._extract_embedding_tta(pil_img) if self.use_tta else self._extract_embedding(pil_img)
        faiss.normalize_L2(feat)

        rerank_pool = max(top_k, 5) if self.use_orb_rerank else top_k
        pool_k = min(max(rerank_pool, self.calibration_pool_size), self.index.ntotal)

        distances, indices = self.index.search(feat, pool_k)
        sims_pool = distances[0]
        probs, margin = self._compute_calibrated_confidence(sims_pool)

        raw_candidates = []
        n_avail = min(rerank_pool, len(indices[0]))
        for rank in range(n_avail):
            idx = indices[0][rank]
            dist = float(distances[0][rank])
            card_id = self.card_id_map.get(str(idx), "Unknown")
            calibrated_pct = float(probs[rank] * 100)

            entry = {
                "card_id": card_id,
                "raw_similarity_score": dist,
                "calibrated_confidence_pct": calibrated_pct,
            }
            if self.use_orb_rerank:
                orb_score = self._orb_match_score(aligned_bgr, card_id)
                entry["orb_verification_score"] = orb_score
                entry["blended_score"] = 0.6 * (calibrated_pct / 100.0) + 0.4 * (orb_score or 0.0)
            else:
                entry["blended_score"] = calibrated_pct / 100.0
            raw_candidates.append(entry)

        raw_candidates.sort(key=lambda e: e["blended_score"], reverse=True)
        raw_candidates = raw_candidates[:top_k]

        candidates = []
        for rank, entry in enumerate(raw_candidates):
            card_id = entry["card_id"]
            card_info = {
                "rank": rank + 1,
                "card_id": card_id,
                "confidence_percentage": round(entry["calibrated_confidence_pct"], 2),
                "raw_similarity_score": round(entry["raw_similarity_score"], 4),
                "confidence_label": self._confidence_label(
                    entry["calibrated_confidence_pct"], margin if rank == 0 else 0.0
                ),
            }
            if rank == 0:
                card_info["margin_to_runner_up"] = round(margin, 4)
            if self.use_orb_rerank:
                orb_score = entry.get("orb_verification_score")
                card_info["orb_verification_score"] = round(orb_score, 3) if orb_score is not None else None

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

        result = {
            "status": "success",
            "execution_time_ms": elapsed_ms,
            "top_match": top_match,
            "candidates": candidates
        }

        if debug:
            result["debug_similarity_pool"] = [round(float(s), 4) for s in sims_pool]
            result["debug_temperature"] = self.confidence_temperature

        return result


# Quick test interface
if __name__ == "__main__":
    print("Testing CardIdentifier engine initialization...")
    identifier = CardIdentifier()
    print("Model 1 CardIdentifier Engine (v2) siap digunakan!")