"""
vector_marks.py — Vector-based Registration Marks for PDF Export
Virtual Design Silk Screen Studio
"""

import math
from typing import List, Tuple, Optional, Dict
import cv2
import numpy as np

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


def scan_for_registration_marks(image: np.ndarray, 
                                min_size: int = 20, 
                                max_size: int = 100) -> List[Dict]:
    """
    Task 4.2 FIX: Scan image for existing registration marks.
    
    Detects crosshair/circle patterns commonly used as registration marks
    in print-ready images. Returns list of detected mark positions.
    
    Args:
        image: Input image (grayscale or BGR)
        min_size: Minimum mark size in pixels
        max_size: Maximum mark size in pixels
        
    Returns:
        List of dicts with 'x', 'y', 'size', 'confidence' for each detected mark
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binary threshold to isolate dark marks
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    marks = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Filter by size range
        if area < min_size * min_size or area > max_size * max_size:
            continue
            
        # Get bounding box and aspect ratio
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / max(h, 1)
        
        # Registration marks are roughly square (crosshair) or circular
        if 0.7 < aspect < 1.3:
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Calculate circularity (circle = 1.0, crosshair ≈ 0.6-0.8)
                perimeter = cv2.arcLength(cnt, True)
                circularity = 4 * math.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                marks.append({
                    'x': cx,
                    'y': cy,
                    'size': int(math.sqrt(area)),
                    'confidence': circularity,
                    'type': 'circle' if circularity > 0.8 else 'crosshair'
                })
    
    # Sort by confidence (highest first)
    marks.sort(key=lambda m: m['confidence'], reverse=True)
    return marks


def remove_existing_marks(image: np.ndarray, 
                         margin_px: int = 50) -> np.ndarray:
    """
    Remove existing registration marks from image edges.
    Useful when re-processing films that already have marks.
    
    Args:
        image: Input image
        margin_px: Margin around edges to clear
        
    Returns:
        Image with marks removed (whitened in margin areas)
    """
    result = image.copy()
    h, w = result.shape[:2]
    
    # White out margins (where marks are typically placed)
    if len(result.shape) == 3:
        white = (255, 255, 255)
    else:
        white = 255
        
    # Top margin
    result[0:margin_px, :] = white
    # Bottom margin  
    result[h-margin_px:h, :] = white
    # Left margin
    result[:, 0:margin_px] = white
    # Right margin
    result[:, w-margin_px:w] = white
    
    return result
