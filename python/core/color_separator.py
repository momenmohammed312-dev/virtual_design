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
            
        # 1. Quick Grayscale check: If image is pure BW/Grayscale, it only needs 1 ink + 1 bg
        b, g, r = cv2.split(image)
        # Check if max difference between channels is extremely small
        diff_bg = cv2.absdiff(b, g)
        diff_gr = cv2.absdiff(g, r)
        if np.max(diff_bg) <= 5 and np.max(diff_gr) <= 5:
            logger.info("[ColorSeparator] Image is effectively grayscale/B&W. Auto-detecting 2 colors.")
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

        # تحويل إلى LAB للـ clustering الأفضل
        if use_lab:
            img_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            clustering_image = img_lab
        else:
            clustering_image = img_rgb

        # --- Senior Phase 17: Optional Global Quantization ---
        # This simplifies the image to num_colors * 2 flat colors to remove noise/gradients
        # before the final separation for a cleaner "Silk Screen" effect.
        if num_colors > 0:
            logger.info(f"[ColorSeparator] Applying global quantization (K={num_colors*2}) to remove noise")
            Z = clustering_image.reshape((-1, 3)).astype(np.float32)
            k_quant = min(num_colors * 2, 16) # Don't over-quantize
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, q_labels, q_centers = cv2.kmeans(Z, k_quant, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            q_centers = np.uint8(q_centers)
            quantized = q_centers[q_labels.flatten()].reshape(clustering_image.shape)
            clustering_image = quantized

        # Smart background detection: Priority to provided white_threshold
        # but with Otsu-based safety check (Senior Phase 15)
        gray_for_bg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        otsu_ret, _ = cv2.threshold(gray_for_bg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # If user provided a specific threshold != 240, use it. 
        # Otherwise, calculate auto_bg_thresh using Otsu.
        if white_threshold != 240:
            auto_bg_thresh = white_threshold
            logger.info(f"[ColorSeparator] Using user-provided white_threshold: {auto_bg_thresh}")
        else:
            auto_bg_thresh = max(int(otsu_ret), 150) if otsu_ret > 100 else 220
            logger.info(f"[ColorSeparator] Auto background threshold: {auto_bg_thresh} (Otsu={otsu_ret:.0f})")
        
        # bg_mask must be 2D (h, w) boolean — use grayscale threshold
        bg_mask_2d = gray_for_bg > auto_bg_thresh  # True = background
        foreground_pixels = clustering_image[~bg_mask_2d].reshape(-1, 3)

        # Fallback if too few pixels detected
        if len(foreground_pixels) < 1000:
            bg_mask_2d = gray_for_bg > 200
            foreground_pixels = clustering_image[~bg_mask_2d].reshape(-1, 3)
            logger.info("Fallback: reduced threshold to 200 for better color detection")
        
        bg_mask = bg_mask_2d

        if len(foreground_pixels) == 0:
            # صورة بيضاء تماماً - ننشئ لون أسود واحد
            logger.warning("No non-white pixels found, creating single black color")
            centers = np.array([[0, 0, 0]], dtype=np.uint8)
            label_map = np.zeros((h, w), dtype=np.int32)
            bg_mask = np.ones((h, w), dtype=bool)
        else:
            # تحسين K-means للصور متعددة الألوان
            max_iter = 200 if num_colors <= 4 else 300
            epsilon = 0.1 if num_colors <= 4 else 0.05
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, max_iter, epsilon)
            flags = cv2.KMEANS_PP_CENTERS

            attempts = 10 if num_colors <= 4 else 20

            compactness, labels, centers = cv2.kmeans(
                foreground_pixels.astype(np.float32),
                num_colors,
                None,
                criteria,
                10,
                flags
            )

            centers = np.uint8(centers)

        # ════════════════════════════════════════════════════════════
        # CRITICAL FIX (Phase 16): Vectorized label_map building on ALL pixels
        # Build on full image (h*w) not just foreground pixels to avoid Reshape error
        # ════════════════════════════════════════════════════════════
        centers_np = centers.astype(np.float32)  # shape: (K, 3)
        all_pixels = clustering_image.reshape(-1, 3).astype(np.float32)  # all h*w pixels
        diff = all_pixels[:, np.newaxis, :] - centers_np[np.newaxis, :, :]
        dists_sq = np.sum(diff ** 2, axis=2)  # (N, K)
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
            label_map[bg_mask] = -1

        colors = [tuple(int(c) for c in center) for center in centers]
        # Convert back to RGB for output if we used LAB
        if use_lab:
            colors_rgb = []
            for c in centers:
                rgb = cv2.cvtColor(np.uint8([[c]]), cv2.COLOR_LAB2RGB)[0][0]
                colors_rgb.append(tuple(int(x) for x in rgb))
            colors = colors_rgb

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

        # ترتيب من الأكثر مساحةً للأقل وإزالة الألوان الفارغة
        info = [x for x in info if x["pixel_count"] > 0]
        info.sort(key=lambda x: x["pixel_count"], reverse=True)
        return info
