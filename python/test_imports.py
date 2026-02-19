#!/usr/bin/env python3
"""
test_imports.py — Validate all Python modules can be imported
Quick check that dependencies are installed correctly
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing Python imports...")
    
    tests = [
        ("numpy", "NumPy"),
        ("cv2", "OpenCV"),
        ("PIL", "Pillow"),
        ("skimage", "scikit-image"),
        ("scipy", "SciPy"),
    ]
    
    failed = []
    
    for module_name, display_name in tests:
        try:
            __import__(module_name)
            print(f"  ✓ {display_name} ({module_name})")
        except ImportError as e:
            print(f"  ✗ {display_name} ({module_name})")
            failed.append((display_name, str(e)))
    
    # Test local modules
    print("\nTesting local modules...")
    core_dir = Path(__file__).parent / "core"
    sys.path.insert(0, str(core_dir.parent))
    
    local_modules = [
        "core.color_separator",
        "core.mask_generator", 
        "core.edge_cleaner",
        "core.image_loader",
    ]
    
    for module_name in local_modules:
        try:
            __import__(module_name)
            print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}: {e}")
            failed.append((module_name, str(e)))
    
    if failed:
        print(f"\n❌ {len(failed)} imports failed:")
        for name, err in failed:
            print(f"   - {name}: {err}")
        return False
    else:
        print(f"\n✅ All imports successful!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
