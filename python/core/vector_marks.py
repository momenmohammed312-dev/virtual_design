"""
vector_marks.py — Vector-based Registration Marks for PDF Export
Virtual Design Silk Screen Studio
"""

import math
from typing import List, Tuple

def draw_vector_registration_mark(canvas, x: float, y: float, size: float = 30):
    """Draw a professional vector registration mark (crosshair + circle)."""
    canvas.setLineWidth(0.5)
    canvas.setStrokeColorRGB(0, 0, 0)
    
    # 1. Circle
    canvas.circle(x, y, size * 0.4, fill=0, stroke=1)
    
    # 2. Crosshair
    canvas.line(x - size * 0.6, y, x + size * 0.6, y)
    canvas.line(x, y - size * 0.6, x, y + size * 0.6)
    
    # 3. Inner solid circle (optional for high-precision alignment)
    canvas.circle(x, y, 1.0, fill=1, stroke=0)

def draw_vector_color_bar(canvas, x: float, y: float, colors: List[Tuple], size: float = 15):
    """Draw a vector color bar (swatches) for the film set."""
    for i, rgb in enumerate(colors):
        r, g, b = [v / 255.0 for v in rgb]
        canvas.setFillColorRGB(r, g, b)
        canvas.rect(x + i * (size + 5), y, size, size, fill=1, stroke=1)
    
    canvas.setFillColorRGB(0, 0, 0) # Reset to black

def add_vector_marks_to_page(canvas, page_w: float, page_h: float, margin: float, color_rgb: Tuple, color_name: str, film_info: dict):
    """Add all registration and info marks to a PDF page."""
    # 1. Corners Crosshairs
    draw_vector_registration_mark(canvas, margin, margin) # Bottom Left
    draw_vector_registration_mark(canvas, page_w - margin, margin) # Bottom Right
    draw_vector_registration_mark(canvas, margin, page_h - margin) # Top Left
    draw_vector_registration_mark(canvas, page_w - margin, page_h - margin) # Top Right
    
    # 2. Centered Crosshairs (Sides)
    draw_vector_registration_mark(canvas, page_w / 2, margin) # Bottom Center
    draw_vector_registration_mark(canvas, page_w / 2, page_h - margin) # Top Center
    
    # 3. Job Info (Top Center)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawCentredString(page_w / 2, page_h - margin + 20, f"FILM: {color_name.upper()}  |  JOB: {film_info.get('job_name', 'UNTITLED')}")
    
    # 4. Calibration Scale (10cm ruler for physical verification)
    canvas.setLineWidth(0.3)
    ruler_x = margin + 50
    ruler_y = margin - 15
    canvas.line(ruler_x, ruler_y, ruler_x + 100 * 72/25.4, ruler_y) # 100mm = 10cm
    for i in range(11): # 0 to 10 cm
        tick_x = ruler_x + (i * 10) * 72/25.4
        canvas.line(tick_x, ruler_y, tick_x, ruler_y + (5 if i % 5 == 0 else 3))
        if i % 5 == 0:
            canvas.setFont("Helvetica", 6)
            canvas.drawCentredString(tick_x, ruler_y - 8, f"{i}cm")
