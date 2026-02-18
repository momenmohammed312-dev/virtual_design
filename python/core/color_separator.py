"""
color_separator.py — Color Separation using K-Means Clustering
Virtual Design Silk Screen Studio
Replaces the empty placeholder that was returning []
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ColorSeparator:
    """
    فصل ألوان الصورة إلى طبقات مستقلة باستخدام K-Means Clustering.
    يستخدم KMEANS_PP_CENTERS لنتائج أفضل من RANDOM_CENTERS.
    """

    def separate(
        self,
        image: np.ndarray,
        num_colors: int = 4,
        attempts: int = 10,
        max_iter: int = 100,
        epsilon: float = 0.2,
        white_threshold: int = 240,
        remove_white_bg: bool = True,
    ) -> Dict:
        """
        فصل الصورة إلى num_colors طبقة.

        Args:
            image: BGR numpy array
            num_colors: عدد الألوان المطلوب (1-10)
            attempts: عدد محاولات K-Means (أكثر = أدق + أبطأ)
            max_iter: أقصى عدد تكرارات للتقارب
            epsilon: دقة التقارب
            white_threshold: قيمة البيكسل اللي تعلاه يُعتبَر أبيض
            remove_white_bg: إزالة الخلفية البيضاء من الحسابات

        Returns:
            Dict يحتوي على:
                - colors: list of RGB tuples
                - color_names: list of strings
                - label_map: 2D array (h x w) قيمة كل بيكسل = رقم اللون
                - image: الصورة الأصلية
                - num_colors: العدد الفعلي للألوان
                - bg_mask: mask الخلفية البيضاء (أو None)
        """
        logger.info(f"[ColorSeparator] Starting: {num_colors} colors, image={image.shape}")

        # تحويل BGR → RGB للعمل
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # إنشاء mask للخلفية البيضاء
        bg_mask = None
        if remove_white_bg:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, bg_mask = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY)

        # تحضير البيكسلات للـ K-Means
        pixels = img_rgb.reshape(-1, 3).astype(np.float32)

        # استثناء الخلفية البيضاء من التحليل
        if bg_mask is not None:
            bg_flat = bg_mask.reshape(-1)
            foreground_pixels = pixels[bg_flat < 128]  # البيكسلات غير البيضاء
            if len(foreground_pixels) < num_colors * 10:
                # صورة بيضاء أو شبه بيضاء — استخدم كل البيكسلات
                logger.warning("[ColorSeparator] Too few foreground pixels, using all pixels")
                foreground_pixels = pixels
        else:
            foreground_pixels = pixels

        # تشغيل K-Means
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            max_iter,
            epsilon,
        )

        try:
            _, labels_fg, centers = cv2.kmeans(
                foreground_pixels,
                num_colors,
                None,
                criteria,
                attempts,
                cv2.KMEANS_PP_CENTERS,  # أفضل من RANDOM_CENTERS
            )
        except cv2.error as e:
            logger.error(f"[ColorSeparator] cv2.kmeans failed: {e}")
            raise RuntimeError(f"Color separation failed: {e}")

        centers = np.uint8(centers)

        # ترتيب الألوان من الأغمق للأفتح (أولوية الطباعة)
        brightness = [int(np.mean(c)) for c in centers]
        sorted_indices = np.argsort(brightness)
        centers = centers[sorted_indices]

        # إعادة بناء الـ label_map الكامل للصورة
        # نحسب label لكل بيكسل من centers
        label_map = np.zeros((h, w), dtype=np.int32)
        all_pixels = img_rgb.reshape(-1, 3).astype(np.float32)

        # حساب أقرب center لكل بيكسل
        centers_f = centers.astype(np.float32)
        for i in range(len(all_pixels)):
            dists = np.linalg.norm(centers_f - all_pixels[i], axis=1)
            label_map.flat[i] = np.argmin(dists)

        # تعيين الخلفية لـ label خاص
        if bg_mask is not None:
            label_map[bg_mask > 128] = -1  # -1 = خلفية

        colors = [tuple(int(c) for c in center) for center in centers]
        color_names = [f"color_{i+1:02d}" for i in range(num_colors)]

        logger.info(f"[ColorSeparator] Done. Colors: {[self.get_color_hex(c) for c in colors]}")

        return {
            "colors": colors,
            "color_names": color_names,
            "label_map": label_map,
            "image": image,
            "num_colors": num_colors,
            "bg_mask": bg_mask,
        }

    def get_color_hex(self, rgb: Tuple) -> str:
        """تحويل RGB tuple لـ HEX string"""
        return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"

    def get_color_info(self, separation_result: Dict) -> List[Dict]:
        """
        إرجاع معلومات تفصيلية عن كل لون للعرض في الـ UI.
        """
        label_map = separation_result["label_map"]
        total_pixels = label_map[label_map >= 0].size  # استثناء الخلفية

        info = []
        for i, (color, name) in enumerate(
            zip(separation_result["colors"], separation_result["color_names"])
        ):
            count = np.sum(label_map == i)
            percentage = (count / total_pixels * 100) if total_pixels > 0 else 0
            info.append(
                {
                    "index": i,
                    "name": name,
                    "rgb": color,
                    "hex": self.get_color_hex(color),
                    "pixel_count": int(count),
                    "percentage": round(percentage, 1),
                }
            )

        # ترتيب من الأكثر مساحةً للأقل
        info.sort(key=lambda x: x["pixel_count"], reverse=True)
        return info
