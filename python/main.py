"""
Silk Screen Image Processor - Main Entry Point
Complete processing pipeline for screen printing color separation
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Core processing modules
from core.image_loader import ImageLoader
from core.color_separator import ColorSeparator
from core.mask_generator import MaskGenerator
from core.edge_cleaner import EdgeCleaner
from core.stroke_validator import StrokeValidator
from core.binarizer import Binarizer
from core.halftone_generator import HalftoneGenerator
from core.exporter import Exporter

# Utilities
from utils.logger import Logger
from utils.validators import Validators
from config.settings import ProcessingSettings, DEFAULT_SETTINGS


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Silk Screen Image Processor - Color Separation for Screen Printing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic processing
  python main.py --input design.jpg
  
  # Custom colors and DPI
  python main.py --input design.jpg --colors 3 --dpi 600
  
  # With halftone
  python main.py --input photo.jpg --colors 4 --halftone --lpi 65
  
  # Full processing with all options
  python main.py --input design.jpg --colors 4 --dpi 300 --clean --validate-strokes --halftone --lpi 55
        """
    )
    
    # Input/Output
    parser.add_argument('--input', '-i', required=True, help='Input image path')
    parser.add_argument('--output', '-o', default='output', help='Output directory (default: output)')
    
    # Color separation
    parser.add_argument('--colors', '-c', type=int, default=4, help='Number of colors (default: 4)')
    parser.add_argument('--attempts', type=int, default=10, help='K-means attempts (default: 10)')
    
    # Image quality
    parser.add_argument('--dpi', type=int, default=300, help='Target DPI (default: 300)')
    
    # Processing options
    parser.add_argument('--clean', action='store_true', help='Clean edges and remove noise')
    parser.add_argument('--kernel-size', type=int, default=3, help='Morphology kernel size (default: 3)')
    parser.add_argument('--min-area', type=int, default=50, help='Minimum object area in pixels (default: 50)')
    
    # Stroke validation
    parser.add_argument('--validate-strokes', action='store_true', help='Validate stroke widths')
    parser.add_argument('--min-stroke', type=float, default=0.5, help='Minimum stroke width in mm (default: 0.5)')
    parser.add_argument('--thicken', action='store_true', help='Auto-thicken thin strokes')
    
    # Binarization
    parser.add_argument('--binarize', action='store_true', help='Apply binarization')
    parser.add_argument('--threshold-method', choices=['simple', 'otsu', 'adaptive_mean', 'adaptive_gaussian'],
                       default='otsu', help='Threshold method (default: otsu)')
    parser.add_argument('--threshold', type=int, default=127, help='Threshold value for simple method (default: 127)')
    
    # Halftone
    parser.add_argument('--halftone', action='store_true', help='Generate halftone patterns')
    parser.add_argument('--lpi', type=int, default=55, help='Lines per inch for halftone (default: 55)')
    parser.add_argument('--angle', type=float, default=45.0, help='Halftone angle in degrees (default: 45)')
    parser.add_argument('--dot-shape', choices=['round', 'square', 'ellipse'], 
                       default='round', help='Halftone dot shape (default: round)')
    
    # Export options
    parser.add_argument('--no-png', action='store_true', help='Skip PNG export')
    parser.add_argument('--pdf', action='store_true', help='Export combined PDF')
    parser.add_argument('--svg', action='store_true', help='Export SVG (experimental)')
    parser.add_argument('--zip', action='store_true', help='Create ZIP archive')
    
    # Other
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress verbose output')
    parser.add_argument('--detail-level', choices=['high', 'medium', 'low'], 
                       default='medium', help='Processing detail level (default: medium)')
    
    return parser.parse_args()


def create_metadata(args, image_data: Dict, processing_results: Dict) -> Dict:
    """Create metadata dictionary"""
    return {
        'timestamp': datetime.now().isoformat(),
        'input_file': args.input,
        'width': image_data['original_size'][0],
        'height': image_data['original_size'][1],
        'dpi': image_data['dpi'],
        'size_cm': f"{image_data['original_size'][0] / image_data['dpi'] * 2.54:.1f} × {image_data['original_size'][1] / image_data['dpi'] * 2.54:.1f}",
        'n_colors': args.colors,
        'colors': processing_results['colors'],
        'color_names': processing_results['color_names'],
        'detail_level': args.detail_level,
        'min_stroke_mm': args.min_stroke if args.validate_strokes else 'N/A',
        'halftone': 'Yes' if args.halftone else 'No',
        'lpi': args.lpi if args.halftone else 'N/A',
        'mesh_count': int(args.lpi * 4.5) if args.halftone else 110,
        'print_method': 'Screen Printing',
        'notes': 'Generated with Silk Screen Processor'
    }


def main():
    """Main processing pipeline"""
    
    # Parse arguments
    args = parse_arguments()
    
    # Initialize logger
    logger = Logger(verbose=not args.quiet)
    
    # Print header
    logger.header("🎨 SILK SCREEN IMAGE PROCESSOR v1.0")
    
    # Start timer
    logger.start_timer()
    
    # Validate inputs
    logger.step(0, 9, "Validating inputs")
    
    valid, error = Validators.validate_image_path(args.input)
    if not valid:
        logger.error(error)
        return 1
    
    valid, message = Validators.validate_color_count(args.colors)
    if not valid:
        logger.error(message)
        return 1
    elif message:
        logger.warning(message)
    
    valid, message = Validators.validate_dpi(args.dpi)
    if not valid:
        logger.error(message)
        return 1
    elif message:
        logger.warning(message)
    
    if args.validate_strokes:
        valid, message = Validators.validate_stroke_width(args.min_stroke)
        if not valid:
            logger.error(message)
            return 1
        elif message:
            logger.warning(message)
    
    if args.halftone:
        valid, message = Validators.validate_lpi(args.lpi)
        if not valid:
            logger.error(message)
            return 1
        elif message:
            logger.warning(message)
    
    logger.success("All inputs validated")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Output directory: {output_dir.absolute()}")
    
    try:
        # ==================== STEP 1: Load Image ====================
        logger.step(1, 9, "Loading and preparing image")
        
        loader = ImageLoader()
        image_data = loader.load(args.input, target_dpi=args.dpi)
        
        valid, message = loader.validate_size(image_data)
        if not valid:
            logger.error(message)
            return 1
        
        logger.success(f"Image loaded: {image_data['original_size'][0]}×{image_data['original_size'][1]} @ {image_data['dpi']} DPI")
        if image_data.get('upscaled'):
            logger.warning("Image was upscaled to meet DPI requirements")
        
        # ==================== STEP 2: Color Separation ====================
        logger.step(2, 9, "Separating colors")
        
        separator = ColorSeparator()
        separation_result = separator.separate(
            image_data['image'],
            n_colors=args.colors,
            attempts=args.attempts
        )
        
        logger.success(f"Colors separated: {', '.join(separation_result['color_names'])}")
        
        # ==================== STEP 3: Generate Masks ====================
        logger.step(3, 9, "Generating color masks")
        
        mask_gen = MaskGenerator()
        masks = mask_gen.generate_masks(
            separation_result['quantized_image'],
            separation_result['colors'],
            separation_result['labels']
        )
        
        logger.success(f"{len(masks)} masks generated")
        
        # ==================== STEP 4: Clean Edges (Optional) ====================
        if args.clean:
            logger.step(4, 9, "Cleaning edges and removing noise")
            
            cleaner = EdgeCleaner()
            cleaned_masks = []
            
            for idx, mask in enumerate(masks):
                logger.info(f"Processing mask {idx+1}/{len(masks)}: {separation_result['color_names'][idx]}")
                
                # Clean edges
                cleaned = cleaner.clean(
                    mask,
                    kernel_size=args.kernel_size,
                    iterations=1
                )
                
                # Remove small objects
                cleaned = cleaner.remove_small_objects(
                    cleaned,
                    min_area=args.min_area
                )
                
                cleaned_masks.append(cleaned)
            
            masks = cleaned_masks
            logger.success("Edges cleaned successfully")
        else:
            logger.step(4, 9, "Skipping edge cleaning")
        
        # ==================== STEP 5: Validate Strokes (Optional) ====================
        if args.validate_strokes:
            logger.step(5, 9, "Validating stroke widths")
            
            validator = StrokeValidator(
                min_stroke_mm=args.min_stroke,
                dpi=args.dpi
            )
            
            validated_masks = []
            all_warnings = []
            
            for idx, mask in enumerate(masks):
                logger.info(f"Validating mask {idx+1}/{len(masks)}: {separation_result['color_names'][idx]}")
                
                result = validator.validate_mask(mask)
                
                if not result['valid']:
                    for warning in result['warnings']:
                        logger.warning(warning)
                        all_warnings.append(warning)
                    
                    if args.thicken:
                        logger.info("Auto-thickening strokes...")
                        mask = validator.thicken_strokes(mask, target_width_mm=args.min_stroke)
                
                validated_masks.append(mask)
            
            masks = validated_masks
            
            if all_warnings:
                logger.warning(f"Total validation warnings: {len(all_warnings)}")
            else:
                logger.success("All stroke widths validated")
        else:
            logger.step(5, 9, "Skipping stroke validation")
        
        # ==================== STEP 6: Binarize (Optional) ====================
        if args.binarize:
            logger.step(6, 9, "Binarizing masks")
            
            binarizer = Binarizer()
            binary_masks = []
            
            for idx, mask in enumerate(masks):
                logger.info(f"Binarizing mask {idx+1}/{len(masks)}: {separation_result['color_names'][idx]}")
                
                binary = binarizer.binarize(
                    mask,
                    method=args.threshold_method,
                    threshold=args.threshold
                )
                
                # Clean noise
                binary = binarizer.remove_noise(binary, kernel_size=3)
                
                binary_masks.append(binary)
            
            masks = binary_masks
            logger.success("Binarization complete")
        else:
            logger.step(6, 9, "Skipping binarization")
        
        # ==================== STEP 7: Halftone (Optional) ====================
        if args.halftone:
            logger.step(7, 9, "Generating halftone patterns")
            
            halftone_gen = HalftoneGenerator(dpi=args.dpi)
            halftone_masks = []
            
            for idx, mask in enumerate(masks):
                logger.info(f"Processing mask {idx+1}/{len(masks)}: {separation_result['color_names'][idx]}")
                
                halftone = halftone_gen.generate(
                    mask,
                    lpi=args.lpi,
                    angle=args.angle,
                    dot_shape=args.dot_shape
                )
                
                halftone_masks.append(halftone)
            
            masks = halftone_masks
            logger.success("Halftone generation complete")
        else:
            logger.step(7, 9, "Skipping halftone")
        
        # ==================== STEP 8: Export ====================
        logger.step(8, 9, "Exporting films")
        
        exporter = Exporter(output_dir, dpi=args.dpi)
        exported_files = []
        
        # Export PNG
        if not args.no_png:
            png_files = exporter.export_all_films(
                masks,
                separation_result['colors'],
                separation_result['color_names']
            )
            exported_files.extend(png_files)
        
        # Export PDF
        if args.pdf:
            pdf_file = exporter.export_pdf(
                masks,
                separation_result['colors'],
                separation_result['color_names']
            )
            if pdf_file:
                exported_files.append(pdf_file)
        
        # Export SVG
        if args.svg:
            logger.info("Exporting SVG files...")
            for idx, (mask, color, name) in enumerate(zip(
                masks,
                separation_result['colors'],
                separation_result['color_names']
            )):
                svg_file = exporter.export_svg(
                    mask,
                    f"film_{idx+1:02d}_{name}.svg",
                    color
                )
                if svg_file:
                    logger.success(f"SVG exported: {svg_file.name}")
                    exported_files.append(svg_file)
        
        logger.success(f"Exported {len(exported_files)} files")
        
        # ==================== STEP 9: Create Documentation ====================
        logger.step(9, 9, "Creating documentation")
        
        # Create metadata
        metadata = create_metadata(args, image_data, separation_result)
        
        # Save metadata JSON
        metadata_path = output_dir / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logger.success(f"Metadata saved: {metadata_path.name}")
        
        # Create README
        readme_path = exporter.create_readme(metadata, exported_files)
        logger.success(f"README created: {readme_path.name}")
        
        # Create ZIP
        if args.zip:
            zip_path = exporter.create_zip()
            logger.success(f"ZIP archive created: {zip_path.name}")
        
        # ==================== COMPLETE ====================
        logger.separator()
        logger.success("🎉 Processing complete!")
        logger.info(f"📁 Output directory: {output_dir.absolute()}")
        logger.separator()
        
        # Print summary
        print("\n📊 SUMMARY:")
        print(f"   Input:       {args.input}")
        print(f"   Colors:      {args.colors}")
        print(f"   DPI:         {args.dpi}")
        print(f"   Files:       {len(exported_files)}")
        print(f"   Output:      {output_dir.absolute()}")
        
        # End timer
        logger.end_timer()
        
        return 0
        
    except KeyboardInterrupt:
        logger.error("\n⚠️  Processing interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        
        if not args.quiet:
            import traceback
            print("\n" + "="*60)
            print("FULL ERROR TRACEBACK:")
            print("="*60)
            traceback.print_exc()
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
