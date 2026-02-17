"""
Export System
Export films in various formats (PNG, PDF, SVG)
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Dict, Optional
import json

# For PDF export
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, A3
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️  reportlab not installed. PDF export will be limited.")

# For SVG export
try:
    import svgwrite
    SVGWRITE_AVAILABLE = True
except ImportError:
    SVGWRITE_AVAILABLE = False
    print("⚠️  svgwrite not installed. SVG export not available.")

# For Registration Marks
from core.registration_marks import (
    RegistrationMarksGenerator,
    RegistrationConfig,
    MarkStyle,
    add_marks_to_all_films,
)


class Exporter:
    """Export films in multiple formats"""
    
    def __init__(self, output_dir: Path, dpi: int = 300):
        """
        Initialize exporter
        
        Args:
            output_dir: Output directory path
            dpi: Export DPI
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.dpi = dpi
    
    def export_png(self,
                   mask: np.ndarray,
                   filename: str,
                   color_info: Optional[Dict] = None) -> Path:
        """
        Export mask as PNG with DPI metadata
        
        Args:
            mask: Binary mask
            filename: Output filename
            color_info: Optional color information dict
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        
        # Convert to RGB if grayscale
        if len(mask.shape) == 2:
            mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        else:
            mask_rgb = mask
        
        # Save with PIL to preserve DPI
        pil_image = Image.fromarray(mask_rgb)
        pil_image.save(filepath, dpi=(self.dpi, self.dpi))
        
        return filepath
    
    def export_all_films(self,
                        masks: List[np.ndarray],
                        colors: List[List[int]],
                        color_names: List[str]) -> List[Path]:
        """
        Export all color films as PNG
        
        Args:
            masks: List of binary masks
            colors: List of RGB colors
            color_names: List of color names
            
        Returns:
            List of file paths
        """
        print(f"\n💾 Exporting {len(masks)} films as PNG...")
        
        exported_files = []
        
        for idx, (mask, color, name) in enumerate(zip(masks, colors, color_names)):
            filename = f"film_{idx+1:02d}_{name}.png"
            filepath = self.export_png(
                mask,
                filename,
                {'color': color, 'name': name}
            )
            print(f"   ✅ {filename}")
            exported_files.append(filepath)
        
        return exported_files
    
    def export_pdf(self,
                   masks: List[np.ndarray],
                   colors: List[List[int]],
                   color_names: List[str],
                   filename: str = "films_combined.pdf") -> Optional[Path]:
        """
        Export all films as multi-page PDF
        
        Args:
            masks: List of binary masks
            colors: List of RGB colors
            color_names: List of color names
            filename: PDF filename
            
        Returns:
            Path to PDF file or None if failed
        """
        if not REPORTLAB_AVAILABLE:
            print("⚠️  PDF export requires reportlab: pip install reportlab")
            return None
        
        print(f"\n📄 Exporting PDF: {filename}...")
        
        filepath = self.output_dir / filename
        
        # Create PDF
        c = canvas.Canvas(str(filepath), pagesize=A4)
        width, height = A4
        
        for idx, (mask, color, name) in enumerate(zip(masks, colors, color_names)):
            # Add page for each film
            if idx > 0:
                c.showPage()
            
            # Add title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(30, height - 40, f"Film {idx+1}: {name}")
            
            # Add color info
            c.setFont("Helvetica", 10)
            c.drawString(30, height - 60, f"Color: RGB{tuple(color)}")
            
            # Save mask as temp image
            temp_img = self.output_dir / f"_temp_film_{idx}.png"
            cv2.imwrite(str(temp_img), mask)
            
            # Add image to PDF
            # Scale to fit page
            img_width = width - 60
            img_height = (mask.shape[0] / mask.shape[1]) * img_width
            
            if img_height > height - 100:
                img_height = height - 100
                img_width = (mask.shape[1] / mask.shape[0]) * img_height
            
            c.drawImage(
                str(temp_img),
                30,
                height - 80 - img_height,
                width=img_width,
                height=img_height
            )
            
            # Clean up temp
            temp_img.unlink()
            
            print(f"   ✅ Page {idx+1}: {name}")
        
        c.save()
        print(f"   📄 PDF saved: {filepath}")
        
        return filepath
    
    def export_svg(self,
                   mask: np.ndarray,
                   filename: str,
                   color: Optional[List[int]] = None) -> Optional[Path]:
        """
        Export mask as SVG (simplified/vectorized)
        
        Args:
            mask: Binary mask
            filename: Output filename
            color: Optional RGB color
            
        Returns:
            Path to SVG file or None if failed
        """
        if not SVGWRITE_AVAILABLE:
            print("⚠️  SVG export requires svgwrite: pip install svgwrite")
            return None
        
        filepath = self.output_dir / filename
        
        # Find contours
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Create SVG
        h, w = mask.shape
        dwg = svgwrite.Drawing(str(filepath), size=(w, h))
        
        # Add each contour as a path
        fill_color = 'black' if color is None else f'rgb({color[0]},{color[1]},{color[2]})'
        
        for contour in contours:
            if len(contour) < 3:
                continue
            
            # Convert contour to SVG path
            points = contour.reshape(-1, 2)
            path_data = f"M {points[0][0]},{points[0][1]}"
            
            for point in points[1:]:
                path_data += f" L {point[0]},{point[1]}"
            
            path_data += " Z"
            
            dwg.add(dwg.path(d=path_data, fill=fill_color))
        
        dwg.save()
        
        return filepath
    
    def export_all_films_with_marks(
        self,
        masks,
        colors,
        color_names,
        add_marks: bool = True,
        mark_type: str = 'full',
    ):
        """
        Export all color films as PNG WITH registration marks

        Args:
            masks:       List of binary masks
            colors:      List of RGB colors [[R,G,B], ...]
            color_names: List of color names
            add_marks:   Whether to add registration marks
            mark_type:   'full', 'corner', 'side', 'minimal'
            
        Returns:
            List of file paths
        """
        print(f"\n💾 Exporting {len(masks)} films...")
        
        exported_files = []
        total = len(masks)
        
        # Configure marks
        config = RegistrationConfig(
            add_border=True,
            border_size=120,
            mark_type=mark_type,
            dpi=self.dpi,
            style=MarkStyle(
                mark_size=60,
                line_thickness=2,
                show_circle=True,
                show_cross=True,
                show_corner_marks=True,
                show_crop_marks=True,
                show_color_label=True,
                show_color_bar=(total > 1),
            )
        )
        
        generator = RegistrationMarksGenerator(dpi=self.dpi)
        
        for idx, (mask, color, name) in enumerate(zip(masks, colors, color_names)):
            color_index = idx + 1
            
            if add_marks:
                # Add registration marks
                result_image = generator.add_marks(
                    image=mask,
                    color_name=name,
                    color_index=color_index,
                    total_colors=total,
                    color_rgb=tuple(color),
                    config=config,
                )
                filename = f"film_{color_index:02d}_{name}_marks.png"
            else:
                result_image = mask
                filename = f"film_{color_index:02d}_{name}.png"
            
            # Save with PIL to keep DPI metadata
            if len(result_image.shape) == 2:
                result_rgb = cv2.cvtColor(result_image, cv2.COLOR_GRAY2RGB)
            else:
                result_rgb = cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB)
            
            filepath = self.output_dir / filename
            pil_image = Image.fromarray(result_rgb)
            pil_image.save(str(filepath), dpi=(self.dpi, self.dpi))
            
            print(f"   ✅ {filename}")
            exported_files.append(filepath)
        
        return exported_files
    
    def export_with_marks(
        self,
        mask,
        color_name: str,
        color_index: int,
        total_colors: int,
        color_rgb,
        mark_type: str = 'full',
    ) -> Path:
        """
        Export single film with registration marks

        Args:
            mask:         Binary mask numpy array
            color_name:   Color name (e.g. "Black")
            color_index:  1-based index
            total_colors: Total number of films
            color_rgb:    RGB color [R, G, B]
            mark_type:    'full', 'corner', 'side', 'minimal'
            
        Returns:
            Path to saved file
        """
        config = RegistrationConfig(
            add_border=True,
            border_size=120,
            mark_type=mark_type,
            dpi=self.dpi,
        )
        
        generator = RegistrationMarksGenerator(dpi=self.dpi)
        
        result = generator.add_marks(
            image=mask,
            color_name=color_name,
            color_index=color_index,
            total_colors=total_colors,
            color_rgb=tuple(color_rgb),
            config=config,
        )
        
        filename = f"film_{color_index:02d}_{color_name}_marks.png"
        filepath = self.output_dir / filename
        
        if len(result.shape) == 2:
            result_rgb = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)
        else:
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        
        pil_image = Image.fromarray(result_rgb)
        pil_image.save(str(filepath), dpi=(self.dpi, self.dpi))
        
        return filepath
    
    def create_readme(self,
                     metadata: Dict,
                     exported_files: List[Path]) -> Path:
        """
        Create README.txt with processing information
        
        Args:
            metadata: Processing metadata
            exported_files: List of exported files
            
        Returns:
            Path to README file
        """
        readme_path = self.output_dir / "README.txt"
        
        content = f"""
═══════════════════════════════════════════════════════════
    SILK SCREEN PRINTING FILES
═══════════════════════════════════════════════════════════

Generated: {metadata.get('timestamp', 'N/A')}
Source: {metadata.get('input_file', 'N/A')}

═══════════════════════════════════════════════════════════
SPECIFICATIONS
═══════════════════════════════════════════════════════════

Image Size:     {metadata.get('width', 0)} × {metadata.get('height', 0)} pixels
DPI:            {metadata.get('dpi', 300)}
Physical Size:  {metadata.get('size_cm', 'N/A')} cm
Print Method:   {metadata.get('print_method', 'Screen Printing')}
Colors:         {metadata.get('n_colors', 0)}

═══════════════════════════════════════════════════════════
COLOR SEPARATION
═══════════════════════════════════════════════════════════

"""
        
        # Add color information
        for idx, (name, color) in enumerate(zip(
            metadata.get('color_names', []),
            metadata.get('colors', [])
        )):
            content += f"{idx+1}. {name:20s} RGB{tuple(color)}\n"
        
        content += f"""
═══════════════════════════════════════════════════════════
FILES INCLUDED
═══════════════════════════════════════════════════════════

"""
        
        for filepath in exported_files:
            content += f"• {filepath.name}\n"
        
        content += f"""
═══════════════════════════════════════════════════════════
PRINTING INSTRUCTIONS
═══════════════════════════════════════════════════════════

1. Print each film on transparent film (positive)
2. Use one screen per color
3. Print colors in order: lightest to darkest
4. Ensure proper registration between screens
5. Recommended mesh count: {metadata.get('mesh_count', 110)} threads/inch

═══════════════════════════════════════════════════════════
QUALITY SETTINGS
═══════════════════════════════════════════════════════════

Minimum Stroke Width: {metadata.get('min_stroke_mm', 0.5)}mm
Detail Level:         {metadata.get('detail_level', 'Medium')}
Halftone:            {metadata.get('halftone', 'No')}
{"LPI:                 " + str(metadata.get('lpi', 'N/A')) if metadata.get('halftone') else ''}

═══════════════════════════════════════════════════════════
NOTES
═══════════════════════════════════════════════════════════

{metadata.get('notes', 'No additional notes.')}

═══════════════════════════════════════════════════════════
Generated with Silk Screen Processor v1.0
═══════════════════════════════════════════════════════════
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return readme_path
    
    def create_zip(self, filename: str = "films.zip") -> Path:
        """
        Create ZIP archive of all output files
        
        Args:
            filename: ZIP filename
            
        Returns:
            Path to ZIP file
        """
        import zipfile
        
        zip_path = self.output_dir / filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in self.output_dir.iterdir():
                if file.is_file() and file.name != filename:
                    zipf.write(file, file.name)
        
        print(f"\n📦 ZIP archive created: {zip_path}")
        return zip_path
