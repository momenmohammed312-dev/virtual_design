"""
test_registration_marks.py
==========================
Test script to verify registration marks are working correctly
Creates synthetic test images and verifies mark placement

Run from python/ directory:
    python tests/test_registration_marks.py
"""

import sys
import os
import numpy as np
import cv2
from pathlib import Path
from PIL import Image

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.registration_marks import (
    RegistrationMarksGenerator,
    RegistrationConfig,
    MarkStyle,
    MarkPosition,
    add_registration_marks,
    add_marks_to_all_films,
)


def create_test_mask(width=800, height=600, pattern='circle') -> np.ndarray:
    """Create a test mask image"""
    mask = np.zeros((height, width), dtype=np.uint8)
    
    if pattern == 'circle':
        cv2.circle(mask, (width//2, height//2), min(width, height)//3, 255, -1)
    
    elif pattern == 'rectangle':
        cv2.rectangle(mask,
                      (width//4, height//4),
                      (3*width//4, 3*height//4),
                      255, -1)
    
    elif pattern == 'text':
        cv2.putText(mask, "SILK", (width//4, height//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, 255, 20)
    
    elif pattern == 'complex':
        # Multiple shapes
        cv2.circle(mask, (width//4, height//4), 100, 255, -1)
        cv2.rectangle(mask, (width//2, height//4), (3*width//4, 3*height//4), 255, -1)
        cv2.circle(mask, (width//4, 3*height//4), 80, 255, -1)
    
    return mask


def test_single_mark():
    """Test adding marks to a single image"""
    print("\n" + "="*60)
    print("TEST 1: Single Image Registration Marks")
    print("="*60)
    
    # Create test image
    mask = create_test_mask(800, 600, 'circle')
    
    # Initialize generator
    generator = RegistrationMarksGenerator(dpi=300)
    
    # Add marks with full config
    config = RegistrationConfig.professional()
    
    result = generator.add_marks(
        image=mask,
        color_name="Black",
        color_index=1,
        total_colors=4,
        color_rgb=(0, 0, 0),
        config=config,
    )
    
    # Save result
    output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "test_single_marks.png"
    pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    pil_img.save(str(output_path), dpi=(300, 300))
    
    # Verify
    assert result is not None, "Result should not be None"
    assert result.shape[0] > mask.shape[0], "Result should be larger (has border)"
    assert result.shape[1] > mask.shape[1], "Result should be wider (has border)"
    
    print(f"✅ Single mark test passed")
    print(f"   Input size:  {mask.shape[1]}×{mask.shape[0]}")
    print(f"   Output size: {result.shape[1]}×{result.shape[0]}")
    print(f"   Saved to: {output_path}")
    
    return True


def test_all_mark_types():
    """Test all mark types"""
    print("\n" + "="*60)
    print("TEST 2: All Mark Types")
    print("="*60)
    
    mark_types = ['full', 'corner', 'side', 'minimal']
    generator = RegistrationMarksGenerator(dpi=300)
    
    output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for mark_type in mark_types:
        mask = create_test_mask(600, 400, 'rectangle')
        
        config = RegistrationConfig(
            add_border=True,
            border_size=100,
            mark_type=mark_type,
        )
        
        result = generator.add_marks(
            image=mask,
            color_name="Test",
            color_index=1,
            total_colors=1,
            config=config,
        )
        
        output_path = output_dir / f"test_marks_{mark_type}.png"
        pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        pil_img.save(str(output_path), dpi=(300, 300))
        
        print(f"   ✅ {mark_type}: saved to {output_path}")
    
    print("✅ All mark types test passed")
    return True


def test_multiple_films():
    """Test adding marks to multiple color films"""
    print("\n" + "="*60)
    print("TEST 3: Multiple Color Films")
    print("="*60)
    
    # Simulate 4-color separation
    films = [
        {
            'image': create_test_mask(800, 600, 'circle'),
            'name': 'Black',
            'color': [0, 0, 0],
        },
        {
            'image': create_test_mask(800, 600, 'rectangle'),
            'name': 'Cyan',
            'color': [0, 188, 212],
        },
        {
            'image': create_test_mask(800, 600, 'complex'),
            'name': 'Magenta',
            'color': [233, 30, 99],
        },
        {
            'image': create_test_mask(800, 600, 'text'),
            'name': 'Yellow',
            'color': [255, 193, 7],
        },
    ]
    
    output_dir = "tests/output/films_with_marks"
    
    saved_paths = add_marks_to_all_films(
        films=films,
        output_dir=output_dir,
        dpi=300,
        mark_type='full',
    )
    
    assert len(saved_paths) == 4, "Should save 4 files"
    
    for path in saved_paths:
        assert Path(path).exists(), f"File should exist: {path}"
    
    print(f"\n✅ Multiple films test passed")
    print(f"   Saved {len(saved_paths)} files to {output_dir}/")
    
    return True


def test_standalone_function():
    """Test the standalone add_registration_marks function"""
    print("\n" + "="*60)
    print("TEST 4: Standalone Function")
    print("="*60)
    
    # Create test image
    mask = create_test_mask(1000, 700, 'complex')
    
    # Save to temp file
    input_path = "tests/output/temp_input.png"
    output_path = "tests/output/test_standalone_output.png"
    
    Path("tests/output").mkdir(parents=True, exist_ok=True)
    cv2.imwrite(input_path, mask)
    
    # Call standalone function
    result_path = add_registration_marks(
        image_path=input_path,
        output_path=output_path,
        color_name="Magenta",
        color_index=3,
        total_colors=4,
        color_rgb=(233, 30, 99),
        mark_type='full',
        dpi=300,
        border_size=120,
    )
    
    assert Path(result_path).exists(), "Output file should exist"
    
    # Verify DPI
    pil_img = Image.open(result_path)
    saved_dpi = pil_img.info.get('dpi', (72, 72))
    assert saved_dpi[0] == 300, f"DPI should be 300, got {saved_dpi[0]}"
    
    print(f"✅ Standalone function test passed")
    print(f"   Output: {result_path}")
    print(f"   DPI: {saved_dpi[0]}")
    
    # Cleanup temp
    Path(input_path).unlink(missing_ok=True)
    
    return True


def test_high_dpi():
    """Test with high DPI (600)"""
    print("\n" + "="*60)
    print("TEST 5: High DPI (600)")
    print("="*60)
    
    mask = create_test_mask(2000, 1500, 'circle')
    
    config = RegistrationConfig(
        add_border=True,
        border_size=200,
        mark_type='full',
        dpi=600,
        style=MarkStyle(
            mark_size=100,
            line_thickness=3,
        )
    )
    
    generator = RegistrationMarksGenerator(dpi=600)
    result = generator.add_marks(
        image=mask,
        color_name="High-Res Test",
        color_index=1,
        total_colors=2,
        config=config,
    )
    
    output_path = "tests/output/test_high_dpi.png"
    pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    pil_img.save(output_path, dpi=(600, 600))
    
    print(f"✅ High DPI test passed")
    print(f"   Output: {output_path}")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 REGISTRATION MARKS - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Single Mark", test_single_mark),
        ("All Mark Types", test_all_mark_types),
        ("Multiple Films", test_multiple_films),
        ("Standalone Function", test_standalone_function),
        ("High DPI", test_high_dpi),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed, None))
        except Exception as e:
            import traceback
            results.append((test_name, False, str(e)))
            print(f"\n❌ FAILED: {test_name}")
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for name, passed, error in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<30} {status}")
        if error:
            print(f"    Error: {error}")
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📁 Output files saved to: tests/output/")
        print("\nOpen the PNG files to verify registration marks visually.")
    else:
        print("\n❌ SOME TESTS FAILED - Check errors above")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
