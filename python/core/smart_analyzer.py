from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ImageClass(Enum):
    TEXT_LOGO   = "text_logo"    # Text or logo - sharp edges, few colors
    ARTWORK      = "artwork"     # Illustration - limited colors, medium details
    PHOTO        = "photo"       # Photographic image - gradients, many colors
    LOW_QUALITY  = "low_quality" # Low quality image - high noise, low resolution

@dataclass
class SmartResult:
    image_class: ImageClass
    
    # Processing Parameters (auto-filled)
    smoothing_factor: float = 0.1
    corner_threshold: float = 30.0
    global_threshold: int = 127
    use_halftone: bool = False
    lpi: int = 85
    num_colors: int = 0
    use_potrace_style: bool = False
    
    # Diagnostic Info
    edge_density: float = 0.0
    color_count_estimate: int = 0
    noise_level: float = 0.0
    is_low_res: bool = False
    confidence: float = 0.0
    
    # Bimodality & Shape Features
    mid_ratio: float = 0.0
    shape_ratio: float = 0.0
    
    # Weighted Scores (for debugging/auditing)
    score_text: float = 0.0
    score_artwork: float = 0.0
    score_photo: float = 0.0

class SmartAnalyzer:
    def analyze(self, image: np.ndarray, dpi: int = 300) -> SmartResult:
        """
        Analyze image using soft scoring instead of hard thresholds.
        """
        metrics = self._extract_metrics(image, dpi)
        scores = self._score_classes(metrics)
        
        # Winner selection
        classes = [ImageClass.TEXT_LOGO, ImageClass.ARTWORK, ImageClass.PHOTO]
        score_vals = [scores['text'], scores['artwork'], scores['photo']]
        winner_idx = np.argmax(score_vals)
        image_class = classes[winner_idx]
        
        # Confidence = winner - runner_up
        sorted_scores = sorted(score_vals, reverse=True)
        confidence = sorted_scores[0] - sorted_scores[1]
        
        # Phase 24: CRITICAL FIX - Deterministic Weighted Scoring (eliminates flip-flop)
        color_norm = metrics['color_count_estimate'] / 8.0  # -> 0.0 to 1.0

        final_text_score = (
            scores['text'] * 0.5 +
            metrics['edge_density'] * 0.2 +
            (1.0 - color_norm) * 0.05 +
            (1.0 - metrics['mid_ratio']) * 0.15 +
            (1.0 - metrics['gradient_ratio']) * 0.1
        )
        
        final_artwork_score = (
            scores['artwork'] * 0.4 +
            color_norm * 0.05 +
            metrics['mid_ratio'] * 0.2 +
            metrics['gradient_ratio'] * 0.15 +
            metrics['sat_mean'] * 0.1 +
            (1.0 - metrics['edge_density']) * 0.1
        )
        
        final_photo_score = (
            scores['photo'] * 0.4 +
            metrics['gradient_ratio'] * 0.3 +
            metrics['mid_ratio'] * 0.2 +
            color_norm * 0.05 +
            metrics['sat_mean'] * 0.05
        )
        
        # Deterministic decision based on weighted scores
        if final_text_score > 0.65:
            image_class = ImageClass.TEXT_LOGO
            confidence = final_text_score
            logger.info(f"  [SmartAnalyzer] Weighted Score: TEXT_LOGO ({confidence:.3f})")
        elif final_photo_score > 0.60 and metrics['gradient_ratio'] > 0.2:
            image_class = ImageClass.PHOTO
            confidence = final_photo_score
            logger.info(f"  [SmartAnalyzer] Weighted Score: PHOTO ({confidence:.3f})")
        else:
            image_class = ImageClass.ARTWORK
            confidence = max(final_artwork_score, 0.70)
            logger.info(f"  [SmartAnalyzer] Weighted Score: ARTWORK ({confidence:.3f})")

        # Adobe-style hard overrides
        if metrics['gradient_ratio'] > 0.30 and float(confidence) < 0.70:
            image_class = ImageClass.PHOTO
            confidence = max(float(confidence), 0.80)
            logger.info("  [SmartAnalyzer] Override: High gradient_ratio. Forcing PHOTO.")
        else:
            edge_threshold = 0.05 + (0.02 * (1.0 - float(metrics['gradient_ratio'])))
            score_gap_ta = abs(float(scores['text']) - float(scores['artwork']))
            allow_override = score_gap_ta >= 0.05

            if (
                allow_override
                and metrics['color_count_estimate'] <= 2
                and float(metrics['edge_density']) >= edge_threshold
                and float(metrics['mid_ratio']) < 0.10
            ):
                image_class = ImageClass.TEXT_LOGO
                confidence = max(float(confidence), 0.85)
                logger.info(
                    f"  [SmartAnalyzer] Override: 2-color + edge_density>= {edge_threshold:.3f} + low midtones. Forcing TEXT_LOGO."
                )
        
        # Override low quality regardless of scoring
        if metrics["is_low_res"] or metrics["noise_level"] > 2000:
            image_class = ImageClass.LOW_QUALITY
            confidence = 0.5
            
        params = self._get_params(image_class, metrics, max_dim=max(h_orig, w_orig))
        
        result = SmartResult(
            image_class=image_class,
            confidence=float(confidence),
            smoothing_factor=params.get('smoothing_factor', 0.1),
            corner_threshold=params.get('corner_threshold', 30.0),
            global_threshold=params.get('global_threshold', 127),
            use_halftone=params.get('use_halftone', False),
            lpi=params.get('lpi', 85),
            num_colors=params.get('num_colors', 0),
            use_potrace_style=params.get('use_potrace_style', False),
            edge_density=float(metrics['edge_density']),
            color_count_estimate=int(metrics['color_count_estimate']),
            noise_level=float(metrics['noise_level']),
            is_low_res=bool(metrics['is_low_res']),
            mid_ratio=float(metrics['mid_ratio']),
            shape_ratio=float(metrics['shape_ratio']),
            score_text=float(final_text_score),
            score_artwork=float(final_artwork_score),
            score_photo=float(final_photo_score),
        )
        
        logger.info(f"[SmartAnalyzer] Weighted: Text={final_text_score:.3f}, Art={final_artwork_score:.3f}, Photo={final_photo_score:.3f}")
        logger.info(f"[SmartAnalyzer] Final: {image_class.value} ({confidence:.0%} confidence)")
        
        return result
    
    def _soft(self, value, low, high, invert=False):
        """Linear ramp between low and high."""
        t = np.clip((value - low) / (high - low + 1e-6), 0, 1)
        return (1.0 - t) if invert else t

    def _extract_metrics(self, image, dpi):
        """Extract 5 core features for classification."""
        h_orig, w_orig = image.shape[:2]
        analysis_scale = min(1.0, 400.0 / max(h_orig, w_orig))
        img_ana = cv2.resize(image, None, fx=analysis_scale, fy=analysis_scale, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(img_ana, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        total_px = h * w
        
        # 1. Edge Density (Canny)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (total_px + 1e-6)
        
        # 2. Color Count (Quick K-means elbow)
        # ── FIX 3-A: Exclude near-white background pixels from color counting ──
        # Background pixels (very bright, low saturation) bias the K-means toward
        # counting the background as an extra color.
        # We mask them out before the elbow analysis.
        img_small = cv2.resize(img_ana, (100, 100))
        pixels_all = img_small.reshape(-1, 3).astype(np.float32)

        # Background exclusion: pixels brighter than 230 in all channels are likely BG
        brightness = pixels_all.min(axis=1)  # min of BGR = darkest channel
        fg_mask = brightness < 230  # keep non-background pixels
        pixels = pixels_all[fg_mask] if fg_mask.sum() > 50 else pixels_all  # safety fallback

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        inertias = []
        for k in [2, 4, 6, 8]:
            _, _, centers = cv2.kmeans(pixels, k, None, criteria, 1, cv2.KMEANS_PP_CENTERS)
            inertia = np.sum((pixels - centers[_.flatten()])**2)
            inertias.append(inertia)
        
        colors = 8
        for i in range(1, len(inertias)):
            if inertias[i-1] > 0 and (inertias[i-1] - inertias[i]) / inertias[i-1] > 0.25:
                colors = [2, 4, 6, 8][i]
                break
        
        # 3. Mid-tone Ratio (Bimodality)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        mid_ratio = np.sum(hist[85:170]) / (total_px + 1e-6)
        
        # 4. Gradient Ratio (Sobel)
        sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = cv2.magnitude(sobelx, sobely)
        gradient_ratio = np.mean(grad_mag) / 255.0
        
        # 5. Saturation Mean (HSV)
        hsv = cv2.cvtColor(img_ana, cv2.COLOR_BGR2HSV)
        sat_mean = np.mean(hsv[:,:,1]) / 255.0
        
        # Noise & Resolution
        noise_level = cv2.Laplacian(gray, cv2.CV_32F).var()
        is_low_res = (min(h_orig, w_orig) < 150) or (dpi < 50)
        
        # Shape Ratio (Secondary)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_perimeter = sum(cv2.arcLength(c, True) for c in contours)
        shape_ratio = total_perimeter / (total_px + 1e-6)
        
        return {
            "edge_density": edge_density,
            "color_count_estimate": colors,
            "mid_ratio": mid_ratio,
            "gradient_ratio": gradient_ratio,
            "sat_mean": sat_mean,
            "noise_level": noise_level,
            "is_low_res": is_low_res,
            "shape_ratio": shape_ratio
        }

    def _score_classes(self, m: dict) -> dict:
        """Soft scoring using weighted features."""
        f_mid = m["mid_ratio"]
        f_col = m["color_count_estimate"] / 8.0
        f_edge = m["edge_density"]
        f_grad = m["gradient_ratio"]
        f_sat = m["sat_mean"]
        f_noise = m["noise_level"]
        
        # TEXT SCORE
        s_text = (
            self._soft(f_mid, 0.02, 0.15, invert=True) * 0.35 +
            self._soft(f_col, 0.25, 1.0, invert=True) * 0.25 +
            self._soft(f_edge, 0.01, 0.10) * 0.20 +
            self._soft(f_grad, 0.05, 0.20, invert=True) * 0.10 +
            self._soft(f_sat, 0.04, 0.39, invert=True) * 0.05 +
            self._soft(m["shape_ratio"], 0.0005, 0.01) * 0.05
        )
        
        # PHOTO SCORE
        s_photo = (
            self._soft(f_col, 0.5, 2.0) * 0.30 +
            self._soft(f_mid, 0.10, 0.40) * 0.25 +
            self._soft(f_grad, 0.15, 0.50) * 0.20 +
            self._soft(f_sat, 0.16, 0.59) * 0.15 +
            self._soft(f_edge, 0.05, 0.20, invert=True) * 0.10
        )
        
        # ARTWORK SCORE
        s_art = (
            self._soft(f_col, 0.25, 1.25) * 0.30 +
            self._soft(f_noise, 100, 800, invert=True) * 0.25 +
            self._soft(f_mid, 0.05, 0.25) * 0.20 +
            self._soft(f_sat, 0.08, 0.47) * 0.15 +
            self._soft(f_edge, 0.02, 0.15) * 0.10
        )
        
        total = s_text + s_photo + s_art + 1e-6
        return {
            "text": s_text / total,
            "photo": s_photo / total,
            "artwork": s_art / total
        }
    
    def _get_params(self, cls: ImageClass, m: dict, max_dim: int = 0) -> dict:
        """Parameters mapping based on classification AND image size.
        All values are adaptive based on resolution to avoid jagged edges
        on large images and over-smoothing on small ones."""
        base = {"use_potrace_style": False, "use_halftone": False, "lpi": 55, "num_colors": 0}

        # Resolution quality: 0.0 (small < 300px) → 1.0 (large > 4000px)
        res_q = np.clip((max_dim - 300) / (4000 - 300), 0.0, 1.0) if max_dim else 0.5

        if cls == ImageClass.TEXT_LOGO:
            # Small: smooth=0.30, corner=55 | Large: smooth=0.08, corner=35
            smooth = float(np.clip(0.30 - res_q * 0.22, 0.05, 0.35))
            corner = float(np.clip(55.0 - res_q * 25.0, 30.0, 70.0))
            return {**base, "smoothing_factor": smooth, "corner_threshold": corner,
                    "global_threshold": 160, "use_potrace_style": True}

        if cls == ImageClass.ARTWORK:
            # Small: smooth=0.45, corner=130 | Large: smooth=0.20, corner=85
            smooth = float(np.clip(0.45 - res_q * 0.25, 0.15, 0.50))
            corner = float(np.clip(130.0 - res_q * 45.0, 70.0, 145.0))
            return {**base, "smoothing_factor": smooth, "corner_threshold": corner,
                    "global_threshold": 180}

        if cls == ImageClass.PHOTO:
            # Small: smooth=0.55, corner=155 | Large: smooth=0.35, corner=115
            smooth = float(np.clip(0.55 - res_q * 0.20, 0.30, 0.65))
            corner = float(np.clip(155.0 - res_q * 40.0, 100.0, 170.0))
            return {**base, "smoothing_factor": smooth, "corner_threshold": corner,
                    "global_threshold": 200, "use_halftone": True}

        # LOW_QUALITY: extra smoothing to handle noise
        # Small: smooth=0.25, corner=135 | Large: smooth=0.10, corner=100
        smooth = float(np.clip(0.25 - res_q * 0.15, 0.08, 0.30))
        corner = float(np.clip(135.0 - res_q * 35.0, 90.0, 150.0))
        return {**base, "smoothing_factor": smooth, "corner_threshold": corner,
                "global_threshold": 200}

    def get_recommended_lpi(self, image_class: ImageClass, detail_level: str = "medium") -> int:
        lpi_map = {
            ImageClass.TEXT_LOGO:   {"high": 85, "medium": 65, "low": 45},
            ImageClass.ARTWORK:     {"high": 75, "medium": 55, "low": 40},
            ImageClass.PHOTO:       {"high": 85, "medium": 65, "low": 45},
            ImageClass.LOW_QUALITY: {"high": 55, "medium": 45, "low": 35},
        }
        return lpi_map.get(image_class, {}).get(detail_level, 55)
    
    def get_dot_shape(self, image_class: ImageClass) -> str:
        dot_shape_map = {
            ImageClass.TEXT_LOGO:   "square",
            ImageClass.ARTWORK:     "round",
            ImageClass.PHOTO:       "round",
            ImageClass.LOW_QUALITY: "round",
        }
        return dot_shape_map.get(image_class, "round")
