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
    
    # NEW: Additional diagnostic fields for bimodality detection
    mid_ratio: float        # histogram midtones ratio (85-169)
    shape_ratio: float      # perimeter/area ratio

class SmartAnalyzer:
    def analyze(self, image: np.ndarray, dpi: int = 300) -> AnalysisResult:
        """
        Analyze image and determine optimal processing parameters.
        
        Args:
            image: Input image as numpy array (BGR format)
            dpi: Image DPI for resolution calculations
            
        Returns:
            AnalysisResult with classification and parameters
        """
        metrics = self._extract_metrics(image, dpi)
        image_class = self._classify(metrics)
        params = self._get_params(image_class, metrics)
        
        # Remove confidence from metrics to avoid duplication
        metrics_without_confidence = {k: v for k, v in metrics.items() if k != 'confidence'}
        
        result = AnalysisResult(
            image_class=image_class,
            **params,
            **metrics_without_confidence
        )
        
        logger.info(f"[SmartAnalyzer] Classified as {image_class.value} "
                   f"with {result.confidence:.0%} confidence")
        
        return result
    
    def _extract_metrics(self, image, dpi):
        """Extract image characteristics for classification."""
        # SENIOR REFINE: Downsample for metrics to save memory and speed (Task 2/2)
        # Metrics don't need 2000x2000 resolution. 500px is enough for analysis.
        h_orig, w_orig = image.shape[:2]
        analysis_scale = min(1.0, 500.0 / max(h_orig, w_orig))
        
        if analysis_scale < 1.0:
            img_ana = cv2.resize(image, None, fx=analysis_scale, fy=analysis_scale, interpolation=cv2.INTER_AREA)
        else:
            img_ana = image.copy()

        gray = cv2.cvtColor(img_ana, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # 1. Edge Density (Canny edges / total pixels)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)
        
        # 2. Color Count Estimate (K-means quick pass)
        img_small = cv2.resize(img_ana, (150, 150))
        pixels = img_small.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        inertias = []
        
        for k in [2, 4, 6, 8]:
            try:
                _, _, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
                # Ensure we have centers before calculating inertia
                if _ is not None:
                    inertia = np.sum((pixels - centers[_.flatten()]) ** 2)
                    inertias.append(inertia)
                else:
                    inertias.append(float('inf'))
            except:
                inertias.append(float('inf'))
        
        # Elbow method: أول drop > 25% يعني الصورة بسيطة
        color_count_estimate = 8
        for i in range(1, len(inertias)):
            if inertias[i-1] > 0 and (inertias[i-1] - inertias[i]) / inertias[i-1] > 0.25:
                color_count_estimate = [2, 4, 6, 8][i]
                break
        
        # 3. Noise Level (Laplacian variance)
        # SENIOR REFINE: Use float32 (CV_32F) instead of float64 (CV_64F) to halve memory
        lap = cv2.Laplacian(gray, cv2.CV_32F)
        noise_level = lap.var()
        
        # 4. Low Resolution Check
        min_dim = min(h_orig, w_orig)
        is_low_res = (min_dim < 150) or (dpi < 50)
        
        # 5. Mid-tone ratio (bimodality)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total_pixels = h * w
        mid_pixels = np.sum(hist[85:170])  # mid-tone band
        mid_ratio = mid_pixels / (total_pixels + 1e-6)
        
        # 6. Shape ratio (perimeter-based)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_perimeter = sum(cv2.arcLength(c, True) for c in contours)
        shape_ratio = total_perimeter / (h * w + 1e-6)
        
        # Clean up
        del gray, edges, img_small, pixels, lap
        
        return {
            "edge_density": round(edge_density, 4),
            "color_count_estimate": color_count_estimate,
            "noise_level": round(noise_level, 2),
            "is_low_res": is_low_res,
            "mid_ratio": round(mid_ratio, 4),
            "shape_ratio": round(shape_ratio, 4),
            "confidence": 0.0,
        }
    
    def _classify(self, m: dict) -> ImageClass:
        """Classify image based on extracted metrics."""
        edge_d = m["edge_density"]
        colors = m["color_count_estimate"]
        noise  = m["noise_level"]
        mid_ratio = m.get("mid_ratio", 0.5)
        shape_ratio = m.get("shape_ratio", 0.0)
        
        # Low quality detection
        if m["is_low_res"] or noise > 2000:
            return ImageClass.LOW_QUALITY
        
        # Level 1 — PRIMARY TEXT_LOGO signal: bimodality (filled silhouettes)
        # Low midtones = bimodal histogram = logo/text on clean background
        # This catches Puma-style logos (edge_density too low for old check)
        if mid_ratio < 0.05 and colors <= 6:
            return ImageClass.TEXT_LOGO
        
        # Level 2 — SECONDARY TEXT_LOGO signal: shape-based
        # Perimeter ratio detects filled shapes even with low edge density
        if shape_ratio > 0.001 and colors <= 4:
            return ImageClass.TEXT_LOGO
        
        # Level 3 — TERTIARY TEXT_LOGO signal (old logic, preserved for compatibility)
        # High edge density + few colors = vector-like design
        if edge_d > 0.08 and colors <= 4:
            return ImageClass.TEXT_LOGO
        
        # Artwork detection: ألوان محدودة، ناعم
        if colors <= 6 and noise < 500:
            return ImageClass.ARTWORK
        
        # Default to photo for everything else
        return ImageClass.PHOTO
    
    def _get_params(self, cls: ImageClass, m: dict) -> dict:
        """Get optimal processing parameters for each image class."""
        base_params = {
            "use_potrace_style": False,
            "use_halftone": False,
            "lpi": 55,
            "num_colors": 0,  # auto-detect
        }
        
        if cls == ImageClass.TEXT_LOGO:
            return {
                **base_params,
                "smoothing_factor": 0.0,     # لا smoothing — حواف حادة
                "corner_threshold": 20.0,    # يحافظ على كل الزوايا
                "global_threshold": 160,
                "use_potrace_style": True,   # Bezier بدون تنعيم
                "use_halftone": False,
                "confidence": 0.9,
            }
        
        if cls == ImageClass.ARTWORK:
            return {
                **base_params,
                "smoothing_factor": 0.20,    # Changed from 0.15 to ensure upscale path
                "corner_threshold": 45.0,
                "global_threshold": 180,
                "use_halftone": False,
                "confidence": 0.8,
            }
        
        if cls == ImageClass.PHOTO:
            return {
                **base_params,
                "smoothing_factor": 0.25,
                "corner_threshold": 60.0,
                "global_threshold": 200,
                "use_halftone": True,
                "lpi": 55,
                "confidence": 0.85,
            }
        
        # LOW_QUALITY — preprocess أولاً ثم يعيد التصنيف
        return {
            **base_params,
            "smoothing_factor": 0.20,
            "corner_threshold": 45.0,
            "global_threshold": 200,
            "use_halftone": False,
            "confidence": 0.5,
        }
    
    def get_recommended_lpi(self, image_class: ImageClass, detail_level: str = "medium") -> int:
        """Get recommended LPI based on image class and detail level."""
        lpi_map = {
            ImageClass.TEXT_LOGO: {"high": 85, "medium": 65, "low": 45},
            ImageClass.ARTWORK:   {"high": 75, "medium": 55, "low": 40},
            ImageClass.PHOTO:     {"high": 85, "medium": 65, "low": 45},
            ImageClass.LOW_QUALITY: {"high": 55, "medium": 45, "low": 35},
        }
        return lpi_map.get(image_class, {}).get(detail_level, 55)
    
    def get_dot_shape(self, image_class: ImageClass) -> str:
        """Get recommended dot shape for halftone."""
        dot_shape_map = {
            ImageClass.TEXT_LOGO: "square",   # تفاصيل حادة
            ImageClass.ARTWORK:   "round",    # طبيعي
            ImageClass.PHOTO:     "round",    # صور
            ImageClass.LOW_QUALITY: "round",  # default
        }
        return dot_shape_map.get(image_class, "round")
