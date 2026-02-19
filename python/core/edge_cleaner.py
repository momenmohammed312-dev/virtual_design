"""
edge_cleaner.py — Edge Cleaning with Morphological Operations
Virtual Design Silk Screen Studio
Fixes the placeholder that was returning mask unchanged
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EdgeCleaner:
    """
    تنظيف حواف الـ masks باستخدام morphological operations وGaussian smoothing.
    يُحسّن جودة الطباعة بإزالة الحواف المتعرجة والضوضاء الدقيقة.
    """

    def clean(
        self,
        mask: np.ndarray,
        kernel_size: int = 3,
        smooth: bool = True,
        smooth_sigma: float = 0.8,
        iterations: int = 1,
    ) -> np.ndarray:
        """
        تنظيف حواف الـ mask.

        Args:
            mask: binary mask (0 و 255)
            kernel_size: حجم kernel المورفولوجي
            smooth: تطبيق Gaussian smoothing على الحواف
            smooth_sigma: قوة الـ smoothing (أكبر = أنعم أكثر)
            iterations: عدد مرات تطبيق العملية

        Returns:
            np.ndarray: mask مع حواف نظيفة
        """
        logger.debug(f"[EdgeCleaner] Cleaning mask {mask.shape}, kernel={kernel_size}")

        result = mask.copy()

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        for _ in range(iterations):
            # 1. إزالة النقاط الصغيرة خارج الشكل (speckles)
            result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)

            # 2. سد الفراغات الصغيرة داخل الشكل (holes)
            result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)

        if smooth:
            # 3. Gaussian blur لتنعيم الحواف المتعرجة
            ksize = kernel_size * 2 + 1  # يجب أن يكون فردي
            result = cv2.GaussianBlur(result, (ksize, ksize), smooth_sigma)

            # 4. إعادة threshold بعد الـ blur
            _, result = cv2.threshold(result, 127, 255, cv2.THRESH_BINARY)

        return result

    def clean_all(
        self,
        masks: list,
        kernel_size: int = 3,
        smooth: bool = True,
    ) -> list:
        """تنظيف قائمة من الـ masks دفعة واحدة."""
        logger.info(f"[EdgeCleaner] Cleaning {len(masks)} masks")
        return [self.clean(m, kernel_size, smooth) for m in masks]

    def anti_alias_edges(self, mask: np.ndarray, radius: int = 1) -> np.ndarray:
        """
        Anti-aliasing للحواف — مفيد للـ halftone printing.
        يُنعّم الحواف بدرجات رمادية بدل الحافة الحادة.
        """
        blurred = cv2.GaussianBlur(mask, (radius * 4 + 1, radius * 4 + 1), radius)
        return blurred

    def expand_edges(self, mask: np.ndarray, pixels: int = 1) -> np.ndarray:
        """
        توسيع الحواف بـ pixels — مفيد لتجنب gaps بين الألوان عند الطباعة.
        """
        kernel = np.ones((pixels * 2 + 1, pixels * 2 + 1), np.uint8)
        return cv2.dilate(mask, kernel, iterations=1)

    def shrink_edges(self, mask: np.ndarray, pixels: int = 1) -> np.ndarray:
        """
        تقليص الحواف بـ pixels — يُجنّب تداخل الألوان.
        """
        kernel = np.ones((pixels * 2 + 1, pixels * 2 + 1), np.uint8)
        return cv2.erode(mask, kernel, iterations=1)
