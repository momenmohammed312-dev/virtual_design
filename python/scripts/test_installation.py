"""
Test Python installation and dependencies
"""

import sys
import subprocess


def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info
    
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (need 3.8+)")
        return False


def check_dependencies():
    """Check if all dependencies are installed"""
    print("\nChecking dependencies...")
    
    dependencies = [
        ('opencv-python', 'cv2'),
        ('numpy', 'numpy'),
        ('Pillow', 'PIL'),
        ('reportlab', 'reportlab'),
        ('svgwrite', 'svgwrite'),
    ]
    
    all_good = True
    
    for package, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            all_good = False
    
    return all_good


def test_imports():
    """Test importing core modules"""
    print("\nTesting core modules...")
    
    modules = [
        'core.image_loader',
        'core.color_separator',
        'core.mask_generator',
        'core.edge_cleaner',
        'core.stroke_validator',
        'core.binarizer',
        'core.halftone_generator',
        'core.exporter',
        'utils.logger',
        'utils.validators',
        'config.settings',
    ]
    
    all_good = True
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module} - {e}")
            all_good = False
    
    return all_good


def test_basic_functionality():
    """Test basic image processing"""
    print("\nTesting basic functionality...")
    
    try:
        import cv2
        import numpy as np
        
        # Create test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:] = (255, 0, 0)  # Blue
        
        # Test basic OpenCV operations
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        print("✅ Basic image processing works")
        return True
        
    except Exception as e:
        print(f"❌ Basic processing failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("SILK SCREEN PYTHON ENGINE - INSTALLATION TEST")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Python Version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Core Modules", test_imports()))
    results.append(("Basic Functionality", test_basic_functionality()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Ready to use!")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
        print("\nTo install missing dependencies:")
        print("  pip install -r requirements.txt")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
