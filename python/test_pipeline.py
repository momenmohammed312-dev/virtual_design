#!/usr/bin/env python3
"""
test_pipeline.py — Minimal pipeline test
Validates that main.py can process a test image without Flutter
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

# Test Parameters
TEST_WIDTH = 200
TEST_HEIGHT = 200
TEST_IMAGE_PATH = Path(__file__).parent / "samples" / "test_simple.png"
OUTPUT_DIR = Path(__file__).parent / "output_test"


def create_test_image():
    """Create a simple test image with solid colors."""
    print("[1/4] Creating test image...")
    
    # Create simple RGB image with colors
    img = np.zeros((TEST_HEIGHT, TEST_WIDTH, 3), dtype=np.uint8)
    
    # Red quadrant
    img[0:100, 0:100] = [0, 0, 255]
    
    # Green quadrant
    img[0:100, 100:200] = [0, 255, 0]
    
    # Blue quadrant
    img[100:200, 0:100] = [255, 0, 0]
    
    # Mixed (background)
    img[100:200, 100:200] = [200, 200, 200]
    
    # Save
    TEST_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(TEST_IMAGE_PATH)
    print(f"✓ Test image created: {TEST_IMAGE_PATH}")


def run_pipeline():
    """Run main.py on test image."""
    print("\n[2/4] Running pipeline...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Run main.py
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "main.py"),
        "--input", str(TEST_IMAGE_PATH),
        "--output", str(OUTPUT_DIR),
        "--colors", "3",
        "--dpi", "300",
    ]
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"Exit code: {result.returncode}")
    
    if result.returncode != 0:
        print("❌ Pipeline failed!")
        return False
    
    print("✓ Pipeline completed")
    return True


def verify_output():
    """Verify output files were created."""
    print("\n[3/4] Verifying output...")
    
    expected_files = ["film_0_k.png", "film_1_cyan.png", "film_2_magenta.png"]
    found_files = []
    
    for file in OUTPUT_DIR.glob("film_*.png"):
        found_files.append(file.name)
    
    print(f"Found {len(found_files)} film files:")
    for f in found_files:
        print(f"  - {f}")
    
    if len(found_files) >= 3:
        print("✓ Output files generated")
        return True
    else:
        print(f"❌ Expected >=3 films, found {len(found_files)}")
        return False


def cleanup():
    """Remove test files."""
    print("\n[4/4] Cleanup...")
    import shutil
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    if TEST_IMAGE_PATH.exists():
        TEST_IMAGE_PATH.unlink()
    print("✓ Cleaned up")


if __name__ == "__main__":
    try:
        create_test_image()
        success = run_pipeline()
        success = verify_output() and success
        
        if success:
            print("\n" + "="*50)
            print("✅ ALL TESTS PASSED!")
            print("="*50)
            exit(0)
        else:
            print("\n" + "="*50)
            print("❌ TESTS FAILED")
            print("="*50)
            exit(1)
    finally:
        cleanup()
