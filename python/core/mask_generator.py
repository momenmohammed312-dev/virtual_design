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
        grayscale_output: bool = False,
    ) -> List[np.ndarray]:
        """
        توليد قائمة masks — mask لكل لون.

        Args:
            image: الصورة الأصلية (للمرجع)
            separation_result: نتيجة ColorSeparator.separate()
            morph_kernel_size: حجم kernel للـ morphological ops
            min_area: أصغر مساحة (pixels) تُحذَف كـ noise
            apply_cleanup: تطبيق التنظيف المورفولوجي
            grayscale_output: إذا كان True، الـ mask يحتفظ بـ grayscale intensity
                              من الصورة الأصلية (للـ halftone قبل الـ binarization)

        Returns:
            List[np.ndarray]: mask لكل لون
        """
        label_map = separation_result["label_map"]
        num_colors = separation_result["num_colors"]

        logger.info(f"[MaskGenerator] Generating {num_colors} masks (grayscale_output={grayscale_output})")
        masks = []

        # تحويل الصورة الأصلية لـ grayscale إذا احتجناه
        if grayscale_output:
            gray_orig = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        for i in range(num_colors):
            # بناء الـ mask الأساسي
            mask = np.zeros(label_map.shape, dtype=np.uint8)
            
            if grayscale_output:
                # SILK SCREEN OPT: We want "Ink Density".
                # Darkest pixel (0) = 100% ink (255) = Largest Dot.
                # Lightest pixel (255) = 0% ink (0) = Smallest Dot.
                mask[label_map == i] = 255 - gray_orig[label_map == i]
            else:
                # SILK SCREEN STANDARD: design=white (255, transparent), background=black (0, opaque)
                # Set design pixels to white (transparent) and background to black (opaque)
                mask.fill(0)  # All black background (opaque)
                mask[label_map == i] = 255  # Design pixels are white (transparent)

            if apply_cleanup and not grayscale_output:
                # لا نطبق cleanup على الـ grayscale masks لأنه يغير الـ intensities
                mask = self._cleanup_mask(mask, morph_kernel_size, min_area)

            pixel_count = int(np.sum(mask > 0)) if not grayscale_output else int(np.sum(mask > 0))
            logger.info(f"[MaskGenerator] Mask {i+1}/{num_colors}: {pixel_count} pixels")
            masks.append(mask)

        return masks

    def _cleanup_mask(
        self,
        mask: np.ndarray,
        kernel_size: int = 3,
        min_area: int = 20,
    ) -> np.ndarray:
        """
        تنظيف الـ mask من الضوضاء الصغيرة والفراغات.
        min_area=20 لحماية النقاط العربية (dots, hamza) اللي بتوصل 20-80px.
        """
        # 1. Smart smoothing: Super-sampling + blur + threshold for anti-aliased edges
        mask = self._smart_smooth_mask(mask)
        
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        # 2. إزالة النقاط الصغيرة المتناثرة (noise)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 3. سد الفراغات الصغيرة داخل الأشكال
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        # 4. إزالة connected components صغيرة جداً
        if min_area > 0:
            cleaned = self._remove_small_components(cleaned, min_area)

        return cleaned

    def _smart_smooth_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        خوارزمية النعومة الفائقة (Anti-Aliasing Engine)
        تحول أي نص "مشرشر" لخط ناعم جداً كأنه فيكتور.
        
        الخطوات:
        1. تكبير الصورة 3x لزيادة الدقة الرياضية (Super-Sampling)
        2. تنعيم الحواف المشرشرة (Gaussian Blur)
        3. إعادة الكبس (Threshold) عند ليفل عالي لحافة حادة
        4. العودة للحجم الأصلي بدقة عالية
        """
        h, w = mask.shape[:2]
        
        # 1. Super-Sampling: تكبير 3x لزيادة الدقة الرياضية
        big_mask = cv2.resize(mask, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        
        # 2. Gaussian Blur: تنعيم درجات السلم بتاعة البكسلات
        smoothed = cv2.GaussianBlur(big_mask, (5, 5), 0)
        
        # 3. High Threshold: كبس عند 150 لحافة حادة ونظيفة
        _, sharp = cv2.threshold(smoothed, 150, 255, cv2.THRESH_BINARY)
        
        # 4. Area Downscale: العودة للحجم الأصلي مع anti-aliasing طبيعي
        final = cv2.resize(sharp, (w, h), interpolation=cv2.INTER_AREA)
        
        # 5. Final threshold لضمان binary clean
        _, final = cv2.threshold(final, 127, 255, cv2.THRESH_BINARY)
        
        return final

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
        invert: bool = True,
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
