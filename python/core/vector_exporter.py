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


def _get_angle(p1, p2, p3):
    """Calculate the interior angle at p2 in degrees."""
    v1 = p1 - p2
    v2 = p3 - p2
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-4 or norm2 < 1e-4:
        return 0
    cos_theta = np.dot(v1, v2) / (norm1 * norm2)
    return np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))


def fit_bezier_to_contour(
    contour: np.ndarray,
    smooth_factor: float = 0.25,
    corner_threshold: float = 45.0
) -> List[Tuple]:
    """
    تحويل النقاط (Contour) إلى منحنيات بيزييه (Bezier Curves) احترافية.
    إضافة: الحفاظ على الزوايا الحادة (Sharp Corners) بناءً على corner_threshold.
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
        
        # Senior Optimization: Check if p1 and p2 are "Sharp Corners"
        # If the angle at p1 or p2 is very sharp (e.g. < 45 deg or > 135 deg context dependent)
        # We skip smoothing for that specific segment to keep it linear.
        
        angle1 = _get_angle(p0, p1, p2)
        angle2 = _get_angle(p1, p2, p3)
        
        # If it's a sharp corner, use linear segment (L) instead of Bezier (C)
        # or reduce smooth_factor to 0 for this segment.
        is_corner = angle1 < corner_threshold or angle2 < corner_threshold
        
        current_smooth = 0.0 if (is_corner or smooth_factor == 0) else smooth_factor
        
        if current_smooth == 0:
            commands.append(('L', p2[0], p2[1]))
        else:
            # Catmull-Rom to Bezier conversion
            cp1x = p1[0] + (p2[0] - p0[0]) * current_smooth
            cp1y = p1[1] + (p2[1] - p0[1]) * current_smooth
            cp2x = p2[0] - (p3[0] - p1[0]) * current_smooth
            cp2y = p2[1] - (p3[1] - p1[1]) * current_smooth
            commands.append(('C', cp1x, cp1y, cp2x, cp2y, p2[0], p2[1]))
    
    return commands


def export_vector_pdf(
    masks: List[np.ndarray],
    colors: List[tuple],
    color_names: List[str],
    output_path: Path,
    dpi: int = 300,
    smooth_factor: float = 0.25,
    corner_threshold: float = 45.0,
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
        # 1. Pre-smoothing: تحويل الحواف المشرشرة لحواف منحنية ناعمة (رؤية البرنامج)
        # Senior Fix: Use MORPH_CLOSE to fill tiny gaps without destroying font details
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        bw_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Use a lighter GaussianBlur (3,3) instead of (5,5) to prevent melting fonts
        smoothed = cv2.GaussianBlur(bw_closed, (3, 3), 0)
        _, bw = cv2.threshold(smoothed, 128, 255, cv2.THRESH_BINARY)
        
        # 2. Contour Extraction: استخراج الحواف مع مراعاة الثقوب الداخلية (RETR_CCOMP)
        contours, hierarchy = cv2.findContours(
            bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS
        )
        
        # coordinate transform (defined once, outside the loop)
        def px_to_pdf(px_x, px_y):
            pt_x = draw_x + (px_x / mask_w) * draw_w
            pt_y = draw_y + (1 - px_y / mask_h) * draw_h
            return pt_x, pt_y
        
        for ci, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < min_contour_area:
                continue
            
            # FIX 1: epsilon ديناميكي حسب حجم الـ contour
            # أكبر contour → epsilon أكبر → حواف أنعم
            perimeter = cv2.arcLength(contour, True)
            epsilon = max(1.5, perimeter * 0.004)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) < 3:
                continue
            
            # Bezier curve fitting
            bezier_cmds = fit_bezier_to_contour(approx, smooth_factor, corner_threshold)
            
            if not bezier_cmds:
                continue
            
            # FIX 2: hole detection — inner contours تتملى أبيض
            is_hole = (hierarchy is not None and
                       hierarchy[0][ci][3] != -1)
            if is_hole:
                c.setFillColor(white)
            else:
                c.setFillColor(black)
            
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
                elif cmd[0] == 'L':
                    # FIX 3: handle linear segments (sharp corners)
                    px, py = px_to_pdf(cmd[1], cmd[2])
                    path.lineTo(px, py)
            
            path.close()
            c.drawPath(path, fill=1, stroke=0)
        
        # Reset fill to black after loop
        c.setFillColor(black)
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
