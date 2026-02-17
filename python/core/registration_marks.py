"""
Registration Marks Generator
============================

Adds registration marks to images for screen printing.

This file provides a flexible generator and CLI.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Tuple, Optional, Literal
from dataclasses import dataclass, field


@dataclass
class MarkStyle:
    color: Tuple[int, int, int] = (0, 0, 0)
    background_color: Tuple[int, int, int] = (255, 255, 255)
    line_thickness: int = 2
    mark_size: int = 60
    margin: int = 40
    show_circle: bool = True
    show_cross: bool = True
    show_corner_marks: bool = True
    show_crop_marks: bool = True
    show_color_label: bool = True
    show_color_bar: bool = False
    font_size: int = 24


@dataclass
class MarkPosition:
    x: int
    y: int
    label: str = ""


@dataclass
class RegistrationConfig:
    add_border: bool = True
    border_size: int = 120
    mark_type: Literal['full', 'corner', 'side', 'minimal'] = 'full'
    style: MarkStyle = field(default_factory=MarkStyle)
    show_film_info: bool = True
    show_screen_angle: bool = False
    dpi: int = 300

    @classmethod
    def professional(cls) -> 'RegistrationConfig':
        return cls(
            add_border=True,
            border_size=150,
            mark_type='full',
            style=MarkStyle(
                mark_size=80,
                margin=50,
                line_thickness=2,
                show_circle=True,
                show_cross=True,
                show_corner_marks=True,
                show_crop_marks=True,
                show_color_label=True,
                show_color_bar=True,
            )
        )

    @classmethod
    def minimal(cls) -> 'RegistrationConfig':
        return cls(
            add_border=True,
            border_size=100,
            mark_type='minimal',
            style=MarkStyle(
                mark_size=50,
                margin=30,
                line_thickness=2,
                show_circle=True,
                show_cross=True,
                show_corner_marks=False,
                show_crop_marks=True,
                show_color_label=True,
                show_color_bar=False,
            )
        )


class RegistrationMarksGenerator:
    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def add_marks(
        self,
        image: np.ndarray,
        color_name: str = "Color",
        color_index: int = 1,
        total_colors: int = 4,
        color_rgb: Tuple[int, int, int] = (0, 0, 0),
        config: Optional[RegistrationConfig] = None,
    ) -> np.ndarray:
        if config is None:
            config = RegistrationConfig()

        if len(image.shape) == 2:
            canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            canvas = image.copy()

        if config.add_border:
            canvas = self._add_border(canvas, config.border_size)

        h, w = canvas.shape[:2]
        style = config.style

        positions = self._get_mark_positions(w, h, config)
        for pos in positions:
            self._draw_registration_mark(canvas, pos.x, pos.y, style)

        if style.show_corner_marks:
            self._draw_corner_marks(canvas, config)

        if style.show_crop_marks:
            self._draw_crop_marks(canvas, config)

        if style.show_color_label:
            self._draw_color_label(canvas, color_name, color_index, total_colors, color_rgb, config)

        if style.show_color_bar:
            self._draw_color_bar(canvas, color_rgb, config)

        return canvas

    def _add_border(self, image: np.ndarray, border_size: int) -> np.ndarray:
        return cv2.copyMakeBorder(
            image,
            border_size,
            border_size,
            border_size,
            border_size,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255)
        )

    def _get_mark_positions(self, w: int, h: int, config: RegistrationConfig) -> List[MarkPosition]:
        margin = config.style.margin
        cx = w // 2
        cy = h // 2
        if config.mark_type == 'full':
            return [
                MarkPosition(cx, margin, "TC"),
                MarkPosition(cx, h - margin, "BC"),
                MarkPosition(margin, cy, "LC"),
                MarkPosition(w - margin, cy, "RC"),
                MarkPosition(cx // 2, margin + 10, "TL"),
                MarkPosition(cx + cx // 2, margin + 10, "TR"),
            ]
        elif config.mark_type == 'corner':
            return [
                MarkPosition(margin, margin, "TL"),
                MarkPosition(w - margin, margin, "TR"),
                MarkPosition(margin, h - margin, "BL"),
                MarkPosition(w - margin, h - margin, "BR"),
            ]
        elif config.mark_type == 'side':
            return [
                MarkPosition(cx, margin, "T"),
                MarkPosition(cx, h - margin, "B"),
                MarkPosition(margin, cy, "L"),
                MarkPosition(w - margin, cy, "R"),
            ]
        elif config.mark_type == 'minimal':
            return [
                MarkPosition(cx, margin, "T"),
                MarkPosition(cx, h - margin, "B"),
            ]
        return []

    def _draw_registration_mark(self, canvas: np.ndarray, cx: int, cy: int, style: MarkStyle):
        size = style.mark_size // 2
        thickness = style.line_thickness
        color = style.color
        bg = style.background_color

        if style.show_circle:
            cv2.circle(canvas, (cx, cy), size + 5, bg, -1)
        if style.show_circle:
            cv2.circle(canvas, (cx, cy), size, color, thickness)
        cv2.circle(canvas, (cx, cy), 4, color, -1)

        if style.show_cross:
            gap = 8
            cv2.line(canvas, (cx - size - 15, cy), (cx - gap, cy), color, thickness)
            cv2.line(canvas, (cx + gap, cy), (cx + size + 15, cy), color, thickness)
            cv2.line(canvas, (cx, cy - size - 15), (cx, cy - gap), color, thickness)
            cv2.line(canvas, (cx, cy + gap), (cx, cy + size + 15), color, thickness)

    def _draw_corner_marks(self, canvas: np.ndarray, config: RegistrationConfig):
        h, w = canvas.shape[:2]
        b = config.border_size
        style = config.style
        color = style.color
        thickness = style.line_thickness
        length = 40
        corners = [
            {'h_start': (b - length, b), 'h_end': (b + length, b), 'v_start': (b, b - length), 'v_end': (b, b + length)},
            {'h_start': (w - b - length, b), 'h_end': (w - b + length, b), 'v_start': (w - b, b - length), 'v_end': (w - b, b + length)},
            {'h_start': (b - length, h - b), 'h_end': (b + length, h - b), 'v_start': (b, h - b - length), 'v_end': (b, h - b + length)},
            {'h_start': (w - b - length, h - b), 'h_end': (w - b + length, h - b), 'v_start': (w - b, h - b - length), 'v_end': (w - b, h - b + length)},
        ]
        for corner in corners:
            cv2.line(canvas, corner['h_start'], corner['h_end'], color, thickness)
            cv2.line(canvas, corner['v_start'], corner['v_end'], color, thickness)

    def _draw_crop_marks(self, canvas: np.ndarray, config: RegistrationConfig):
        h, w = canvas.shape[:2]
        b = config.border_size
        style = config.style
        color = style.color
        thickness = 1
        gap = 10
        length = 25
        cv2.line(canvas, (b - gap - length, b), (b - gap, b), color, thickness)
        cv2.line(canvas, (b, b - gap - length), (b, b - gap), color, thickness)
        cv2.line(canvas, (w - b + gap, b), (w - b + gap + length, b), color, thickness)
        cv2.line(canvas, (w - b, b - gap - length), (w - b, b - gap), color, thickness)
        cv2.line(canvas, (b - gap - length, h - b), (b - gap, h - b), color, thickness)
        cv2.line(canvas, (b, h - b + gap), (b, h - b + gap + length), color, thickness)
        cv2.line(canvas, (w - b + gap, h - b), (w - b + gap + length, h - b), color, thickness)
        cv2.line(canvas, (w - b, h - b + gap), (w - b, h - b + gap + length), color, thickness)

    def _draw_color_label(self, canvas: np.ndarray, color_name: str, color_index: int, total_colors: int, color_rgb: Tuple[int, int, int], config: RegistrationConfig):
        h, w = canvas.shape[:2]
        b = config.border_size
        pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        x = b
        y = h - b + 10
        swatch_size = 25
        swatch_color = (color_rgb[0], color_rgb[1], color_rgb[2])
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=(255, 255, 255))
        draw.rectangle([x + 2, y + 2, x + swatch_size - 2, y + swatch_size - 2], fill=swatch_color)
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], outline=(0, 0, 0), width=1)
        text_x = x + swatch_size + 10
        text_main = f"Film {color_index}/{total_colors}  |  {color_name.upper()}"
        draw.text((text_x, y + 2), text_main, fill=(0, 0, 0), font=font_large)
        text_info = f"DPI: {config.dpi}  |  Registration Mark"
        draw.text((text_x, y + 28), text_info, fill=(100, 100, 100), font=font_small)
        canvas[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _draw_color_bar(self, canvas: np.ndarray, color_rgb: Tuple[int, int, int], config: RegistrationConfig):
        h, w = canvas.shape[:2]
        b = config.border_size
        bar_x = w - b + 10
        bar_y = b
        bar_width = 30
        bar_height = h - (2 * b)
        for i in range(bar_height):
            t = i / bar_height
            r = int(255 + (color_rgb[0] - 255) * t)
            g = int(255 + (color_rgb[1] - 255) * t)
            b_val = int(255 + (color_rgb[2] - 255) * t)
            cv2.line(canvas, (bar_x, bar_y + i), (bar_x + bar_width, bar_y + i), (b_val, g, r), 1)
        cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (0, 0, 0), 1)
        cv2.putText(canvas, "0%", (bar_x, bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(canvas, "100%", (bar_x, bar_y + bar_height + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)


def add_registration_marks(image_path: str, output_path: str, color_name: str = "Color", color_index: int = 1, total_colors: int = 1, color_rgb: Tuple[int, int, int] = (0, 0, 0), mark_type: str = 'full', dpi: int = 300, border_size: int = 120) -> str:
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    config = RegistrationConfig(add_border=True, border_size=border_size, mark_type=mark_type, dpi=dpi, style=MarkStyle(mark_size=60, show_circle=True, show_cross=True, show_corner_marks=True, show_crop_marks=True, show_color_label=True, show_color_bar=(total_colors > 1)))
    generator = RegistrationMarksGenerator(dpi=dpi)
    result = generator.add_marks(image=image, color_name=color_name, color_index=color_index, total_colors=total_colors, color_rgb=color_rgb, config=config)
    pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    pil_result.save(output_path, dpi=(dpi, dpi))
    print(f"✅ Registration marks added: {output_path}")
    return output_path


def add_marks_to_all_films(films: List[dict], output_dir: str, dpi: int = 300, mark_type: str = 'full', config: Optional[RegistrationConfig] = None) -> List[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    if config is None:
        config = RegistrationConfig(add_border=True, border_size=120, mark_type=mark_type, dpi=dpi)
    generator = RegistrationMarksGenerator(dpi=dpi)
    total_colors = len(films)
    saved_paths = []
    for idx, film in enumerate(films):
        color_index = idx + 1
        color_name = film.get('name', f'Color {color_index}')
        color_rgb = tuple(film.get('color', [0, 0, 0]))
        image = film['image']
        result = generator.add_marks(image=image, color_name=color_name, color_index=color_index, total_colors=total_colors, color_rgb=color_rgb, config=config)
        filename = f"film_{color_index:02d}_{color_name}_with_marks.png"
        filepath = output_dir / filename
        pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        pil_result.save(str(filepath), dpi=(dpi, dpi))
        saved_paths.append(str(filepath))
    return saved_paths


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='Add Registration Marks to images for Screen Printing')
    parser.add_argument('--input', '-i', required=True, help='Input image path')
    parser.add_argument('--output', '-o', required=True, help='Output image path')
    parser.add_argument('--color-name', default='Color', help='Color name (e.g. Black, Cyan)')
    parser.add_argument('--color-index', type=int, default=1, help='Color index (1-based)')
    parser.add_argument('--total-colors', type=int, default=1, help='Total number of colors')
    parser.add_argument('--color-rgb', nargs=3, type=int, default=[0, 0, 0], metavar=('R', 'G', 'B'), help='Color RGB values')
    parser.add_argument('--mark-type', choices=['full', 'corner', 'side', 'minimal'], default='full', help='Type of registration marks')
    parser.add_argument('--dpi', type=int, default=300, help='Image DPI (default: 300)')
    parser.add_argument('--border', type=int, default=120, help='Border size in pixels (default: 120)')
    parser.add_argument('--professional', action='store_true', help='Use professional print shop settings')
    args = parser.parse_args()
    try:
        config = RegistrationConfig.professional() if args.professional else None
        add_registration_marks(image_path=args.input, output_path=args.output, color_name=args.color_name, color_index=args.color_index, total_colors=args.total_colors, color_rgb=tuple(args.color_rgb), mark_type=args.mark_type, dpi=args.dpi, border_size=args.border)
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
"""
Registration Marks Generator
============================
يضيف علامات التسجيل (Registration Marks) على الصور لضمان دقة التوافق
بين الشاشات المختلفة في طباعة السيلك سكرين

Types of marks supported:
- Crosshair (نجمة التقاطع) - الأكثر شيوعاً
- Circle + Cross (دائرة مع صليب)
- Corner marks (علامات الزوايا)
- Crop marks (علامات القص)
- Color bars (شريط مقارنة الألوان)
- Color labels (اسم اللون على كل فيلم)
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Tuple, Optional, Literal
from dataclasses import dataclass, field


# =============================================
# Data Classes
# =============================================

@dataclass
class MarkStyle:
    """Style settings for registration marks"""
    color: Tuple[int, int, int] = (0, 0, 0)          # Black by default
    background_color: Tuple[int, int, int] = (255, 255, 255)  # White background
    line_thickness: int = 2
    mark_size: int = 60                                # Size in pixels at 300 DPI
    margin: int = 40                                   # Distance from image edge
    show_circle: bool = True
    show_cross: bool = True
    show_corner_marks: bool = True
    show_crop_marks: bool = True
    show_color_label: bool = True
    show_color_bar: bool = False
    font_size: int = 24


@dataclass
class MarkPosition:
    """Position for a single registration mark"""
    x: int
    y: int
    label: str = ""


@dataclass
class RegistrationConfig:
    """Complete configuration for registration marks"""
    
    # Mark placement
    add_border: bool = True
    border_size: int = 120       # Extra border around image for marks
    
    # Mark types
    mark_type: Literal['full', 'corner', 'side', 'minimal'] = 'full'
    
    # Mark style
    style: MarkStyle = field(default_factory=MarkStyle)
    
    # Labels
    show_film_info: bool = True
    show_screen_angle: bool = False
    
    # DPI
    dpi: int = 300
    
    @classmethod
    def professional(cls) -> 'RegistrationConfig':
        """Professional print shop configuration"""
        return cls(
            add_border=True,
            border_size=150,
            mark_type='full',
            style=MarkStyle(
                mark_size=80,
                margin=50,
                line_thickness=2,
                show_circle=True,
                show_cross=True,
                show_corner_marks=True,
                show_crop_marks=True,
                show_color_label=True,
                show_color_bar=True,
            )
        )
    
    @classmethod
    def minimal(cls) -> 'RegistrationConfig':
        """Minimal configuration for simple prints"""
        return cls(
            add_border=True,
            border_size=100,
            mark_type='minimal',
            style=MarkStyle(
                mark_size=50,
                margin=30,
                line_thickness=2,
                show_circle=True,
                show_cross=True,
                show_corner_marks=False,
                show_crop_marks=True,
                show_color_label=True,
                show_color_bar=False,
            )
        )


# =============================================
# Registration Marks Generator Class
# =============================================

class RegistrationMarksGenerator:
    """
    Generates professional registration marks for screen printing
    
    Usage:
        generator = RegistrationMarksGenerator(dpi=300)
        
        result = generator.add_marks(
            image=mask,
            color_name="Black",
            color_index=1,
            total_colors=4,
            config=RegistrationConfig.professional()
        )
    """
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
    
    # =============================================
    # Main Method
    # =============================================
    
    def add_marks(
        self,
        image: np.ndarray,
        color_name: str = "Color",
        color_index: int = 1,
        total_colors: int = 4,
        color_rgb: Tuple[int, int, int] = (0, 0, 0),
        config: Optional[RegistrationConfig] = None,
    ) -> np.ndarray:
        """
        Add all registration marks to an image
        
        Args:
            image:        Input image (grayscale or RGB)
            color_name:   Name of this color layer (e.g. "Black", "Cyan")
            color_index:  Index of this color (1-based)
            total_colors: Total number of color layers
            color_rgb:    RGB color of this layer for color bar
            config:       RegistrationConfig settings
            
        Returns:
            Image with registration marks added
        """
        if config is None:
            config = RegistrationConfig()
        
        # Convert to RGB if grayscale
        if len(image.shape) == 2:
            canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            canvas = image.copy()
        
        # Add white border for marks
        if config.add_border:
            canvas = self._add_border(canvas, config.border_size)
        
        h, w = canvas.shape[:2]
        style = config.style
        
        # Get mark positions based on type
        positions = self._get_mark_positions(w, h, config)
        
        # Draw marks
        for pos in positions:
            self._draw_registration_mark(canvas, pos.x, pos.y, style)
        
        # Add corner marks
        if style.show_corner_marks:
            self._draw_corner_marks(canvas, config)
        
        # Add crop marks
        if style.show_crop_marks:
            self._draw_crop_marks(canvas, config)
        
        # Add color label
        if style.show_color_label:
            self._draw_color_label(
                canvas,
                color_name,
                color_index,
                total_colors,
                color_rgb,
                config
            )
        
        # Add color bar
        if style.show_color_bar:
            self._draw_color_bar(canvas, color_rgb, config)
        
        return canvas
    
    # =============================================
    # Border
    # =============================================
    
    def _add_border(self, image: np.ndarray, border_size: int) -> np.ndarray:
        """Add white border around image"""
        return cv2.copyMakeBorder(
            image,
            border_size,    # top
            border_size,    # bottom
            border_size,    # left
            border_size,    # right
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255)   # White border
        )
    
    # =============================================
    # Mark Positions
    # =============================================
    
    def _get_mark_positions(
        self,
        w: int,
        h: int,
        config: RegistrationConfig
    ) -> List[MarkPosition]:
        """Get positions for registration marks based on config type"""
        
        margin = config.style.margin
        cx = w // 2
        cy = h // 2
        
        if config.mark_type == 'full':
            # 6 marks: centers of sides + extra top marks
            return [
                # Center of top edge
                MarkPosition(cx, margin, "TC"),
                # Center of bottom edge
                MarkPosition(cx, h - margin, "BC"),
                # Center of left edge
                MarkPosition(margin, cy, "LC"),
                # Center of right edge
                MarkPosition(w - margin, cy, "RC"),
                # 45-degree positions (between corners and center)
                MarkPosition(cx // 2, margin + 10, "TL"),
                MarkPosition(cx + cx // 2, margin + 10, "TR"),
            ]
        
        elif config.mark_type == 'corner':
            # 4 marks at corners only
            return [
                MarkPosition(margin, margin, "TL"),
                MarkPosition(w - margin, margin, "TR"),
                MarkPosition(margin, h - margin, "BL"),
                MarkPosition(w - margin, h - margin, "BR"),
            ]
        
        elif config.mark_type == 'side':
            # 4 marks at center of each side
            return [
                MarkPosition(cx, margin, "T"),
                MarkPosition(cx, h - margin, "B"),
                MarkPosition(margin, cy, "L"),
                MarkPosition(w - margin, cy, "R"),
            ]
        
        elif config.mark_type == 'minimal':
            # 2 marks: top center and bottom center
            return [
                MarkPosition(cx, margin, "T"),
                MarkPosition(cx, h - margin, "B"),
            ]
        
        return []
    
    # =============================================
    # Individual Mark Drawing
    # =============================================
    
    def _draw_registration_mark(
        self,
        canvas: np.ndarray,
        cx: int,
        cy: int,
        style: MarkStyle
    ):
        """
        Draw a single registration mark (crosshair + circle)
        
        الشكل النهائي:
           ─────────
              ╋
           ─────────
        """
        size = style.mark_size // 2
        thickness = style.line_thickness
        color = style.color
        bg = style.background_color
        
        # White background circle (for visibility on any background)
        if style.show_circle:
            cv2.circle(canvas, (cx, cy), size + 5, bg, -1)
        
        # Outer circle
        if style.show_circle:
            cv2.circle(canvas, (cx, cy), size, color, thickness)
        
        # Inner small circle (center dot)
        cv2.circle(canvas, (cx, cy), 4, color, -1)
        
        # Cross lines (horizontal)
        if style.show_cross:
            gap = 8  # Gap around center
            
            # Horizontal left
            cv2.line(
                canvas,
                (cx - size - 15, cy),
                (cx - gap, cy),
                color, thickness
            )
            # Horizontal right
            cv2.line(
                canvas,
                (cx + gap, cy),
                (cx + size + 15, cy),
                color, thickness
            )
            # Vertical top
            cv2.line(
                canvas,
                (cx, cy - size - 15),
                (cx, cy - gap),
                color, thickness
            )
            # Vertical bottom
            cv2.line(
                canvas,
                (cx, cy + gap),
                (cx, cy + size + 15),
                color, thickness
            )
    
    # =============================================
    # Corner Marks
    # =============================================
    
    def _draw_corner_marks(
        self,
        canvas: np.ndarray,
        config: RegistrationConfig
    ):
        """
        Draw L-shaped corner marks at image boundaries
        
        ┌─────
        │
        │
        """
        h, w = canvas.shape[:2]
        b = config.border_size
        style = config.style
        color = style.color
        thickness = style.line_thickness
        length = 40  # Length of corner mark lines
        
        corners = [
            # Top-left
            {
                'h_start': (b - length, b),
                'h_end': (b + length, b),
                'v_start': (b, b - length),
                'v_end': (b, b + length),
            },
            # Top-right
            {
                'h_start': (w - b - length, b),
                'h_end': (w - b + length, b),
                'v_start': (w - b, b - length),
                'v_end': (w - b, b + length),
            },
            # Bottom-left
            {
                'h_start': (b - length, h - b),
                'h_end': (b + length, h - b),
                'v_start': (b, h - b - length),
                'v_end': (b, h - b + length),
            },
            # Bottom-right
            {
                'h_start': (w - b - length, h - b),
                'h_end': (w - b + length, h - b),
                'v_start': (w - b, h - b - length),
                'v_end': (w - b, h - b + length),
            },
        ]
        
        for corner in corners:
            # Horizontal line
            cv2.line(canvas, corner['h_start'], corner['h_end'], color, thickness)
            # Vertical line
            cv2.line(canvas, corner['v_start'], corner['v_end'], color, thickness)
    
    # =============================================
    # Crop Marks
    # =============================================
    
    def _draw_crop_marks(
        self,
        canvas: np.ndarray,
        config: RegistrationConfig
    ):
        """
        Draw crop marks showing trim lines
        
        These show where to cut the paper after printing
        """
        h, w = canvas.shape[:2]
        b = config.border_size
        style = config.style
        color = style.color
        thickness = 1  # Crop marks are always thin
        
        gap = 10     # Gap between mark start and image edge
        length = 25  # Length of crop mark line
        
        # Top-left corner crop marks
        # Horizontal
        cv2.line(canvas, (b - gap - length, b), (b - gap, b), color, thickness)
        # Vertical
        cv2.line(canvas, (b, b - gap - length), (b, b - gap), color, thickness)
        
        # Top-right corner crop marks
        cv2.line(canvas, (w - b + gap, b), (w - b + gap + length, b), color, thickness)
        cv2.line(canvas, (w - b, b - gap - length), (w - b, b - gap), color, thickness)
        
        # Bottom-left corner crop marks
        cv2.line(canvas, (b - gap - length, h - b), (b - gap, h - b), color, thickness)
        cv2.line(canvas, (b, h - b + gap), (b, h - b + gap + length), color, thickness)
        
        # Bottom-right corner crop marks
        cv2.line(canvas, (w - b + gap, h - b), (w - b + gap + length, h - b), color, thickness)
        cv2.line(canvas, (w - b, h - b + gap), (w - b, h - b + gap + length), color, thickness)
    
    # =============================================
    # Color Label
    # =============================================
    
    def _draw_color_label(
        self,
        canvas: np.ndarray,
        color_name: str,
        color_index: int,
        total_colors: int,
        color_rgb: Tuple[int, int, int],
        config: RegistrationConfig
    ):
        """
        Draw color name, index, and color swatch in the bottom border
        
        Example:
        ■ Film 2/4 | BLACK | 300 DPI
        """
        h, w = canvas.shape[:2]
        b = config.border_size
        
        # Convert to PIL for text rendering
        pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        # Try to load font
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Position: bottom-left of canvas
        x = b
        y = h - b + 10
        
        # Color swatch (small colored rectangle)
        swatch_size = 25
        swatch_color = (color_rgb[0], color_rgb[1], color_rgb[2])
        
        # White background for swatch
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=(255, 255, 255))
        # Color swatch
        draw.rectangle([x + 2, y + 2, x + swatch_size - 2, y + swatch_size - 2], fill=swatch_color)
        # Border
        draw.rectangle([x, y, x + swatch_size, y + swatch_size], outline=(0, 0, 0), width=1)
        
        # Text: "Film X/Y | COLOR NAME"
        text_x = x + swatch_size + 10
        text_main = f"Film {color_index}/{total_colors}  |  {color_name.upper()}"
        draw.text((text_x, y + 2), text_main, fill=(0, 0, 0), font=font_large)
        
        # Second line: DPI info
        text_info = f"DPI: {config.dpi}  |  Registration Mark"
        draw.text((text_x, y + 28), text_info, fill=(100, 100, 100), font=font_small)
        
        # Convert back to OpenCV
        canvas[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    # =============================================
    # Color Bar
    # =============================================
    
    def _draw_color_bar(
        self,
        canvas: np.ndarray,
        color_rgb: Tuple[int, int, int],
        config: RegistrationConfig
    ):
        """
        Draw a color reference bar showing gradient from 0% to 100%
        Used to calibrate ink density
        """
        h, w = canvas.shape[:2]
        b = config.border_size
        
        # Position: right side of canvas
        bar_x = w - b + 10
        bar_y = b
        bar_width = 30
        bar_height = h - (2 * b)
        
        # Draw gradient bar from white to full color
        for i in range(bar_height):
            # Progress from 0 (white) to 1 (full color)
            t = i / bar_height
            
            r = int(255 + (color_rgb[0] - 255) * t)
            g = int(255 + (color_rgb[1] - 255) * t)
            b_val = int(255 + (color_rgb[2] - 255) * t)
            
            cv2.line(
                canvas,
                (bar_x, bar_y + i),
                (bar_x + bar_width, bar_y + i),
                (b_val, g, r),  # BGR for OpenCV
                1
            )
        
        # Border around bar
        cv2.rectangle(
            canvas,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (0, 0, 0),
            1
        )
        
        # Labels: 0% and 100%
        cv2.putText(canvas, "0%",
                   (bar_x, bar_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(canvas, "100%",
                   (bar_x, bar_y + bar_height + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)


# =============================================
# Standalone Function - Simple Interface
# =============================================

def add_registration_marks(
    image_path: str,
    output_path: str,
    color_name: str = "Color",
    color_index: int = 1,
    total_colors: int = 1,
    color_rgb: Tuple[int, int, int] = (0, 0, 0),
    mark_type: str = 'full',
    dpi: int = 300,
    border_size: int = 120,
) -> str:
    """
    Simple function to add registration marks to any image
    
    Args:
        image_path:   Path to input image
        output_path:  Path to save result
        color_name:   Name of color layer (e.g. "Black")
        color_index:  Index of this color (1-based)
        total_colors: Total number of colors
        color_rgb:    RGB color tuple for this layer
        mark_type:    'full', 'corner', 'side', or 'minimal'
        dpi:          Image DPI
        border_size:  Size of border to add for marks
        
    Returns:
        Path to saved output image
    
    Example:
        add_registration_marks(
            "design.jpg",
            "design_with_marks.png",
            color_name="Black",
            color_index=1,
            total_colors=4,
        )
    """
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    
    # Configure
    config = RegistrationConfig(
        add_border=True,
        border_size=border_size,
        mark_type=mark_type,
        dpi=dpi,
        style=MarkStyle(
            mark_size=60,
            show_circle=True,
            show_cross=True,
            show_corner_marks=True,
            show_crop_marks=True,
            show_color_label=True,
            show_color_bar=(total_colors > 1),
        )
    )
    
    # Generate marks
    generator = RegistrationMarksGenerator(dpi=dpi)
    result = generator.add_marks(
        image=image,
        color_name=color_name,
        color_index=color_index,
        total_colors=total_colors,
        color_rgb=color_rgb,
        config=config,
    )
    
    # Save result with DPI metadata
    pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    pil_result.save(output_path, dpi=(dpi, dpi))
    
    print(f"✅ Registration marks added: {output_path}")
    return output_path


def add_marks_to_all_films(
    films: List[dict],
    output_dir: str,
    dpi: int = 300,
    mark_type: str = 'full',
    config: Optional[RegistrationConfig] = None,
) -> List[str]:
    """
    Add registration marks to all color films at once
    
    Args:
        films: List of dicts with keys:
               - 'image': np.ndarray
               - 'name': str (color name)
               - 'color': list [R, G, B]
        output_dir: Directory to save results
        dpi: Image DPI
        mark_type: Type of marks
        config: Optional custom config
        
    Returns:
        List of paths to saved files
    
    Example:
        films = [
            {'image': mask1, 'name': 'Black',   'color': [0, 0, 0]},
            {'image': mask2, 'name': 'Cyan',    'color': [0, 188, 212]},
            {'image': mask3, 'name': 'Magenta', 'color': [233, 30, 99]},
            {'image': mask4, 'name': 'Yellow',  'color': [255, 193, 7]},
        ]
        paths = add_marks_to_all_films(films, 'output/')
    """
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if config is None:
        config = RegistrationConfig(
            add_border=True,
            border_size=120,
            mark_type=mark_type,
            dpi=dpi,
        )
    
    generator = RegistrationMarksGenerator(dpi=dpi)
    total_colors = len(films)
    saved_paths = []
    
    print(f"\n🎯 Adding registration marks to {total_colors} films...")
    
    for idx, film in enumerate(films):
        color_index = idx + 1
        color_name = film.get('name', f'Color {color_index}')
        color_rgb = tuple(film.get('color', [0, 0, 0]))
        image = film['image']
        
        print(f"   Processing film {color_index}/{total_colors}: {color_name}")
        
        # Add marks
        result = generator.add_marks(
            image=image,
            color_name=color_name,
            color_index=color_index,
            total_colors=total_colors,
            color_rgb=color_rgb,
            config=config,
        )
        
        # Save
        filename = f"film_{color_index:02d}_{color_name}_with_marks.png"
        filepath = output_dir / filename
        
        pil_result = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        pil_result.save(str(filepath), dpi=(dpi, dpi))
        
        saved_paths.append(str(filepath))
        print(f"   ✅ Saved: {filename}")
    
    print(f"\n✅ All films processed with registration marks!")
    print(f"📁 Output: {output_dir.absolute()}")
    
    return saved_paths


# =============================================
# CLI Interface
# =============================================

if __name__ == '__main__':
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='Add Registration Marks to images for Screen Printing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single image
  python registration_marks.py --input design.jpg --output design_marks.png

  # With color info
  python registration_marks.py \\
      --input black_film.png \\
      --output black_film_marks.png \\
      --color-name "Black" \\
      --color-index 1 \\
      --total-colors 4

  # Minimal marks
  python registration_marks.py \\
      --input film.png \\
      --output film_marks.png \\
      --mark-type minimal

  # Professional full marks
  python registration_marks.py \\
      --input film.png \\
      --output film_marks.png \\
      --mark-type full \\
      --dpi 600 \\
      --border 150
        """
    )
    
    # Input/Output
    parser.add_argument('--input', '-i', required=True,
                        help='Input image path')
    parser.add_argument('--output', '-o', required=True,
                        help='Output image path')
    
    # Color info
    parser.add_argument('--color-name', default='Color',
                        help='Color name (e.g. Black, Cyan)')
    parser.add_argument('--color-index', type=int, default=1,
                        help='Color index (1-based)')
    parser.add_argument('--total-colors', type=int, default=1,
                        help='Total number of colors')
    parser.add_argument('--color-rgb', nargs=3, type=int, default=[0, 0, 0],
                        metavar=('R', 'G', 'B'),
                        help='Color RGB values (e.g. 0 0 0 for black)')
    
    # Mark settings
    parser.add_argument('--mark-type',
                        choices=['full', 'corner', 'side', 'minimal'],
                        default='full',
                        help='Type of registration marks (default: full)')
    parser.add_argument('--dpi', type=int, default=300,
                        help='Image DPI (default: 300)')
    parser.add_argument('--border', type=int, default=120,
                        help='Border size in pixels (default: 120)')
    
    # Profile shortcuts
    parser.add_argument('--professional', action='store_true',
                        help='Use professional print shop settings')
    
    args = parser.parse_args()
    
    # Run
    try:
        config = RegistrationConfig.professional() if args.professional else None
        
        add_registration_marks(
            image_path=args.input,
            output_path=args.output,
            color_name=args.color_name,
            color_index=args.color_index,
            total_colors=args.total_colors,
            color_rgb=tuple(args.color_rgb),
            mark_type=args.mark_type,
            dpi=args.dpi,
            border_size=args.border,
        )
        
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
