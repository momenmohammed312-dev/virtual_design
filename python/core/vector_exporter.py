"""
vector_exporter.py — High-Quality Vector PDF Export
Uses Bezier curve fitting for smooth edges (no staircase artifacts)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def fit_bezier_to_contour(
    contour: np.ndarray,
    smooth_factor: float = 0.25
) -> List[Tuple]:
    """
    تحويل contour pixel إلى قائمة Bezier curves.
    
    Args:
        contour: numpy array shape (N, 1, 2)
        smooth_factor: مقدار التنعيم (0=لا تنعيم, 1=تنعيم كامل)
    
    Returns:
        قائمة tuples: ('M', x, y) أو ('C', cx1, cy1, cx2, cy2, x, y)
    """
    pts = contour.reshape(-1, 2).astype(float)
    n = len(pts)
    if n < 3:
        return []
    
    commands = [('M', pts[0][0], pts[0][1])]
    
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        
        # Catmull-Rom to Bezier conversion
        cp1x = p1[0] + (p2[0] - p0[0]) * smooth_factor
        cp1y = p1[1] + (p2[1] - p0[1]) * smooth_factor
        cp2x = p2[0] - (p3[0] - p1[0]) * smooth_factor
        cp2y = p2[1] - (p3[1] - p1[1]) * smooth_factor
        
        commands.append(('C', cp1x, cp1y, cp2x, cp2y, p2[0], p2[1]))
    
    return commands


def export_vector_pdf(
    masks: List[np.ndarray],
    colors: List[tuple],
    color_names: List[str],
    output_path: Path,
    dpi: int = 300,
    smooth_factor: float = 0.25,
    min_contour_area: int = 50,
    page_size: str = 'A4',
) -> Path:
    """
    تصدير كل الأفلام في PDF واحد متعدد الصفحات بجودة vector حقيقية.
    
    كل صفحة تحتوي على:
      - اسم الفيلم + اللون (hex)
      - علامات التسجيل
      - الفيلم نفسه كـ vector paths (Bezier curves)
      - شريط المعلومات في الأسفل
    
    Args:
        masks: قائمة binary masks (numpy arrays)
        colors: قائمة ألوان RGB
        color_names: أسماء الألوان
        output_path: مسار حفظ الـ PDF
        dpi: دقة الإخراج
        smooth_factor: مقدار تنعيم الحواف (0.0-0.5)
        min_contour_area: أصغر contour يُرسم (pixels²)
        page_size: 'A4', 'A3', 'LETTER'
    
    Returns:
        Path للملف المحفوظ
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab required: pip install reportlab")
    
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4, A3, letter
    from reportlab.lib.colors import Color, black, white
    from reportlab.lib.units import mm, inch
    
    page_sizes = {'A4': A4, 'A3': A3, 'LETTER': letter}
    page_w, page_h = page_sizes.get(page_size.upper(), A4)
    
    # نقاط PDF في بوصة = pixels / dpi * 72
    def px_to_pt(px: float) -> float:
        return px / dpi * 72.0
    
    c = rl_canvas.Canvas(str(output_path), pagesize=(page_w, page_h))
    
    MARGIN_PT = 40  # هامش في points
    HEADER_PT = 60  # ارتفاع رأس الصفحة
    FOOTER_PT = 50  # ارتفاع تذيل الصفحة
    
    for film_idx, (mask, color_rgb, color_name) in enumerate(
        zip(masks, colors, color_names)
    ):
        if film_idx > 0:
            c.showPage()
        
        mask_h, mask_w = mask.shape[:2]
        
        # حساب المساحة المتاحة للرسم
        available_w = page_w - 2 * MARGIN_PT
        available_h = page_h - HEADER_PT - FOOTER_PT - 2 * MARGIN_PT
        
        # حساب scale للتوافق مع الصفحة
        mask_w_pt = px_to_pt(mask_w)
        mask_h_pt = px_to_pt(mask_h)
        
        scale = min(available_w / mask_w_pt, available_h / mask_h_pt, 1.0)
        
        draw_w = mask_w_pt * scale
        draw_h = mask_h_pt * scale
        
        # موضع رسم الصورة (مركز أفقياً)
        draw_x = MARGIN_PT + (available_w - draw_w) / 2
        draw_y = FOOTER_PT + MARGIN_PT
        
        # ═══ رسم الخلفية البيضاء للفيلم ═══
        c.setFillColor(white)
        c.rect(draw_x, draw_y, draw_w, draw_h, fill=1, stroke=0)
        
        # ═══ رسم الـ vector paths ═══
        _, bw = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(
            bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS
        )
        
        c.setFillColor(black)
        c.setStrokeColor(black)
        
        for ci, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < min_contour_area:
                continue
            
            # Douglas-Peucker simplification
            epsilon = 0.5  # pixels — أصغر = أدق، أكبر = أسلس
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) < 3:
                continue
            
            # Bezier curve fitting
            bezier_cmds = fit_bezier_to_contour(approx, smooth_factor)
            
            if not bezier_cmds:
                continue
            
            # تحويل coordinates: pixel → PDF points
            # PDF: y=0 في الأسفل. Pixel: y=0 في الأعلى
            def px_to_pdf(px_x, px_y):
                pt_x = draw_x + (px_x / mask_w) * draw_w
                pt_y = draw_y + (1 - px_y / mask_h) * draw_h
                return pt_x, pt_y
            
            path = c.beginPath()
            
            for cmd in bezier_cmds:
                if cmd[0] == 'M':
                    px, py = px_to_pdf(cmd[1], cmd[2])
                    path.moveTo(px, py)
                elif cmd[0] == 'C':
                    cx1, cy1 = px_to_pdf(cmd[1], cmd[2])
                    cx2, cy2 = px_to_pdf(cmd[3], cmd[4])
                    ex, ey   = px_to_pdf(cmd[5], cmd[6])
                    path.curveTo(cx1, cy1, cx2, cy2, ex, ey)
            
            path.close()
            c.drawPath(path, fill=1, stroke=0)
        
        # ═══ إطار الفيلم ═══
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(draw_x, draw_y, draw_w, draw_h, fill=0, stroke=1)
        
        # ═══ رأس الصفحة (Header) ═══
        r, g, b = [v / 255.0 for v in color_rgb]
        hex_color = f"#{color_rgb[0]:02X}{color_rgb[1]:02X}{color_rgb[2]:02X}"
        
        # عنوان الفيلم
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(black)
        c.drawString(
            MARGIN_PT,
            page_h - MARGIN_PT - 15,
            f"FILM {film_idx + 1}/{len(masks)}  —  {color_name.upper()}"
        )
        
        # صندوق اللون
        c.setFillColor(Color(r, g, b))
        c.rect(
            page_w - MARGIN_PT - 50,
            page_h - MARGIN_PT - 30,
            40, 25, fill=1, stroke=1
        )
        c.setFillColor(black)
        c.setFont("Helvetica", 9)
        c.drawString(
            page_w - MARGIN_PT - 55,
            page_h - MARGIN_PT - 40,
            hex_color
        )
        
        # ═══ تذيل الصفحة (Footer) ═══
        c.setFont("Helvetica", 8)
        c.setFillColor(black)
        footer_y = MARGIN_PT
        
        # معلومات الفيلم
        c.drawString(MARGIN_PT, footer_y + 30, f"Color: {hex_color}  |  RGB: {color_rgb}")
        c.drawString(MARGIN_PT, footer_y + 18, f"Size: {mask_w}×{mask_h}px  |  DPI: {dpi}")
        
        # رقم الصفحة
        c.setFont("Helvetica", 9)
        c.drawRightString(
            page_w - MARGIN_PT,
            footer_y + 18,
            f"Page {film_idx + 1} of {len(masks)}"
        )
        
        # خط الفاصل
        c.setLineWidth(0.3)
        c.line(MARGIN_PT, footer_y + 10, page_w - MARGIN_PT, footer_y + 10)
        c.line(MARGIN_PT, page_h - HEADER_PT, page_w - MARGIN_PT, page_h - HEADER_PT)
    
    c.save()
    logger.info(f"[VectorExporter] Saved: {output_path} ({len(masks)} films)")
    return output_path
