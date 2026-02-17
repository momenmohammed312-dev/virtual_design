"""
Benchmark script to measure processing performance
"""

import time
import sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.image_loader import ImageLoader
from core.color_separator import ColorSeparator
from core.mask_generator import MaskGenerator
from core.edge_cleaner import EdgeCleaner
from utils.logger import Logger


def create_test_images():
    """Create test images of various sizes"""
    sizes = [
        (500, 500, "Small"),
        (1000, 1000, "Medium"),
        (2000, 2000, "Large"),
        (4000, 4000, "X-Large"),
    ]
    
    images = []
    
    for width, height, name in sizes:
        # Create random colored image
        img = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        images.append((img, name, width, height))
    
    return images


def benchmark_processing():
    """Benchmark processing performance"""
    logger = Logger(verbose=True)
    logger.header("⏱️  PROCESSING BENCHMARK")
    
    # Create test images
    print("Creating test images...")
    test_images = create_test_images()
    
    # Test each size
    results = []
    
    for img, name, width, height in test_images:
        print(f"\n{'='*60}")
        print(f"Testing: {name} ({width}×{height})")
        print('='*60)
        
        # Time color separation
        start = time.time()
        separator = ColorSeparator()
        result = separator.separate(img, n_colors=4, attempts=5)
        sep_time = time.time() - start
        
        # Time mask generation
        start = time.time()
        mask_gen = MaskGenerator()
        masks = mask_gen.generate_masks(
            result['quantized_image'],
            result['colors'],
            result['labels']
        )
        mask_time = time.time() - start
        
        # Time edge cleaning
        start = time.time()
        cleaner = EdgeCleaner()
        for mask in masks:
            cleaner.clean(mask, kernel_size=3)
        clean_time = time.time() - start
        
        total_time = sep_time + mask_time + clean_time
        
        results.append({
            'name': name,
            'size': f"{width}×{height}",
            'pixels': width * height,
            'separation': sep_time,
            'masking': mask_time,
            'cleaning': clean_time,
            'total': total_time,
        })
        
        print(f"\nResults:")
        print(f"  Color Separation: {sep_time:.2f}s")
        print(f"  Mask Generation:  {mask_time:.2f}s")
        print(f"  Edge Cleaning:    {clean_time:.2f}s")
        print(f"  TOTAL:            {total_time:.2f}s")
        print(f"  Pixels/second:    {(width*height)/total_time:,.0f}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"{'Image':<15} {'Size':<15} {'Time':<10} {'Speed':<15}")
    print('-'*60)
    
    for r in results:
        speed = f"{r['pixels']/r['total']/1000:.0f}K px/s"
        print(f"{r['name']:<15} {r['size']:<15} {r['total']:.2f}s    {speed:<15}")
    
    print('='*60)


if __name__ == '__main__':
    benchmark_processing()
