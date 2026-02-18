"""
test_color_separator.py — Unit Tests for ColorSeparator
Virtual Design Silk Screen Studio

Run with: python -m pytest python/tests/test_color_separator.py -v
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import cv2
    from core.color_separator import ColorSeparator
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


@unittest.skipUnless(HAS_OPENCV, "opencv-python not installed")
class TestColorSeparator(unittest.TestCase):

    def setUp(self):
        self.separator = ColorSeparator()

    # ─── Helper image factories ───────────────────────────────────────────

    def _make_solid_image(self, color_bgr: tuple, size=(100, 100)) -> np.ndarray:
        """صورة بلون واحد ثابت"""
        img = np.zeros((*size, 3), dtype=np.uint8)
        img[:] = color_bgr
        return img

    def _make_two_color_image(
        self,
        color1=(0, 0, 255),    # أحمر (BGR)
        color2=(255, 0, 0),    # أزرق (BGR)
        size=(100, 100),
    ) -> np.ndarray:
        """صورة نصفها لون ونصفها لون آخر"""
        img = np.zeros((*size, 3), dtype=np.uint8)
        half = size[1] // 2
        img[:, :half] = color1
        img[:, half:] = color2
        return img

    def _make_checker_image(self, size=(100, 100)) -> np.ndarray:
        """صورة Checkerboard بـ 4 ألوان"""
        img = np.zeros((*size, 3), dtype=np.uint8)
        h, w = size
        h2, w2 = h // 2, w // 2
        img[:h2, :w2]  = (255,   0,   0)  # أحمر
        img[:h2, w2:]  = (0,   255,   0)  # أخضر
        img[h2:, :w2]  = (0,     0, 255)  # أزرق
        img[h2:, w2:]  = (255, 255,   0)  # أصفر
        return img

    # ─── Test: Basic separation ────────────────────────────────────────────

    def test_separate_returns_dict_with_required_keys(self):
        """التأكد من وجود كل الـ keys في النتيجة"""
        image = self._make_two_color_image()
        result = self.separator.separate(image, num_colors=2)

        self.assertIn('colors', result)
        self.assertIn('color_names', result)
        self.assertIn('label_map', result)
        self.assertIn('image', result)
        self.assertIn('num_colors', result)

    def test_separate_returns_correct_num_colors(self):
        """عدد الألوان المُرجَع يطابق num_colors"""
        image = self._make_checker_image()
        for n in [1, 2, 3, 4]:
            result = self.separator.separate(image, num_colors=n)
            self.assertEqual(len(result['colors']), n, f"Expected {n} colors")
            self.assertEqual(len(result['color_names']), n)
            self.assertEqual(result['num_colors'], n)

    def test_label_map_shape_matches_image(self):
        """label_map له نفس أبعاد الصورة"""
        image = self._make_two_color_image(size=(80, 120))
        result = self.separator.separate(image, num_colors=2)
        self.assertEqual(result['label_map'].shape, (80, 120))

    def test_label_map_values_in_range(self):
        """قيم label_map إما -1 (خلفية) أو بين 0 و num_colors-1"""
        image = self._make_two_color_image()
        n = 2
        result = self.separator.separate(image, num_colors=n)
        lm = result['label_map']
        # قيم صالحة فقط
        valid_values = set(range(-1, n))
        unique_values = set(np.unique(lm))
        self.assertTrue(unique_values.issubset(valid_values),
            f"Unexpected label values: {unique_values - valid_values}")

    def test_colors_are_rgb_tuples(self):
        """كل لون هو tuple من 3 قيم بين 0-255"""
        image = self._make_checker_image()
        result = self.separator.separate(image, num_colors=4)
        for color in result['colors']:
            self.assertEqual(len(color), 3, "Color should be RGB tuple")
            for channel in color:
                self.assertGreaterEqual(channel, 0)
                self.assertLessEqual(channel, 255)

    def test_color_names_format(self):
        """أسماء الألوان بالصيغة color_NN"""
        image = self._make_two_color_image()
        result = self.separator.separate(image, num_colors=2)
        for i, name in enumerate(result['color_names']):
            self.assertEqual(name, f"color_{i+1:02d}")

    def test_single_color_image(self):
        """صورة بلون واحد — يجب أن تنجح"""
        image = self._make_solid_image((128, 64, 200))
        result = self.separator.separate(image, num_colors=1)
        self.assertEqual(len(result['colors']), 1)

    # ─── Test: get_color_hex ──────────────────────────────────────────────

    def test_get_color_hex_format(self):
        """get_color_hex يرجع HEX بالصيغة الصحيحة"""
        cases = [
            ((255, 0, 0),   '#FF0000'),
            ((0, 255, 0),   '#00FF00'),
            ((0, 0, 255),   '#0000FF'),
            ((0, 0, 0),     '#000000'),
            ((255, 255, 255), '#FFFFFF'),
            ((16, 32, 48),  '#102030'),
        ]
        for rgb, expected in cases:
            with self.subTest(rgb=rgb):
                self.assertEqual(self.separator.get_color_hex(rgb), expected)

    # ─── Test: get_color_info ────────────────────────────────────────────

    def test_get_color_info_returns_list(self):
        """get_color_info يرجع قائمة بنفس عدد الألوان"""
        image = self._make_checker_image()
        result = self.separator.separate(image, num_colors=4)
        info = self.separator.get_color_info(result)
        self.assertEqual(len(info), 4)

    def test_get_color_info_has_required_fields(self):
        """كل عنصر في get_color_info له الـ fields المطلوبة"""
        image = self._make_two_color_image()
        result = self.separator.separate(image, num_colors=2)
        info = self.separator.get_color_info(result)
        required = {'index', 'name', 'rgb', 'hex', 'pixel_count', 'percentage'}
        for item in info:
            self.assertEqual(required, set(item.keys()))

    def test_color_info_percentages_sum_to_100(self):
        """مجموع النسب المئوية = 100% (تقريباً)"""
        image = self._make_checker_image()
        result = self.separator.separate(image, num_colors=4)
        info = self.separator.get_color_info(result)
        total_pct = sum(item['percentage'] for item in info)
        self.assertAlmostEqual(total_pct, 100.0, delta=2.0)

    # ─── Test: Edge cases ────────────────────────────────────────────────

    def test_num_colors_one(self):
        """num_colors=1 لا يسبب crash"""
        image = self._make_checker_image()
        result = self.separator.separate(image, num_colors=1)
        self.assertEqual(result['num_colors'], 1)

    def test_small_image(self):
        """صورة صغيرة جداً (10x10) — يجب أن تنجح"""
        image = self._make_two_color_image(size=(10, 10))
        result = self.separator.separate(image, num_colors=2)
        self.assertIsNotNone(result)

    def test_large_num_colors_on_simple_image(self):
        """طلب ألوان أكثر من الموجود في الصورة — يجب أن لا يُسبّب crash"""
        image = self._make_two_color_image()  # صورة بلونين فقط
        # طلب 6 ألوان — K-Means سيُعيد 6 clusters رغم أن الصورة بها لونان
        try:
            result = self.separator.separate(image, num_colors=6)
            self.assertEqual(len(result['colors']), 6)
        except Exception as e:
            self.fail(f"Should not raise: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
