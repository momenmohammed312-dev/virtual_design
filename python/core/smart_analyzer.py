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
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # 1. Edge Density (Canny edges / total pixels)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)
        
        # 2. Color Count Estimate (K-means quick pass)
        img_small = cv2.resize(image, (150, 150))
        pixels = img_small.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        inertias = []
        
        for k in [2, 4, 6, 8]:
            try:
                _, _, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
                inertia = np.sum((pixels - centers[_.flatten()]) ** 2)
                inertias.append(inertia)
            except:
                inertias.append(float('inf'))
        
        # Elbow method: أول drop > 25% يعني الصورة بسيطة
        color_count_estimate = 8
        for i in range(1, len(inertias)):
            if inertias[i-1] > 0 and (inertias[i-1] - inertias[i]) / inertias[i-1] > 0.25:
                color_count_estimate = [2, 4, 6, 8][i]
                break
        
        # 3. Noise Level (Laplacian variance)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        noise_level = lap.var()
        
        # 4. Low Resolution Check
        min_dim = min(h, w)
        is_low_res = (min_dim < 300) or (dpi < 72)
        
        return {
            "edge_density": round(edge_density, 4),
            "color_count_estimate": color_count_estimate,
            "noise_level": round(noise_level, 2),
            "is_low_res": is_low_res,
            "confidence": 0.0,  # Will be set in _get_params
        }
    
    def _classify(self, m: dict) -> ImageClass:
        """Classify image based on extracted metrics."""
        edge_d = m["edge_density"]
        colors = m["color_count_estimate"]
        noise  = m["noise_level"]
        
        # Low quality detection
        if m["is_low_res"] or noise > 2000:
            return ImageClass.LOW_QUALITY
        
        # Text/Logo detection: حواف كثيرة + ألوان قليلة
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
                "smoothing_factor": 0.15,
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
