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

    def auto_detect_color_count(
        self,
        image: np.ndarray,
        max_colors: int = 8,
        white_threshold: int = 240,
    ) -> int:
        """
        اكتشاف تلقائي لعدد الألوان في الصورة.
        يستخدم inertia curve (elbow method) لتحديد K الأمثل.
        
        Returns: العدد المقترح (2-8)
        """
        logger.info("[ColorSeparator] Auto-detecting color count...")
        
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # استثناء الخلفية البيضاء
        _, fg_mask = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY_INV)
        img_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        pixels = img_lab.reshape(-1, 3).astype(np.float32)
        fg_flat = fg_mask.reshape(-1)
        fg_pixels = pixels[fg_flat > 128]
        
        if len(fg_pixels) < 100:
            logger.warning("Too few foreground pixels, defaulting to 2")
            return 2
        
        # Sample للسرعة
        if len(fg_pixels) > 10000:
            indices = np.random.choice(len(fg_pixels), 10000, replace=False)
            fg_pixels = fg_pixels[indices]
        
        # حساب inertia لكل K
        inertias = []
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
        
        for k in range(2, max_colors + 1):
            try:
                _, labels, centers = cv2.kmeans(
                    fg_pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS
                )
                # حساب inertia = مجموع المسافات المربعة من كل نقطة لمركزها
                inertia = 0.0
                for i in range(k):
                    cluster_pts = fg_pixels[labels.flatten() == i]
                    if len(cluster_pts) > 0:
                        inertia += np.sum((cluster_pts - centers[i]) ** 2)
                inertias.append(inertia)
            except Exception:
                inertias.append(float('inf'))
        
        # Elbow method: ابحث عن أكبر انخفاض نسبي
        if len(inertias) < 2:
            return 2
        
        best_k = 2
        best_drop = 0
        for i in range(1, len(inertias)):
            if inertias[i - 1] > 0:
                drop = (inertias[i - 1] - inertias[i]) / inertias[i - 1]
                if drop > best_drop:
                    best_drop = drop
                    best_k = i + 2  # i=0 → K=2
        
        # لو الصورة بسيطة (drop صغير جدًا) → K=2
        if best_drop < 0.15:
            best_k = 2
        
        logger.info(f"[ColorSeparator] Auto-detected {best_k} colors")
        return best_k

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
        auto_detect: bool = False,
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
        if auto_detect:
            num_colors = self.auto_detect_color_count(image, white_threshold=white_threshold)
        
        logger.info(f"[ColorSeparator] Starting: {num_colors} colors, LAB={use_lab}, image={image.shape}")

        # تحويل BGR → RGB
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # إنشاء mask للخلفية البيضاء - استخدم threshold أعلى لتجنب حذف الألوان الفاتحة
        white_threshold = 245  # زيادة من 240 إلى 245 لتجنب حذف الألوان الفاتحة
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

        # تحسين فصل الألوان للصور متعددة الألوان
        # استخدام threshold أعلى لاستبعاد الخلفية البيضاء
        white_threshold = 245  # زيادة من 240 لتجنب حذف الألوان الفاتحة

        # إنشاء mask للخلفية البيضاء مع تحسين
        bg_mask = np.all(clustering_image > white_threshold, axis=2)
        pixels = clustering_image[~bg_mask].reshape(-1, 3)

        # إذا كان عدد البكسلات قليل جداً، نقوم بتقليل الـ threshold
        if len(pixels) < 1000:
            white_threshold = 220
            bg_mask = np.all(clustering_image > white_threshold, axis=2)
            pixels = clustering_image[~bg_mask].reshape(-1, 3)
            logger.info(f"Reduced white threshold to {white_threshold} for better color detection")

        if len(pixels) == 0:
            # صورة بيضاء تماماً - ننشئ لون أسود واحد
            logger.warning("No non-white pixels found, creating single black color")
            centers = np.array([[0, 0, 0]], dtype=np.uint8)
            label_map = np.zeros((h, w), dtype=np.int32)
            bg_mask = np.ones((h, w), dtype=bool)
        else:
            # تحسين K-means للصور متعددة الألوان
            # زيادة عدد التكرارات والمحاولات حسب عدد الألوان
            max_iter = 200 if num_colors <= 4 else 300  # أكثر تكرارات للألوان الكثيرة
            epsilon = 0.1 if num_colors <= 4 else 0.05  # دقة أعلى للألوان الكثيرة
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, max_iter, epsilon)
            flags = cv2.KMEANS_PP_CENTERS  # استخدام PP centers لنتائج أفضل

            attempts = 10 if num_colors <= 4 else 20  # محاولات أكثر للألوان الكثيرة

            compactness, labels, centers = cv2.kmeans(
                pixels.astype(np.float32),
                num_colors,
                None,
                criteria,
                10,  # زيادة عدد المحاولات
                flags
            )

            centers = np.uint8(centers)

        # ════════════════════════════════════════════════════════════
        # CRITICAL FIX: Vectorized label_map building (was Python loop)
        # ════════════════════════════════════════════════════════════
        centers_np = centers.astype(np.float32)  # shape: (K, 3)
        # Pixels: (N, 3) where N = h*w
        # diff: (N, K, 3) via broadcasting
        diff = pixels[:, np.newaxis, :] - centers_np[np.newaxis, :, :]
        dists_sq = np.sum(diff ** 2, axis=2)  # (N, K) — squared distance
        label_map = np.argmin(dists_sq, axis=1).reshape(h, w).astype(np.int32)
        # ════════════════════════════════════════════════════════════

        # ترتيب من الأغمق للأفتح
        brightness = [int(np.mean(cv2.cvtColor(c.astype(np.uint8).reshape(1, 1, 3), cv2.COLOR_RGB2GRAY))) for c in centers]
        sorted_indices = np.argsort(brightness)
        centers = centers[sorted_indices]

        # Remap label_map to match sorted centers
        new_label_map = np.full_like(label_map, -1)
        for new_idx, old_idx in enumerate(sorted_indices):
            new_label_map[label_map == old_idx] = new_idx
        label_map = new_label_map

        # تحديد الخلفية
        if bg_mask is not None:
            label_map[bg_mask > 128] = -1

        colors = [tuple(int(c) for c in center) for center in centers]
        color_names = [f"color_{i+1:02d}" for i in range(num_colors)]

        logger.info(f"[ColorSeparator] Done. Colors: {[self.get_color_hex(c) for c in colors]}")

        # VALIDATION: Check for single color result (causes solid black films) — DISABLED to allow 1 color processing
        # if num_colors <= 1:
        #     logger.error(f"[ColorSeparator] CRITICAL: Only {num_colors} color detected! This will create solid black film.")
        #     logger.error("This usually happens when:")
        #     logger.error("- Image has insufficient contrast")
        #     logger.error("- White background threshold is too low")
        #     logger.error("- K-means clustering failed")
        #     raise ValueError(f"Color separation failed: only {num_colors} color detected. Film would be solid black.")

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

        # ترتيب من الأكثر مساحةً للأقل وإزالة الألوان الفارغة
        info = [x for x in info if x["pixel_count"] > 0]
        info.sort(key=lambda x: x["pixel_count"], reverse=True)
        return info
