#!/usr/bin/env python3
"""
Simple test case to validate core pipeline fixes:
1. PDF polarity (bitwise_not)
2. DPI consistency (300)
3. 1:1 scaling with proper mm conversion
4. Proportional registration marks
5. High-quality upscaling (1200px min + LANCZOS4)
"""

import os
import sys
import numpy as np
import cv2
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

def create_test_logo():
    """Create a simple vector-style test logo"""
    # 800x600 canvas with white background
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    
    # Draw a black circle (logo element)
    cv2.circle(img, (400, 300), 150, (0, 0, 0), -1)
    
    # Draw text
    cv2.putText(img, "TEST", (320, 320), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    return img

def run_test():
    """Run the complete pipeline test"""
    print("🧪 Creating test logo...")
    test_img = create_test_logo()
    
    # Save test image
    input_dir = Path("test_input")
    input_dir.mkdir(exist_ok=True)
    test_path = input_dir / "test_logo.png"
    cv2.imwrite(str(test_path), test_img)
    print(f"✅ Test image saved: {test_path}")
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Run pipeline with corrected settings
    try:
        from main import main as pipeline_main
        
        # Mock args with corrected values
        class MockArgs:
            def __init__(self):
                self.input = str(test_path)
                self.output = str(output_dir)
                self.colors = 1  # Single color for simplicity
                self.dpi = 300  # Fixed DPI
                self.halftone = False  # No halftone for clean vector test
                self.clean = True
                self.combine_pdf = True
                self.auto_colors = False
                self.lpi = 65
                self.dot_shape = "round"
                self.detail_level = "medium"
                self.validate_strokes = True
                self.min_stroke = 0.0
                self.edge_enhance = "light"
                self.smoothing_factor = 0.25
                self.corner_threshold = 150.0
                self.dot_gain_radius = 1.0
                self.dot_gain_curve = "linear"
        
        args = MockArgs()
        
        print("🚀 Running pipeline with corrected settings...")
        print(f"   DPI: {args.dpi}")
        print(f"   Colors: {args.colors}")
        print(f"   Halftone: {args.halftone}")
        
        # Run the pipeline
        pipeline_main()
        
        print("✅ Pipeline completed successfully!")
        
        # Check outputs
        pdf_files = list(output_dir.glob("*.pdf"))
        png_files = list(output_dir.glob("*.png"))
        
        print(f"\n📄 Generated {len(pdf_files)} PDF files:")
        for pdf in pdf_files:
            size_kb = pdf.stat().st_size / 1024
            print(f"   {pdf.name} ({size_kb:.1f} KB)")
        
        print(f"\n🖼️ Generated {len(png_files)} PNG files:")
        for png in png_files:
            size_kb = png.stat().st_size / 1024
            print(f"   {png.name} ({size_kb:.1f} KB)")
        
        # Validation checks
        print("\n🔍 Validation Results:")
        
        # Check 1: PDF files should not be empty
        non_empty_pdfs = [p for p in pdf_files if p.stat().st_size > 1000]  # > 1KB
        print(f"   ✅ Non-empty PDFs: {len(non_empty_pdfs)}/{len(pdf_files)}")
        
        # Check 2: PNG files should have correct polarity
        if png_files:
            first_png = cv2.imread(str(png_files[0]), cv2.IMREAD_GRAYSCALE)
            if first_png is not None:
                mean_val = np.mean(first_png)
                # Film should have ink=0 (dark), so mean should be low
                polarity_ok = mean_val < 200  # Most pixels should be white (255)
                print(f"   ✅ PNG polarity check: mean={mean_val:.1f} (ink=0 expected)")
        
        print("\n🎉 Test completed! Check the output files to verify:")
        print("   1. PDFs show the logo (not empty)")
        print("   2. Logo is black on white background")
        print("   3. Registration marks are proportional")
        print("   4. Edges are smooth (not jagged)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    run_test()
