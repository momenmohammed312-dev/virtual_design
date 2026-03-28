import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ImageClass(Enum):
    TEXT_LOGO   = "text_logo"    # نص أو لوجو — حواف حادة، ألوان قليلة
    ARTWORK      = "artwork"     # رسمة / illustration — ألوان محدودة، تفاصيل متوسطة  
    PHOTO        = "photo"       # صورة فوتوغرافية — gradients، ألوان كثيرة
    LOW_QUALITY  = "low_quality" # صورة مضروبة — noise عالي، دقة منخفضة

@dataclass
class AnalysisResult:
    image_class: ImageClass
    
    # Processing Parameters (auto-filled)
    smoothing_factor: float
    corner_threshold: float
    global_threshold: int
    use_halftone: bool
    lpi: int
    num_colors: int          # 0 = auto-detect
    use_potrace_style: bool  # sharp vectorization
    
    # Diagnostic Info
    edge_density: float
    color_count_estimate: int
    noise_level: float
    is_low_res: bool
    confidence: float        # 0.0 - 1.0
    
    # Bimodality & Shape Features
    mid_ratio: float        # histogram midtones ratio (85-169)
    shape_ratio: float      # perimeter/area ratio
    
    # NEW Scores (V2)
    score_text: float
    score_artwork: float
    score_photo: float

class SmartAnalyzer:
    def analyze(self, image: np.ndarray, dpi: int = 300) -> AnalysisResult:
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
        
        # Phase 24: Senior Confidence Gate & Rule Overrides
        # 1. Force TEXT_LOGO if it's clearly a high-contrast 2-color (1 ink + 1 bg) image
        if metrics["color_count_estimate"] <= 2 and scores['text'] > 0.4:
            logger.info("  [SmartAnalyzer] Rule: Low color count detected. Forcing TEXT_LOGO.")
            image_class = ImageClass.TEXT_LOGO
            confidence = 0.95
            
        # 2. If we are < 70% confident in text_logo, default to artwork
        # This prevents aggressive binarization on fuzzy/complex images.
        elif image_class == ImageClass.TEXT_LOGO and confidence < 0.70:
            logger.warning(f"  [SmartAnalyzer] Unstable confidence ({confidence:.1%}) for text_logo. Falling back to ARTWORK.")
            image_class = ImageClass.ARTWORK
            confidence = 0.7
            
        # Low quality override
        if metrics["is_low_res"] or metrics["noise_level"] > 2000:
            image_class = ImageClass.LOW_QUALITY
            confidence = 0.5

            
        params = self._get_params(image_class, metrics)
        
        # Merge all into result
        result = AnalysisResult(
            image_class=image_class,
            confidence=round(float(confidence), 3),
            score_text=round(scores['text'], 3),
            score_artwork=round(scores['artwork'], 3),
            score_photo=round(scores['photo'], 3),
            is_low_res=metrics["is_low_res"], # Explicitly pass is_low_res
            **params,
            **{k: v for k, v in metrics.items() if k not in ['is_low_res'] and k in AnalysisResult.__annotations__}
        )

        
        logger.info(f"[SmartAnalyzer] V2 Score: Text={result.score_text:.2f}, Art={result.score_artwork:.2f}, Photo={result.score_photo:.2f}")
        logger.info(f"[SmartAnalyzer] Final: {image_class.value} ({result.confidence:.0%} confidence)")
        
        return result
    
    def _soft(self, value, low, high, invert=False):
        """Linear ramp between low and high."""
        t = np.clip((value - low) / (high - low + 1e-6), 0, 1)
        return (1.0 - t) if invert else t

    def _extract_metrics(self, image, dpi):
        """Extract 5 core features for classification."""
        # Downsample for analysis speed and stability
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
        img_small = cv2.resize(img_ana, (100, 100))
        pixels = img_small.reshape(-1, 3).astype(np.float32)
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
        
        # 4. Gradient Ratio (Sobel) - High for photos, low for flat logos
        sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = cv2.magnitude(sobelx, sobely)
        gradient_ratio = np.mean(grad_mag) / 255.0
        
        # 5. Saturation Mean (HSV) - High for art/photos, low for BW logos
        hsv = cv2.cvtColor(img_ana, cv2.COLOR_BGR2HSV)
        sat_mean = np.mean(hsv[:,:,1])
        
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
        # Normalize features
        f_mid = m["mid_ratio"]
        f_col = m["color_count_estimate"]
        f_edge = m["edge_density"]
        f_grad = m["gradient_ratio"]
        f_sat = m["sat_mean"]
        f_noise = m["noise_level"]
        
        # TEXT SCORE
        # Low midtones (bimodal), few colors, high edge density relative to gradient complexity
        s_text = (
            self._soft(f_mid, 0.02, 0.15, invert=True) * 0.35 +
            self._soft(f_col, 2, 8, invert=True) * 0.25 +
            self._soft(f_edge, 0.01, 0.10) * 0.20 +
            self._soft(f_grad, 0.05, 0.20, invert=True) * 0.10 +
            self._soft(f_sat, 10, 100, invert=True) * 0.05 +
            self._soft(m["shape_ratio"], 0.0005, 0.01) * 0.05
        )
        
        # PHOTO SCORE
        # High midtones, many colors, high gradients, high saturation
        s_photo = (
            self._soft(f_col, 4, 16) * 0.30 +
            self._soft(f_mid, 0.10, 0.40) * 0.25 +
            self._soft(f_grad, 0.15, 0.50) * 0.20 +
            self._soft(f_sat, 40, 150) * 0.15 +
            self._soft(f_edge, 0.05, 0.20, invert=True) * 0.10
        )
        
        # ARTWORK SCORE
        # Mid-range colors, low noise, moderate gradients
        s_art = (
            self._soft(f_col, 2, 10) * 0.30 +
            self._soft(f_noise, 100, 800, invert=True) * 0.25 +
            self._soft(f_mid, 0.05, 0.25) * 0.20 +
            self._soft(f_sat, 20, 120) * 0.15 +
            self._soft(f_edge, 0.02, 0.15) * 0.10
        )
        
        total = s_text + s_photo + s_art + 1e-6
        return {
            "text": s_text / total,
            "photo": s_photo / total,
            "artwork": s_art / total
        }
    
    def _get_params(self, cls: ImageClass, m: dict) -> dict:
        """Parameters mapping based on classification."""
        base = {"use_potrace_style": False, "use_halftone": False, "lpi": 55, "num_colors": 0}
        
        if cls == ImageClass.TEXT_LOGO:
            # Phase 25: Senior Sharpening (High Fidelity)
            return {**base, "smoothing_factor": 0.0, "corner_threshold": 10.0, "global_threshold": 160, "use_potrace_style": True}
        if cls == ImageClass.ARTWORK:
            # Conservative smoothing to prevent "melting" details
            return {**base, "smoothing_factor": 0.10, "corner_threshold": 30.0, "global_threshold": 180}
        if cls == ImageClass.PHOTO:
            return {**base, "smoothing_factor": 0.25, "corner_threshold": 45.0, "global_threshold": 200, "use_halftone": True}
        
        return {**base, "smoothing_factor": 0.10, "corner_threshold": 30.0, "global_threshold": 200}



    def get_recommended_lpi(self, image_class: ImageClass, detail_level: str = "medium") -> int:
        lpi_map = {
            ImageClass.TEXT_LOGO: {"high": 85, "medium": 65, "low": 45},
            ImageClass.ARTWORK:   {"high": 75, "medium": 55, "low": 40},
            ImageClass.PHOTO:     {"high": 85, "medium": 65, "low": 45},
            ImageClass.LOW_QUALITY: {"high": 55, "medium": 45, "low": 35},
        }
        return lpi_map.get(image_class, {}).get(detail_level, 55)
    
    def get_dot_shape(self, image_class: ImageClass) -> str:
        dot_shape_map = {
            ImageClass.TEXT_LOGO: "square",
            ImageClass.ARTWORK:   "round",
            ImageClass.PHOTO:     "round",
            ImageClass.LOW_QUALITY: "round",
        }
        return dot_shape_map.get(image_class, "round")
