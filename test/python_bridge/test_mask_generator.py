"""
test_mask_generator.py — Unit Tests for MaskGenerator
Virtual Design Silk Screen Studio

Run with: python -m pytest python/tests/test_mask_generator.py -v
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import cv2
    from core.color_separator import ColorSeparator
    from core.mask_generator import MaskGenerator
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


@unittest.skipUnless(HAS_OPENCV, "opencv-python not installed")
class TestMaskGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = MaskGenerator()
        self.separator = ColorSeparator()

    # ─── Helper ───────────────────────────────────────────────────────────

    def _make_two_color_separation(self, size=(100, 100)):
        """نتيجة separation جاهزة للاختبار"""
        img = np.zeros((*size, 3), dtype=np.uint8)
        half = size[1] // 2
        img[:, :half] = (0, 0, 255)    # أحمر
        img[:, half:] = (255, 0, 0)    # أزرق
        return img, self.separator.separate(img, num_colors=2)

    def _make_solid_separation(self, size=(50, 50)):
        """صورة بلون واحد"""
        img = np.full((*size, 3), 128, dtype=np.uint8)
        return img, self.separator.separate(img, num_colors=1)

    # ─── Test: generate_masks basic ──────────────────────────────────────

    def test_generate_masks_returns_list(self):
        """generate_masks يرجع list"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        self.assertIsInstance(masks, list)

    def test_generate_masks_correct_count(self):
        """عدد الـ masks = num_colors"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        self.assertEqual(len(masks), sep['num_colors'])

    def test_masks_are_binary(self):
        """كل mask يحتوي فقط على 0 و 255"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        for i, mask in enumerate(masks):
            unique_vals = set(np.unique(mask))
            self.assertTrue(
                unique_vals.issubset({0, 255}),
                f"Mask {i} has non-binary values: {unique_vals}"
            )

    def test_masks_shape_matches_image(self):
        """أبعاد الـ masks تطابق أبعاد الصورة"""
        size = (80, 120)
        img = np.zeros((*size, 3), dtype=np.uint8)
        img[:, :60] = (255, 0, 0)
        img[:, 60:] = (0, 255, 0)
        sep = self.separator.separate(img, num_colors=2)
        masks = self.generator.generate_masks(img, sep)
        for mask in masks:
            self.assertEqual(mask.shape, size)

    def test_masks_are_not_all_empty(self):
        """لا يجب أن تكون كل الـ masks فارغة"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        non_empty = [m for m in masks if np.any(m > 0)]
        self.assertGreater(len(non_empty), 0, "All masks are empty!")

    def test_masks_coverage_is_positive(self):
        """كل mask يغطي على الأقل بعض البيكسلات"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep, min_area=1)
        for i, mask in enumerate(masks):
            filled = np.sum(mask > 0)
            self.assertGreater(filled, 0, f"Mask {i} is completely empty")

    def test_masks_dont_overlap_significantly(self):
        """
        الـ masks لا تتداخل بشكل كبير — مجموع التغطيات ≈ 100% من المساحة
        (قد يكون هناك تداخل طفيف بسبب الـ morphological ops)
        """
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        total_pixels = masks[0].size
        total_covered = sum(np.sum(m > 0) for m in masks)
        # مجموع التغطية لا يتجاوز 150% (تداخل معقول)
        self.assertLessEqual(total_covered, total_pixels * 1.5)

    # ─── Test: generate_film_image ────────────────────────────────────────

    def test_generate_film_image_returns_rgb(self):
        """generate_film_image يرجع صورة RGB"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        film = self.generator.generate_film_image(masks[0])
        self.assertEqual(len(film.shape), 3, "Film should be RGB")
        self.assertEqual(film.shape[2], 3)

    def test_generate_film_image_with_border(self):
        """إضافة border يزيد أبعاد الصورة"""
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:40, 10:40] = 255

        border_px = 10
        film_no_border = self.generator.generate_film_image(mask, add_border=False)
        film_with_border = self.generator.generate_film_image(mask, add_border=True, border_px=border_px)

        expected_h = mask.shape[0] + border_px * 2
        expected_w = mask.shape[1] + border_px * 2
        self.assertEqual(film_with_border.shape[:2], (expected_h, expected_w))

    def test_generate_film_image_inverted(self):
        """invert=True يعكس الألوان"""
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:40, 10:40] = 255

        film_normal   = self.generator.generate_film_image(mask, invert=False, add_border=False)
        film_inverted = self.generator.generate_film_image(mask, invert=True, add_border=False)

        # بيكسل كان 255 يصبح 0 والعكس
        self.assertFalse(np.array_equal(film_normal, film_inverted))

    # ─── Test: generate_combined_preview ─────────────────────────────────

    def test_generate_combined_preview_shape(self):
        """preview له نفس أبعاد الـ masks"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        preview = self.generator.generate_combined_preview(masks, sep['colors'])
        self.assertEqual(preview.shape[:2], image.shape[:2])
        self.assertEqual(preview.shape[2], 3)

    def test_generate_combined_preview_empty_masks(self):
        """preview مع masks فارغة لا يُسبّب crash"""
        try:
            preview = self.generator.generate_combined_preview([], [])
            self.assertIsNotNone(preview)
        except Exception as e:
            self.fail(f"Should not raise: {e}")

    # ─── Test: get_mask_stats ─────────────────────────────────────────────

    def test_get_mask_stats_returns_list(self):
        """get_mask_stats يرجع list بنفس عدد الـ masks"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        stats = self.generator.get_mask_stats(masks)
        self.assertEqual(len(stats), len(masks))

    def test_get_mask_stats_fields(self):
        """كل عنصر في stats له الـ fields المطلوبة"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        stats = self.generator.get_mask_stats(masks)
        for stat in stats:
            self.assertIn('index', stat)
            self.assertIn('filled_pixels', stat)
            self.assertIn('coverage_percent', stat)
            self.assertIn('is_empty', stat)

    def test_get_mask_stats_coverage_in_range(self):
        """coverage_percent بين 0 و 100"""
        image, sep = self._make_two_color_separation()
        masks = self.generator.generate_masks(image, sep)
        stats = self.generator.get_mask_stats(masks)
        for stat in stats:
            self.assertGreaterEqual(stat['coverage_percent'], 0)
            self.assertLessEqual(stat['coverage_percent'], 100)

    # ─── Test: _cleanup_mask ─────────────────────────────────────────────

    def test_cleanup_preserves_large_regions(self):
        """الـ cleanup لا تحذف مناطق كبيرة"""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255  # منطقة كبيرة 60x60

        # استدعاء داخلي
        cleaned = self.generator._cleanup_mask(mask, kernel_size=3, min_area=50)
        filled_after = np.sum(cleaned > 0)

        # المنطقة الكبيرة يجب أن تبقى
        self.assertGreater(filled_after, 100)

    def test_cleanup_removes_tiny_noise(self):
        """الـ cleanup تحذف نقاط صغيرة جداً"""
        mask = np.zeros((100, 100), dtype=np.uint8)
        # نقطة صغيرة جداً (1x1)
        mask[50, 50] = 255

        cleaned = self.generator._cleanup_mask(mask, kernel_size=5, min_area=100)
        filled_after = np.sum(cleaned > 0)

        # النقطة الصغيرة يجب أن تُحذَف
        self.assertEqual(filled_after, 0, "Small noise should be removed")


if __name__ == '__main__':
    unittest.main(verbosity=2)
