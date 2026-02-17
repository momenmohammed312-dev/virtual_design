"""
Demo script showing how to use the Python engine
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.image_loader import ImageLoader
from core.color_separator import ColorSeparator
from core.mask_generator import MaskGenerator
from core.edge_cleaner import EdgeCleaner
from core.exporter import Exporter
from utils.logger import Logger


def demo_processing(image_path: str):
    """
    Demo: Process an image step by step
    
    Args:
        image_path: Path to input image
    """
    logger = Logger(verbose=True)
    logger.header("🎨 SILK SCREEN PROCESSING DEMO")
    
    try:
        # Step 1: Load image
        logger.step(1, 5, "Loading image")
        loader = ImageLoader()
        image_data = loader.load(image_path, target_dpi=300)
        logger.success(f"Image loaded: {image_data['original_size'][0]}×{image_data['original_size'][1]}")
        
        # Step 2: Separate colors
        logger.step(2, 5, "Separating colors")
        separator = ColorSeparator()
        result = separator.separate(image_data['image'], n_colors=4)
        logger.success(f"Separated into {len(result['colors'])} colors")
        
        # Step 3: Generate masks
        logger.step(3, 5, "Generating masks")
        mask_gen = MaskGenerator()
        masks = mask_gen.generate_masks(
            result['quantized_image'],
            result['colors'],
            result['labels']
        )
        logger.success(f"Generated {len(masks)} masks")
        
        # Step 4: Clean edges
        logger.step(4, 5, "Cleaning edges")
        cleaner = EdgeCleaner()
        cleaned_masks = []
        for mask in masks:
            cleaned = cleaner.clean(mask, kernel_size=3)
            cleaned = cleaner.remove_small_objects(cleaned, min_area=50)
            cleaned_masks.append(cleaned)
        logger.success("Edges cleaned")
        
        # Step 5: Export
        logger.step(5, 5, "Exporting results")
        output_dir = Path('demo_output')
        output_dir.mkdir(exist_ok=True)
        
        exporter = Exporter(output_dir, dpi=300)
        files = exporter.export_all_films(
            cleaned_masks,
            result['colors'],
            result['color_names']
        )
        
        logger.success(f"Exported {len(files)} files to {output_dir}")
        
        # Show results
        logger.separator()
        logger.info("📊 RESULTS:")
        for idx, (file, name) in enumerate(zip(files, result['color_names'])):
            logger.info(f"  {idx+1}. {name}: {file.name}")
        
        logger.separator()
        logger.success("✅ Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python demo.py <image_path>")
        print("\nExample:")
        print("  python demo.py tests/test_samples/logo.png")
        sys.exit(1)
    
    demo_processing(sys.argv[1])
