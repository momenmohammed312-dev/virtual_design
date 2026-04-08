"""
Vector PDF Exporter for Silk Screen Masks.
Generates print-ready PDF with vector paths, registration marks, and professional print specifications.
FIXED: Consistent 1:1 scaling across all masks with proper centering.
NEW: Professional fit-to-page scaling with configurable modes.
"""

import cv2
import numpy as np
import math
import io
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Literal
import logging
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4, A3, letter

# Scale modes for artwork rendering
ScaleMode = Literal["fit_to_page", "actual_size", "custom_scale"]

# Default configuration
DEFAULT_MARGIN_PT = 65  # Professional margin for marks
DEFAULT_HEADER_PT = 60
DEFAULT_FOOTER_PT = 60
MIN_MARGIN_PT = 20  # Minimum safe margin
MAX_SCALE_PERCENT = 500  # Maximum 5x upscaling

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
    smooth_factor: float = 0.35,
    corner_threshold: float = 120.0,
    image_class: str = 'auto',
    epsilon: Optional[float] = None
) -> List[Tuple]:
    """
    Potrace-inspired Bezier fitting with three-phase approach:
    1. SMART Simplification (adaptive epsilon based on contour area)
    2. Corner detection via signed curvature (true geometric corners)
    3. Catmull-Rom only on smooth segments between confirmed corners
    """
    pts = contour.reshape(-1, 2).astype(float)
    n = len(pts)
    if n < 3:
        return []

    # STEP 1: SMART Douglas-Peucker simplification (adaptive epsilon)
    perimeter = cv2.arcLength(contour, True)
    area = abs(cv2.contourArea(contour))
    
    def signed_angle(p0, p1, p2):
        v1 = p1 - p0
        v2 = p2 - p1
        cross = v1[0]*v2[1] - v1[1]*v2[0]
        dot   = v1[0]*v2[0] + v1[1]*v2[1]
        return math.degrees(math.atan2(cross, dot))

    def compute_adaptive_epsilon(cnt, img_class):
        perimeter = cv2.arcLength(cnt, True)
        area = cv2.contourArea(cnt)

        if area < 1:
            return 0.0

        scale = np.sqrt(area)
        base = 0.002

        if img_class == "text_logo":
            return base * 0.4 * scale
        else:
            return base * 1.25 * scale

    if epsilon is None:
        epsilon = compute_adaptive_epsilon(contour, image_class)
    
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    pts = simplified.reshape(-1, 2).astype(float)
    n = len(pts)
    if n < 3:
        return []

    def _is_corner(p0, p1, p2, threshold_degrees: float = 120.0) -> bool:
        v1 = p1 - p0
        v2 = p2 - p1
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-4 or norm2 < 1e-4:
            return False
        cos_theta = np.dot(v1, v2) / (norm1 * norm2)
        interior_angle = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))
        return interior_angle < threshold_degrees

    corners = set()
    for i in range(n):
        p0 = pts[(i-1)%n]
        p1 = pts[i]
        p2 = pts[(i+1)%n]
        if _is_corner(p0, p1, p2, corner_threshold):
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


def preprocess_mask_for_vector(mask: np.ndarray, apply_blur: bool = False, smooth_factor: float = 0.0) -> np.ndarray:
    """
    Prepares a binary mask for vector tracing.
    1. Upscales by 2x for subpixel precision.
    2. Optional Gaussian Blur to 'melt' pixelation artifacts (essential for small logos).
    3. Re-binarizes to maintain sharp edges.
    """
    # 1) upscale (subpixel support)
    bw = cv2.resize(mask, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)

    # Use a higher threshold for applying strong blur
    # Note: smooth_factor here is expected to be in 0.0-1.0 range
    if apply_blur or smooth_factor > 0.4:
        # 2) float smoothing (critical for artwork to melt artifacts)
        bw = bw.astype(np.float32) / 255.0
        
        # Determine blur strength: higher smoothing_factor -> larger kernel / sigma
        if smooth_factor > 0.6:
            k_size = (5, 5)
            sigma = 1.0
        elif smooth_factor > 0.4:
            k_size = (3, 3)
            sigma = 0.8
        else:
            k_size = (3, 3)
            sigma = 0.5
            
        bw = cv2.GaussianBlur(bw, k_size, sigma)
        
        # 3) threshold back
        # Use a slightly lower threshold if smooth_factor is very high to avoid eroding thin lines
        thresh_val = 0.5 if smooth_factor < 0.7 else 0.45
        _, bw = cv2.threshold(bw, thresh_val, 1.0, cv2.THRESH_BINARY)
        bw = (bw * 255).astype(np.uint8)
    else:
        # Zero blur for TEXT_LOGO, keep sharp
        _, bw = cv2.threshold(bw, 127, 255, cv2.THRESH_BINARY)

    return bw


def compute_adaptive_smooth(
    contour: np.ndarray,
    base_smooth: float,
    image_class: str = 'auto'
) -> float:
    """
    Compute per-contour smoothing factor.
    
    Rules:
    - Very small contours (area < 200): minimal smoothing (preserve detail)
    - Medium contours (200-2000): moderate smoothing
    - Large contours (> 2000): full base_smooth
    - Complex contours (high perimeter/area ratio): reduce smoothing by 30%
    - text_logo class: cap at 0.3 to preserve letter shapes
    - photo class: always use base_smooth unchanged
    """
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    
    # Complexity ratio (circle=1, jagged=high)
    if area > 0:
        complexity = (perimeter ** 2) / (4 * math.pi * area)
    else:
        complexity = 1.0
    
    # Size-based scaling
    if area < 200:
        size_factor = 0.3
    elif area < 2000:
        size_factor = 0.3 + 0.7 * ((area - 200) / 1800)
    else:
        size_factor = 1.0
    
    # Complexity penalty
    complexity_factor = 1.0
    if complexity > 3.0:
        complexity_factor = 0.7
    elif complexity > 6.0:
        complexity_factor = 0.5
    
    adaptive = base_smooth * size_factor * complexity_factor
    
    # Class-specific caps
    if image_class == 'text_logo':
        adaptive = min(adaptive, 0.3)
    elif image_class == 'photo':
        adaptive = base_smooth  # no scaling for photos
    
    return max(0.05, min(adaptive, 0.5))


def export_vector_pdf(
    masks: List[np.ndarray],
    colors: List[tuple],
    color_names: List[str],
    output_path: Path,
    dpi: int = 300,
    smooth_factor: float = 0.2,
    corner_threshold: float = 120.0,
    min_contour_area: int = 50,
    page_size: str = 'A4',
    no_vector_blur: bool = False,
    image_class: str = 'auto',
    epsilon: Optional[float] = None,
    job_name: Optional[str] = None,
    is_halftone: bool = False,
    args = None
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
    
    # Import print calibration for 1:1 scaling
    try:
        from .print_calibration import get_calibration
        calib = get_calibration(dpi)
        logger.info(f"Using calibrated scaling: {calib.pixels_per_mm:.1f} px/mm @ {dpi} DPI")
    except ImportError:
        calib = None
    
    from .vector_marks import draw_vector_registration_mark, add_vector_marks_to_page
    
    # ─────────────────────────────────────────────────────────────────────────
    # 🔥 NEW: Professional Fit-to-Page Scaling System
    # ─────────────────────────────────────────────────────────────────────────
    
    # Get configuration from args or use defaults
    scale_mode: ScaleMode = getattr(args, 'scale_mode', 'fit_to_page')
    custom_scale_percent = getattr(args, 'custom_scale_percent', 100.0)
    margin_pt = getattr(args, 'margin_pt', DEFAULT_MARGIN_PT)
    
    # Ensure minimum margins
    margin_pt = max(margin_pt, MIN_MARGIN_PT)
    
    page_sizes = {'A4': A4, 'A3': A3, 'LETTER': letter}
    page_w, page_h = page_sizes.get(page_size.upper(), A4)
    
    # Log page setup
    logger.info(f"[VectorExporter] Page setup: {page_size} = {page_w:.1f}pt x {page_h:.1f}pt "
               f"({page_w/72*25.4:.1f}mm x {page_h/72*25.4:.1f}mm)")
    logger.info(f"[VectorExporter] Scale mode: {scale_mode}, margin: {margin_pt}pt, DPI: {dpi}")
    
    # Professional 1:1 scaling: pixels to points with calibration
    def px_to_pt(px: float) -> float:
        if calib:
            mm = calib.pixels_to_mm(px)
            return mm * 72.0 / 25.4  # mm to points
        else:
            return px / dpi * 72.0
    
    def px_to_mm(px: float) -> float:
        if calib:
            return calib.pixels_to_mm(px)
        else:
            return px / dpi * 25.4
    
    if (corner_threshold or 0.0) > 150.0:
        logger.info(f"[VectorExporter] Applying Hard-Corner Logic (Threshold: {corner_threshold:.1f})")
    
    c = rl_canvas.Canvas(str(output_path), pagesize=(page_w, page_h))
    
    # Calculate printable area (consistent for all films)
    printable_w = page_w - 2 * margin_pt
    printable_h = page_h - 2 * margin_pt
    
    logger.info(f"[VectorExporter] Printable area: {printable_w:.1f}pt x {printable_h:.1f}pt "
               f"({printable_w/72*25.4:.1f}mm x {printable_h/72*25.4:.1f}mm)")
    
    # Compute scale factor once (for multi-film consistency)
    # Use first mask to determine artwork bounds
    first_mask = masks[0] if masks else None
    if first_mask is not None:
        first_h, first_w = first_mask.shape[:2]
        artwork_w_pt = px_to_pt(first_w)
        artwork_h_pt = px_to_pt(first_h)
        artwork_w_mm = px_to_mm(first_w)
        artwork_h_mm = px_to_mm(first_h)
        
        logger.info(f"[VectorExporter] Original artwork: {first_w}x{first_h}px = "
                   f"{artwork_w_mm:.1f}mm x {artwork_h_mm:.1f}mm")
        
        # Calculate scale factor based on mode
        if scale_mode == 'actual_size':
            scale_factor = 1.0
            logger.info(f"[VectorExporter] Scale mode: actual_size (1:1, no scaling)")
            
        elif scale_mode == 'custom_scale':
            scale_factor = custom_scale_percent / 100.0
            logger.info(f"[VectorExporter] Scale mode: custom_scale ({custom_scale_percent}%)")
            
        else:  # fit_to_page (default)
            # Calculate scale to fit within printable area
            scale_w = printable_w / artwork_w_pt if artwork_w_pt > 0 else 1.0
            scale_h = printable_h / artwork_h_pt if artwork_h_pt > 0 else 1.0
            scale_factor = min(scale_w, scale_h)
            
            # Clamp to reasonable limits
            scale_factor = min(scale_factor, MAX_SCALE_PERCENT / 100.0)
            scale_factor = max(scale_factor, 0.1)  # Minimum 10%
            
            logger.info(f"[VectorExporter] Scale mode: fit_to_page, computed scale: {scale_factor:.2f}x "
                       f"(w_ratio={scale_w:.2f}, h_ratio={scale_h:.2f})")
        
        final_w_pt = artwork_w_pt * scale_factor
        final_h_pt = artwork_h_pt * scale_factor
        final_w_mm = artwork_w_mm * scale_factor
        final_h_mm = artwork_h_mm * scale_factor
        
        logger.info(f"[VectorExporter] Final render size: {final_w_pt:.1f}pt x {final_h_pt:.1f}pt "
                   f"({final_w_mm:.1f}mm x {final_h_mm:.1f}mm)")
    else:
        scale_factor = 1.0
        logger.warning("[VectorExporter] No masks provided, using default scale=1.0")
    
    MARGIN_PT = margin_pt  # Use configured margin
    
    for film_idx, (mask, color_rgb, color_name) in enumerate(
        zip(masks, colors, color_names)
    ):
        if film_idx > 0:
            c.showPage()
        
        mask_h, mask_w = mask.shape[:2]
        
        # Convert mask dimensions to points
        mask_w_pt = px_to_pt(mask_w)
        mask_h_pt = px_to_pt(mask_h)
        
        # Apply consistent scale factor
        draw_w = mask_w_pt * scale_factor
        draw_h = mask_h_pt * scale_factor
        
        # 🎯 AUTO-CENTERING: Perfectly center design on film page
        draw_x = margin_pt + (printable_w - draw_w) / 2
        draw_y = margin_pt + (printable_h - draw_h) / 2
        
        # Log per-film positioning (debug only, not to spam)
        if film_idx == 0:
            logger.info(f"[VectorExporter] Film {film_idx+1} position: ({draw_x:.1f}, {draw_y:.1f})pt, "
                       f"size: ({draw_w:.1f}, {draw_h:.1f})pt")
        else:
            logger.debug(f"[VectorExporter] Film {film_idx+1} using identical positioning")
        
        # ─── Professional Print Specs Table (Top Right) ───
        c.setFont("Helvetica", 8)
        c.drawRightString(page_w - MARGIN_PT, page_h - MARGIN_PT + 35, f"MESH: 160 T/I")
        c.drawRightString(page_w - MARGIN_PT, page_h - MARGIN_PT + 25, f"LPI: 55 | ANGLE: 45°")
        
        # ─── Symmetric Registration Marks ───
        film_info = {'job_name': job_name or output_path.stem}
        add_vector_marks_to_page(c, page_w, page_h, MARGIN_PT, color_rgb, color_name, film_info)
        
        # ─── Background rectangle (white, invisible in print but good for PDF preview) ───
        c.setFillColorRGB(1, 1, 1)
        c.rect(draw_x, draw_y, draw_w, draw_h, fill=1, stroke=0)
        
        # ─── Advanced Vector Path Generation ───
        # 🔥 Smart Smoothing: Adjust smooth_factor based on scale to prevent artifacts
        # When upscaling significantly, reduce smoothing to preserve sharp edges
        adjusted_smooth = smooth_factor
        if scale_factor > 2.0:
            # Reduce smoothing proportionally to scale factor
            # At 5x scale, smoothing should be ~20% of original
            scale_reduction = min(1.0, 2.0 / scale_factor)  # 2.0/4.94 ≈ 0.4
            adjusted_smooth = smooth_factor * scale_reduction
            logger.info(f"[VectorExporter] Scale-aware smoothing: {smooth_factor} → {adjusted_smooth:.3f} "
                       f"(scale={scale_factor:.2f}x, reduction={scale_reduction:.2f})")
        
        if image_class == 'text_logo' and adjusted_smooth < 0.2:
            bw = preprocess_mask_for_vector(mask, apply_blur=False, smooth_factor=adjusted_smooth)
        else:
            bw = preprocess_mask_for_vector(mask, apply_blur=True, smooth_factor=adjusted_smooth)
        
        # Ensure CV_8UC1 format for findContours
        if bw.dtype != np.uint8:
            bw = (bw * 255).astype(np.uint8)
        if len(bw.shape) == 3:
            bw = cv2.cvtColor(bw, cv2.COLOR_BGR2GRAY)
        
        # Ensure ink=BLACK(0) for contour tracing
        # preprocess_mask_for_vector uses THRESH_BINARY which preserves input polarity
        # But findContours traces WHITE(255) regions — so we need design=WHITE, background=BLACK
        # This is INVERTED from silk screen convention, only for the purpose of contour detection
        bw_for_contours = cv2.bitwise_not(bw)
        
        contours, hierarchy = cv2.findContours(
            bw_for_contours, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
        )
        
        def px_to_pdf(px_x, px_y):
            # Scale down to original pixels before converting to PDF points
            # 2.0 comes from the pre-processing upscale
            px_x = px_x / 2.0
            px_y = px_y / 2.0
            scale_w = draw_w / mask_w
            scale_h = draw_h / mask_h
            return draw_x + px_x * scale_w, draw_y + (mask_h - px_y) * scale_h
        
        path = c.beginPath()
        use_even_odd = False
        if hasattr(path, 'setFillMode'):
            path.setFillMode(1)
            use_even_odd = True
        
        def _append_contour_to_path(target_path, contour_arr):
            area = cv2.contourArea(contour_arr)
            if area < min_contour_area or len(contour_arr) < 3:
                return
            
            # 🔥 Use adjusted_smooth (scale-aware) instead of original smooth_factor
            adaptive_smooth = compute_adaptive_smooth(
                contour_arr, adjusted_smooth, image_class
            )
            
            # 🔥 Scale-aware epsilon: reduce epsilon for high upscales to preserve detail
            adjusted_epsilon = epsilon
            if scale_factor > 2.0 and epsilon is not None:
                epsilon_reduction = min(1.0, 2.0 / scale_factor)
                adjusted_epsilon = epsilon * epsilon_reduction
            
            bezier_cmds = fit_bezier_to_contour(
                contour_arr, 
                adaptive_smooth, 
                corner_threshold, 
                image_class,
                epsilon=adjusted_epsilon
            )
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
        
        # 🔗 EVEN-ODD FILL: Handles holes (like inside "O" or "0") correctly
        if use_even_odd:
            for contour in contours:
                _append_contour_to_path(path, contour)
            c.setFillColorRGB(0, 0, 0)
            c.drawPath(path, fill=1, stroke=0)
        else:
            # Fallback for older reportlab without even-odd (loop-based hole subtract)
            c.setFillColorRGB(0, 0, 0)
            if hierarchy is None:
                for contour in contours:
                    p = c.beginPath()
                    _append_contour_to_path(p, contour)
                    c.drawPath(p, fill=1, stroke=0)
            else:
                h = hierarchy[0]
                for idx in range(len(contours)):
                    if h[idx][3] != -1: continue # Only process outer shapes
                    p_outer = c.beginPath()
                    _append_contour_to_path(p_outer, contours[idx])
                    c.drawPath(p_outer, fill=1, stroke=0)
                    
                    child = h[idx][2]
                    while child != -1:
                        c.setFillColorRGB(1, 1, 1) # Set to White (Hole)
                        p_hole = c.beginPath()
                        _append_contour_to_path(p_hole, contours[child])
                        c.drawPath(p_hole, fill=1, stroke=0)
                        c.setFillColorRGB(0, 0, 0) # Back to Black
                        child = h[child][0]
        
        # Title and Page Numbers (Footer Specs)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)
        # Left: Film info
        c.drawString(MARGIN_PT, MARGIN_PT - 15, f"FILM {film_idx+1}: {color_name}  |  DPI: {dpi}")
        # Right: Brand name and page
        brand_text = f"Virtual Design Studio | {job_name or 'Untitled'} | Page {film_idx+1}/{len(masks)}"
        c.drawRightString(page_w - MARGIN_PT, MARGIN_PT - 15, brand_text)
    
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

    # 🔥 FIX: Use 1:1 scaling to respect paper size (image grows with page size)
    # If image is larger than available space, scale down to fit. Otherwise use 1:1.
    scale_x = available_w / img_w_pt
    scale_y = available_h / img_h_pt
    scale = min(scale_x, scale_y, 1.0)  # Only scale DOWN, never scale UP (1:1 max)

    draw_w = img_w_pt * scale
    draw_h = img_h_pt * scale
    draw_x = margin_pt + (available_w - draw_w) / 2
    draw_y = footer_pt + margin_pt

    canvas.drawImage(img_reader, draw_x, draw_y, width=draw_w, height=draw_h, mask='auto')