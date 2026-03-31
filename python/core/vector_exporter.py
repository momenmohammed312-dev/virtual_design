"""
vector_exporter.py — High-Quality Vector PDF Export
Uses Bezier curve fitting for smooth edges (no staircase artifacts)
"""

import cv2
import numpy as np
import math
from pathlib import Path
from typing import List, Tuple, Optional
import logging
import io
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4, A3, letter
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
    corner_threshold: float = 95.0
) -> List[Tuple]:
    """
    Potrace-inspired Bezier fitting with three-phase approach:
    1. Douglas-Peucker simplification (removes staircase noise)
    2. Corner detection via signed curvature (true geometric corners)
    3. Catmull-Rom only on smooth segments between confirmed corners
    """
    pts = contour.reshape(-1, 2).astype(float)
    n = len(pts)
    if n < 3:
        return []

    # STEP 1: Douglas-Peucker polygon simplification (removes staircase noise)
    # epsilon relative to contour perimeter — industry standard
    # Last 5% tweak: dynamic epsilon
    # - TEXT_LOGO: tighter (preserve sharp details)
    # - ARTWORK: looser (reduce polygonization / micro-zigzag)
    perimeter = cv2.arcLength(contour, True)
    is_text_logo_proxy = (smooth_factor <= 1e-6) or (corner_threshold <= 20.0)
    eps_ratio = 0.001 if is_text_logo_proxy else 0.003
    epsilon = max(0.5, perimeter * eps_ratio)
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    pts = simplified.reshape(-1, 2).astype(float)
    n = len(pts)
    if n < 3:
        return []

    # STEP 2: Corner detection via signed curvature (Potrace-style)
    def signed_angle(p0, p1, p2):
        v1 = p1 - p0
        v2 = p2 - p1
        cross = v1[0]*v2[1] - v1[1]*v2[0]
        dot   = v1[0]*v2[0] + v1[1]*v2[1]
        return math.degrees(math.atan2(cross, dot))

    corners = set()
    for i in range(n):
        angle = signed_angle(pts[(i-1)%n], pts[i], pts[(i+1)%n])
        if abs(angle) > (180 - corner_threshold):
            corners.add(i)

    # STEP 3: Catmull-Rom only on smooth segments
    commands = [('M', pts[0][0], pts[0][1])]
    for i in range(n):
        p0 = pts[(i-1)%n]
        p1 = pts[i]
        p2 = pts[(i+1)%n]
        p3 = pts[(i+2)%n]
        is_corner = (i in corners) or ((i+1)%n in corners)
        sf = 0.0 if is_corner else smooth_factor
        if sf == 0:
            commands.append(('L', p2[0], p2[1]))
        else:
            cp1x = p1[0] + (p2[0]-p0[0])*sf
            cp1y = p1[1] + (p2[1]-p0[1])*sf
            cp2x = p2[0] - (p3[0]-p1[0])*sf
            cp2y = p2[1] - (p3[1]-p1[1])*sf
            commands.append(('C', cp1x,cp1y, cp2x,cp2y, p2[0],p2[1]))
    return commands


def export_vector_pdf(
    masks: List[np.ndarray],
    colors: List[tuple],
    color_names: List[str],
    output_path: Path,
    dpi: int = 300,
    smooth_factor: float = 0.2,
    corner_threshold: float = 150.0,
    min_contour_area: int = 50,
    page_size: str = 'A4',
    no_vector_blur: bool = False,
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
        corner_threshold: عتبة للحفاظ على الزوايا الحادة (درجات)
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
        # Senior Fix: Use the mask EXACTLY as it came from preview.
        # Last 5% tweak: enforce hard-binary edges before any vectorization.
        bw = mask.copy()
        if bw.dtype != np.uint8:
            bw = bw.astype(np.uint8)

        # Always enforce hard binary edges (prevents gray quantization artifacts)
        bw = ((bw > 127).astype(np.uint8) * 255)

        # ARTWORK-only: light blur then re-threshold to reduce staircase micro-zigzags.
        # TEXT_LOGO must remain perfectly hard (no blur). We infer TEXT_LOGO when
        # smoothing is ~0 or corner_threshold is very low.
        is_text_logo_proxy = (smooth_factor <= 1e-6) or (corner_threshold <= 20.0)
        if not is_text_logo_proxy:
            bw_blur = cv2.GaussianBlur(bw, (3, 3), 0.5)
            bw = ((bw_blur > 127).astype(np.uint8) * 255)

        
        # 2. Contour Extraction: TC89_KCOS for better curve approximation
        contours, hierarchy = cv2.findContours(
            bw, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS
        )
        
        # coordinate transform (defined once, outside the loop)
        def px_to_pdf(px_x, px_y):
            # --- Phase 20: Unified Path Rendering for Holes ---
            # Instead of drawing one-by-one, we use a single path for ALL contours
            # This allows the Even-Odd fill rule to handle holes perfectly (BMW logo FIX)
            # We need to calculate scale_w and scale_h for the new coordinate transformation
            scale_w = draw_w / mask_w
            scale_h = draw_h / mask_h
            return draw_x + px_x * scale_w, draw_y + (mask_h - px_y) * scale_h
        
        path = c.beginPath()
        # Some reportlab versions don't expose setFillMode() on PDFPathObject.
        # We'll use it when available; otherwise we fall back to hierarchy-based
        # drawing to preserve holes.
        use_even_odd = False
        if hasattr(path, 'setFillMode'):
            path.setFillMode(1) # 1 = Even-Odd fill rule (essential for nested holes)
            use_even_odd = True
        
        min_contour_area = 10 # capture small details
        
        # We need to sort contours by area descending so outer ones come first?
        # Actually with RETR_TREE and Even-Odd, order doesn't matter for pure fill.
        def _append_contour_to_path(target_path, contour_arr):
            area = cv2.contourArea(contour_arr)
            if area < min_contour_area:
                return

            perimeter = cv2.arcLength(contour_arr, True)
            area = cv2.contourArea(contour_arr)

            # Last 5% tweak: dynamic epsilon before Bezier fitting
            # - TEXT_LOGO: tighter
            # - ARTWORK: looser
            eps_ratio = 0.001 if is_text_logo_proxy else 0.003
            epsilon = eps_ratio * perimeter
            approx = cv2.approxPolyDP(contour_arr, epsilon, True)

            
            if len(approx) < 3:
                return
            
            bezier_cmds = fit_bezier_to_contour(approx, smooth_factor, corner_threshold)
            if not bezier_cmds:
                return
            
            for cmd in bezier_cmds:
                if cmd[0] == 'M':
                    px, py = px_to_pdf(cmd[1], cmd[2])
                    target_path.moveTo(px, py)
                elif cmd[0] == 'C':
                    cx1, cy1 = px_to_pdf(cmd[1], cmd[2])
                    cx2, cy2 = px_to_pdf(cmd[3], cmd[4])
                    ex, ey = px_to_pdf(cmd[5], cmd[6])
                    target_path.curveTo(cx1, cy1, cx2, cy2, ex, ey)
                elif cmd[0] == 'L':
                    px, py = px_to_pdf(cmd[1], cmd[2])
                    target_path.lineTo(px, py)
            target_path.close()
        
        if use_even_odd:
            for _, contour in enumerate(contours):
                _append_contour_to_path(path, contour)
            
            c.setFillColor(black)
            c.drawPath(path, fill=1, stroke=0)
        else:
            # Fallback hole handling without even-odd fill:
            # draw outer contours filled black, then draw children (holes) filled white.
            c.setFillColor(black)
            if hierarchy is None:
                for contour in contours:
                    p = c.beginPath()
                    _append_contour_to_path(p, contour)
                    c.drawPath(p, fill=1, stroke=0)
            else:
                h = hierarchy[0]
                for idx in range(len(contours)):
                    parent_idx = h[idx][3]
                    if parent_idx != -1:
                        continue
                    
                    p_outer = c.beginPath()
                    _append_contour_to_path(p_outer, contours[idx])
                    c.drawPath(p_outer, fill=1, stroke=0)
                    
                    child = h[idx][2]
                    while child != -1:
                        c.setFillColor(white)
                        p_hole = c.beginPath()
                        _append_contour_to_path(p_hole, contours[child])
                        c.drawPath(p_hole, fill=1, stroke=0)
                        c.setFillColor(black)
                        child = h[child][0]
        
        # Reset fill settings
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

def render_vector_halftone(canvas, mask, color_rgb, page_h):
    """تحويل نقاط الهافتون لدوائر فيكتور حقيقية"""
    import numpy as np
    # جلب أماكن النقاط السوداء (ink = 0 في الـ mask الأصلي، بنسبة دقة الـ mask)
    points = np.argwhere(mask < 127) 
    
    canvas.setFillColorRGB(0, 0, 0) # رسم النقاط بالأسود للفيلم
    dot_size = 0.8 # حجم النقطة - ممكن تظبطه حسب الـ LPI
    
    for y, x in points:
        # رسم دائرة صغيرة لكل بكسل هافتون
        canvas.circle(x, page_h - y, dot_size, fill=1, stroke=0)

def render_raster_halftone(canvas, mask: np.ndarray, dpi: int, page_w: float, page_h: float) -> None:
    """Embed halftone mask as a high-resolution raster image inside the PDF.

    This is used as a fallback for dense halftone patterns where vector dots become
    too heavy/slow or cause visual artifacts in PDF renderers.
    """
    if mask.dtype != np.uint8:
        mask_u8 = mask.astype(np.uint8)
    else:
        mask_u8 = mask

    if len(mask_u8.shape) == 3:
        mask_u8 = cv2.cvtColor(mask_u8, cv2.COLOR_BGR2GRAY)

    mask_h, mask_w = mask_u8.shape[:2]

    ok, png_bytes = cv2.imencode('.png', mask_u8)
    if not ok:
        raise RuntimeError("Failed to encode halftone mask as PNG")

    from reportlab.lib.utils import ImageReader
    img_reader = ImageReader(io.BytesIO(png_bytes.tobytes()))

    margin_pt = 40.0
    header_pt = 60.0
    footer_pt = 50.0
    available_w = page_w - 2 * margin_pt
    available_h = page_h - header_pt - footer_pt - 2 * margin_pt

    img_w_pt = (mask_w / max(1, dpi)) * 72.0
    img_h_pt = (mask_h / max(1, dpi)) * 72.0
    scale = min(available_w / img_w_pt, available_h / img_h_pt, 1.0)

    draw_w = img_w_pt * scale
    draw_h = img_h_pt * scale
    draw_x = margin_pt + (available_w - draw_w) / 2
    draw_y = footer_pt + margin_pt

    canvas.drawImage(img_reader, draw_x, draw_y, width=draw_w, height=draw_h, mask='auto')