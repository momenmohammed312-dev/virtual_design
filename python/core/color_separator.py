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
        use_lab: bool = True,
    ) -> Dict:
        """
        فصل الصورة إلى num_colors طبقة (محسّن للـ LAB color space).

        Args:
            image: BGR numpy array
            num_colors: عدد الألوان المطلوب (1-10)
            attempts: عدد محاولات K-Means
            max_iter: أقصى عدد تكرارات للتقارب
            epsilon: دقة التقارب
            white_threshold: قيمة البيكسل اللي تعلاه يُعتبَر أبيض
            remove_white_bg: إزالة الخلفية البيضاء من الحسابات
            use_lab: استخدام LAB color space (أفضل للطباعة)

        Returns:
            Dict يحتوي على البيانات المطلوبة
        """
        logger.info(f"[ColorSeparator] Starting: {num_colors} colors, LAB={use_lab}, image={image.shape}")

        # تحويل BGR → RGB
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # إنشاء mask للخلفية البيضاء
        bg_mask = None
        if remove_white_bg:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, bg_mask = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY)

        # تحويل إلى LAB للـ clustering الأفضل
        if use_lab:
            img_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            clustering_image = img_lab
        else:
            clustering_image = img_rgb

        # تحضير البيكسلات
        pixels = clustering_image.reshape(-1, 3).astype(np.float32)

        # استثناء الخلفية البيضاء
        if bg_mask is not None:
            bg_flat = bg_mask.reshape(-1)
            foreground_pixels = pixels[bg_flat < 128]
            if len(foreground_pixels) < num_colors * 10:
                logger.warning("[ColorSeparator] Too few foreground pixels, using all pixels")
                foreground_pixels = pixels
        else:
            foreground_pixels = pixels

        # K-Means clustering
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            max_iter,
            epsilon,
        )

        try:
            _, labels_fg, centers_cluster = cv2.kmeans(
                foreground_pixels,
                num_colors,
                None,
                criteria,
                attempts,
                cv2.KMEANS_PP_CENTERS,
            )
        except cv2.error as e:
            logger.error(f"[ColorSeparator] cv2.kmeans failed: {e}")
            raise RuntimeError(f"Color separation failed: {e}")

        # تحويل centers إلى RGB للعرض والتخزين
        if use_lab:
            centers_lab = np.uint8(centers_cluster)
            # تحويل LAB centers إلى RGB للعرض
            centers_rgb = cv2.cvtColor(centers_lab.reshape(1, -1, 3), cv2.COLOR_LAB2RGB)
            centers = centers_rgb.reshape(-1, 3)
        else:
            centers = np.uint8(centers_cluster)

        # ترتيب من الأغمق للأفتح
        brightness = [int(np.mean(cv2.cvtColor(c.astype(np.uint8).reshape(1, 1, 3), cv2.COLOR_RGB2GRAY))) for c in centers]
        sorted_indices = np.argsort(brightness)
        centers = centers[sorted_indices]
        centers_cluster = centers_cluster[sorted_indices]

        # بناء label_map
        label_map = np.zeros((h, w), dtype=np.int32)
        all_pixels = clustering_image.reshape(-1, 3).astype(np.float32)

        for i in range(len(all_pixels)):
            dists = np.linalg.norm(centers_cluster.astype(np.float32) - all_pixels[i], axis=1)
            label_map.flat[i] = np.argmin(dists)

        # تحديد الخلفية
        if bg_mask is not None:
            label_map[bg_mask > 128] = -1

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
