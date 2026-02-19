"""
mask_generator.py — Binary Mask Generator for each color layer
Virtual Design Silk Screen Studio
Replaces the empty placeholder that was returning None
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MaskGenerator:
    """
    يولّد binary mask (أبيض وأسود) لكل لون من نتيجة ColorSeparator.
    يطبق morphological operations لتنظيف الـ masks.
    """

    def generate_masks(
        self,
        image: np.ndarray,
        separation_result: Dict,
        morph_kernel_size: int = 3,
        min_area: int = 50,
        apply_cleanup: bool = True,
    ) -> List[np.ndarray]:
        """
        توليد قائمة masks — mask لكل لون.

        Args:
            image: الصورة الأصلية (للمرجع)
            separation_result: نتيجة ColorSeparator.separate()
            morph_kernel_size: حجم kernel للـ morphological ops
            min_area: أصغر مساحة (pixels) تُحذَف كـ noise
            apply_cleanup: تطبيق التنظيف المورفولوجي

        Returns:
            List[np.ndarray]: mask أبيض/أسود لكل لون (255=هذا اللون, 0=لأ)
        """
        label_map = separation_result["label_map"]
        num_colors = separation_result["num_colors"]

        logger.info(f"[MaskGenerator] Generating {num_colors} masks")
        masks = []

        for i in range(num_colors):
            # بناء الـ mask الأساسي
            mask = np.zeros(label_map.shape, dtype=np.uint8)
            mask[label_map == i] = 255

            if apply_cleanup:
                mask = self._cleanup_mask(mask, morph_kernel_size, min_area)

            pixel_count = int(np.sum(mask > 0))
            logger.info(f"[MaskGenerator] Mask {i+1}/{num_colors}: {pixel_count} pixels")
            masks.append(mask)

        return masks

    def _cleanup_mask(
        self,
        mask: np.ndarray,
        kernel_size: int = 3,
        min_area: int = 50,
    ) -> np.ndarray:
        """
        تنظيف الـ mask من الضوضاء الصغيرة والفراغات.
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        # إزالة النقاط الصغيرة المتناثرة (noise)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # سد الفراغات الصغيرة داخل الأشكال
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        # إزالة connected components صغيرة جداً
        if min_area > 0:
            cleaned = self._remove_small_components(cleaned, min_area)

        return cleaned

    def _remove_small_components(
        self, mask: np.ndarray, min_area: int
    ) -> np.ndarray:
        """إزالة المكونات المتصلة الأصغر من min_area pixels."""
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        result = np.zeros_like(mask)
        for label_idx in range(1, num_labels):  # 0 = background
            area = stats[label_idx, cv2.CC_STAT_AREA]
            if area >= min_area:
                result[labels == label_idx] = 255
        return result

    def generate_film_image(
        self,
        mask: np.ndarray,
        invert: bool = False,
        add_border: bool = True,
        border_px: int = 20,
    ) -> np.ndarray:
        """
        تحويل الـ mask لصورة فيلم جاهزة للطباعة.

        Args:
            mask: binary mask
            invert: عكس الألوان (أسود على أبيض أو أبيض على أسود)
            add_border: إضافة حدود بيضاء حول الصورة
            border_px: عرض الحدود بالـ pixels

        Returns:
            np.ndarray: صورة الفيلم النهائية
        """
        film = mask.copy()

        if invert:
            film = cv2.bitwise_not(film)

        if add_border:
            film = cv2.copyMakeBorder(
                film, border_px, border_px, border_px, border_px,
                cv2.BORDER_CONSTANT, value=255,
            )

        # تحويل لـ RGB للتصدير
        film_rgb = cv2.cvtColor(film, cv2.COLOR_GRAY2RGB)
        return film_rgb

    def generate_combined_preview(
        self,
        masks: List[np.ndarray],
        colors: List,
        background_color: tuple = (255, 255, 255),
    ) -> np.ndarray:
        """
        Preview ملوّن يجمع جميع الـ masks بألوانها الأصلية.
        مفيد للعرض في الـ UI.
        """
        if not masks:
            return np.zeros((100, 100, 3), dtype=np.uint8)

        h, w = masks[0].shape
        preview = np.full((h, w, 3), background_color, dtype=np.uint8)

        for mask, color in zip(masks, colors):
            # تطبيق اللون — color هو RGB tuple
            bgr = (color[2], color[1], color[0])  # RGB → BGR
            preview[mask > 0] = bgr

        return preview

    def get_mask_stats(self, masks: List[np.ndarray]) -> List[Dict]:
        """إحصاءات تفصيلية لكل mask — مفيدة للـ validation."""
        total_pixels = masks[0].size if masks else 1
        stats = []
        for i, mask in enumerate(masks):
            filled = int(np.sum(mask > 0))
            stats.append(
                {
                    "index": i,
                    "filled_pixels": filled,
                    "coverage_percent": round(filled / total_pixels * 100, 2),
                    "is_empty": filled == 0,
                }
            )
        return stats
