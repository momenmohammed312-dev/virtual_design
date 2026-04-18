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
        
        # Check if this segment is part of a corner
        is_corner = (i in corners) or ((i+1)%n in corners)
        
        # FIX: [1d] Scale-aware minimum segment length
        # Increased threshold from 2.0 to 4.5 for more stability at high scales
        seg_len = np.linalg.norm(p2 - p1)
        min_seg_for_curve = max(2.0, 3.0 / max(smooth_factor, 0.01))
        if seg_len < min_seg_for_curve:
            sf = 0.0 # Force line for short segments
        else:
            sf = 0.0 if is_corner else smooth_factor
            
            # Additional check: if the segment is turning sharply, 
            # reduce sf to prevent overshooting (spikes)
            angle_p1p2 = _get_angle(p0, p1, p2)
            angle_p2p3 = _get_angle(p1, p2, p3)
            # If turning more than 30 deg at either knot, dampen tension
            if angle_p1p2 < 150 or angle_p2p3 < 150:
                sf *= 0.4 # More aggressive dampening
            # Extreme case: very sharp turns get even less tension
            if angle_p1p2 < 120 or angle_p2p3 < 120:
                sf *= 0.25
            
        if sf <= 0.01:
            commands.append(('L', p2[0], p2[1]))
        else:
            # Traditional Catmull-Rom
            cp1x = p1[0] + (p2[0]-p0[0])*sf
            cp1y = p1[1] + (p2[1]-p0[1])*sf
            cp2x = p2[0] - (p3[0]-p1[0])*sf
            cp2y = p2[1] - (p3[1]-p1[1])*sf
            commands.append(('C', cp1x,cp1y, cp2x,cp2y, p2[0],p2[1]))
    return commands


def preprocess_mask_for_vector(mask: np.ndarray, apply_blur: bool = False, smooth_factor: float = 0.0, image_class: str = 'auto') -> Tuple[np.ndarray, float]:
    """
    Prepares a binary mask for vector tracing.
    1. Conditionally upscales by 2x for subpixel precision (only if mask < 800px).
    2. Optional Gaussian Blur to 'melt' pixelation artifacts (essential for small logos).
    3. Re-binarizes to maintain sharp edges.

    Returns:
        Tuple of (processed_mask, upsample_factor)
    """
    max_dim = max(mask.shape[0], mask.shape[1])
    # NEW FIX: Mask-specific noise removal (Essential for clean vector edges)
    # Remove small non-contiguously connected noise pixels
    if max_dim < 3000:
        kernel_noise = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_noise)
    
    # 1) upscale (subpixel support) for small masks only
    if max_dim < 1200:
        bw = cv2.resize(mask, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_LANCZOS4)
        upsample_factor = 2.5
        logger.debug(f"[Preprocess] Upscaling small mask {mask.shape} -> {bw.shape} (Lanczos4)")
    else:
        bw = mask.copy()
        upsample_factor = 1.0

    # FIX: [1b] For text_logo: bilateral only, no Gaussian (preserves edges)
    if image_class == 'text_logo' and smooth_factor > 0.05:
        # USE BILATERAL FILTER TO PRESERVE EDGES WHILE SMOOTHING NOISE
        bw_u8 = bw.astype(np.uint8) if bw.dtype != np.uint8 else bw
        sigma_color = 50 + int(smooth_factor * 150)  # 50-125
        bw_u8 = cv2.bilateralFilter(bw_u8, 9, sigma_color, sigma_color)
        _, bw = cv2.threshold(bw_u8, 127, 255, cv2.THRESH_BINARY)
    elif apply_blur or smooth_factor > 0.05:
        # 2) float smoothing (critical for artwork to melt artifacts)
        bw_f = bw.astype(np.float32) / 255.0
        
        # Determine blur strength based on smooth_factor
        if smooth_factor > 0.6:
            k_size = (7, 7)
            sigma = 1.5
        elif smooth_factor > 0.4:
            k_size = (5, 5)
            sigma = 1.1
        elif smooth_factor > 0.2:
            k_size = (3, 3)
            sigma = 0.8
        else:
            k_size = (3, 3)
            sigma = 0.4 # Subtler blur for low smooth factor
            
        bw_f = cv2.GaussianBlur(bw_f, k_size, sigma)
        
        # 3) threshold back
        thresh_val = 0.5 if smooth_factor < 0.7 else 0.45
        _, bw = cv2.threshold(bw_f, thresh_val, 1.0, cv2.THRESH_BINARY)
        bw = (bw * 255).astype(np.uint8)
    else:
        _, bw = cv2.threshold(bw, 127, 255, cv2.THRESH_BINARY)
        
    # APPLY MORPHOLOGICAL CLOSING BEFORE CONTOUR EXTRACTION (Solid mode fix)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)

    return bw, upsample_factor


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
    args = None,
    # FIX GROUP 5.5: Add runtime print parameters
    lpi: int = 45,
    angle: float = 45.0,
    mesh_count: int = 160,
    mask_dpi: Optional[int] = None,
) -> Path:
    """
    Export all films as multi-page PDF with true vector quality.

    Each page contains:
      - Film name + color (hex)
      - Registration marks
      - Film as vector paths (Bezier curves)
      - Info bar at bottom

    Args:
        masks: List of binary masks (numpy arrays)
        colors: List of RGB colors
        color_names: Color names
        output_path: Path to save PDF
        dpi: Output resolution
        smooth_factor: Edge smoothing amount (0.0-0.5)
        corner_threshold: Threshold to preserve sharp corners (degrees)
        min_contour_area: Smallest contour to draw (pixels²)
        page_size: 'A4', 'A3', 'LETTER'

    Returns:
        Path to saved file
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
    
    # --- PAGE DETERMINATION ---
    custom_w_mm = getattr(args, 'page_width', 0)
    custom_h_mm = getattr(args, 'page_height', 0)
    fit_to_artwork = getattr(args, 'fit_artwork', False)
    
    page_sizes = {'A4': A4, 'A3': A3, 'LETTER': letter}
    
    if fit_to_artwork and masks:
        # Determine exact artwork size
        m_h, m_w = masks[0].shape[:2]
        effective_dpi = mask_dpi if mask_dpi is not None else dpi
        artwork_w_pt = (m_w / effective_dpi * 72.0) + (2 * margin_pt)
        artwork_h_pt = (m_h / effective_dpi * 72.0) + (2 * margin_pt)
        page_w, page_h = artwork_w_pt, artwork_h_pt
        page_size = f"Custom (Fit Artwork: {m_w}x{m_h}px)"
        
    elif custom_w_mm > 0 and custom_h_mm > 0:
        page_w = custom_w_mm * 72.0 / 25.4
        page_h = custom_h_mm * 72.0 / 25.4
        page_size = f"Custom ({custom_w_mm}x{custom_h_mm}mm)"
        
    else:
        page_w, page_h = page_sizes.get(page_size.upper(), A4)
    
    # Log page setup
    logger.info(f"[VectorExporter] Page setup: {page_size} = {page_w:.1f}pt x {page_h:.1f}pt "
               f"({page_w/72*25.4:.1f}mm x {page_h/72*25.4:.1f}mm)")
    logger.info(f"[VectorExporter] Scale mode: {scale_mode}, margin: {margin_pt}pt, DPI: {dpi}")
    
    # 🎯 NEW: Physical Sizing & Scaling Engine
    # Standardize on 'mm' as the internal unit of truth
    
    # 1. Determine Source Size in MM
    # We use source_dpi to understand how many mm the pixels represent
    source_dpi = getattr(args, 'source_dpi', dpi) or dpi
    
    first_mask = masks[0] if masks else None
    if first_mask is not None:
        first_h, first_w = first_mask.shape[:2]
        src_w_mm = first_w / source_dpi * 25.4
        src_h_mm = first_h / source_dpi * 25.4
        logger.info(f"[VectorExporter] Source Artwork: {first_w}x{first_h}px @ {source_dpi} DPI = {src_w_mm:.1f}mm x {src_h_mm:.1f}mm")
        
        # 2. Identify Scaling Mode
        scale_mode = getattr(args, 'scale_mode', 'fit_to_page')
        target_width_mm = getattr(args, 'target_width_mm', 0)
        
        # 3. Compute Final Scale Factor (relative to source mm)
        if target_width_mm > 0:
            scale_factor = target_width_mm / src_w_mm
        elif scale_mode == 'actual_size':
            scale_factor = 1.0
        elif scale_mode == 'custom_scale':
            scale_factor = getattr(args, 'custom_scale_percent', 100.0) / 100.0
        else: # fit_to_page
            printable_w_mm = (page_w - 2 * margin_pt) * 25.4 / 72.0
            printable_h_mm = (page_h - 2 * margin_pt) * 25.4 / 72.0
            scale_factor = min(printable_w_mm / src_w_mm, printable_h_mm / src_h_mm)
            
            # Capping: Don't blow up tiny logos unless explicit
            if 'scale_mode' not in getattr(args, 'overrides', []):
                if scale_factor > 2.0: scale_factor = 2.0

        final_w_mm = src_w_mm * scale_factor
        final_h_mm = src_h_mm * scale_factor
        logger.info(f"[VectorExporter] Final Print Size: {final_w_mm:.1f}mm x {final_h_mm:.1f}mm (Scale: {scale_factor:.2f}x)")
    else:
        scale_factor = 1.0

    def px_to_pt(px: float) -> float:
        return px / source_dpi * 72.0
    
    def px_to_mm(px: float) -> float:
        return px / source_dpi * 25.4

    if (corner_threshold or 0.0) > 150.0:
        logger.info(f"[VectorExporter] Applying Hard-Corner Logic (Threshold: {corner_threshold:.1f})")
    
    c = rl_canvas.Canvas(str(output_path), pagesize=(page_w, page_h))
    
    # Calculate printable area (consistent for all films)
    printable_w = page_w - 2 * margin_pt
    printable_h = page_h - 2 * margin_pt
    
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
        # FIX GROUP 5.5: Use runtime parameters instead of hardcoded values
        c.setFont("Helvetica", 8)
        c.drawRightString(page_w - MARGIN_PT, page_h - MARGIN_PT + 35, f"MESH: {mesh_count} T/I")
        c.drawRightString(page_w - MARGIN_PT, page_h - MARGIN_PT + 25, f"LPI: {lpi} | ANGLE: {angle:.0f}°")
        
        # ─── Symmetric Registration Marks ───
        film_info = {'job_name': job_name or output_path.stem}
        add_vector_marks_to_page(c, page_w, page_h, MARGIN_PT, color_rgb, color_name, film_info)
        
        # ─── Background rectangle (white, invisible in print but good for PDF preview) ───
        c.setFillColorRGB(1, 1, 1)
        c.rect(draw_x, draw_y, draw_w, draw_h, fill=1, stroke=0)
        
        # ─── Advanced Vector Path Generation ───
        # FIX: [1a] Scale-aware smoothing - INCREASE smoothing at high scale
        # A 1px staircase becomes a 5px staircase at 5x scale, requiring MORE smoothing
        adjusted_smooth = smooth_factor
        if scale_factor > 2.0:
            # Increase smoothing up to a cap
            scale_boost = min(2.5, scale_factor / 2.0)
            adjusted_smooth = min(0.45, smooth_factor * scale_boost)
            # FIX: [1a] Raise cap for text_logo when high scale
            if image_class == 'text_logo':
                # Raise cap from 0.25 to 0.35 when scale > 4
                max_smooth = 0.35 if scale_factor > 4.0 else 0.25
                adjusted_smooth = min(adjusted_smooth, max_smooth)
            logger.info(f"[VectorExporter] Scale-aware smoothing: {smooth_factor} → {adjusted_smooth:.3f} "
                       f"(scale={scale_factor:.2f}x, boost={scale_boost:.2f})")
        
        # FIX: [1c] Updated call with image_class
        if image_class == 'text_logo' and adjusted_smooth < 0.2:
            bw, upsample_factor = preprocess_mask_for_vector(mask, apply_blur=False, smooth_factor=adjusted_smooth, image_class=image_class)
        else:
            bw, upsample_factor = preprocess_mask_for_vector(mask, apply_blur=True, smooth_factor=adjusted_smooth, image_class=image_class)

        # Ensure CV_8UC1 format for findContours
        if bw.dtype != np.uint8:
            bw = (bw * 255).astype(np.uint8)
        if len(bw.shape) == 3:
            bw = cv2.cvtColor(bw, cv2.COLOR_BGR2GRAY)

        # FINAL FIX: enforce strict binary integrity directly before contour trace
        bw = (bw > 127).astype(np.uint8) * 255

        # Ensure ink=BLACK(0) for contour tracing
        # preprocess_mask_for_vector uses THRESH_BINARY which preserves input polarity
        # But findContours traces WHITE(255) regions — so we need design=WHITE, background=BLACK
        # This is INVERTED from silk screen convention, only for the purpose of contour detection
        bw_for_contours = cv2.bitwise_not(bw)

        # FIX GROUP 4.3: Use CHAIN_APPROX_TC89_L1 for smoother initial point reduction
        contours, hierarchy = cv2.findContours(
            bw_for_contours, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1
        )

        def px_to_pdf(px_x, px_y):
            # Scale down by upsample_factor from pre-processing upscale
            px_x = px_x / upsample_factor
            px_y = px_y / upsample_factor
            scale_w = draw_w / mask_w
            scale_h = draw_h / mask_h
            return draw_x + px_x * scale_w, draw_y + (mask_h - px_y) * scale_h
        
        def _append_contour_to_path(target_path, contour_arr):
            """Appends a single OpenCV contour to the PDF path with cleaning."""
            # 1. PRIMARY AREA GATE
            area = cv2.contourArea(contour_arr)
            if area < min_contour_area or len(contour_arr) < 3:
                return
            
            # 2. CONTOUR HYGIENE PHASE (Remove spikes and micro-protrusions)
            # Spikes often appear due to binarization noise or anti-aliasing artifacts
            # We filter points that create extremely sharp interior angles (< 15 degrees)
            cleaned_cnt = []
            n_pts = len(contour_arr)
            for i in range(n_pts):
                p0 = contour_arr[(i-1)%n_pts][0]
                p1 = contour_arr[i][0]
                p2 = contour_arr[(i+1)%n_pts][0]
                
                # Calculate angle
                v_prev = p1 - p0
                v_next = p2 - p1
                norm_prev = max(1e-6, np.linalg.norm(v_prev))
                norm_next = max(1e-6, np.linalg.norm(v_next))
                
                # Dot product for angle
                cos_theta = np.dot(v_prev, v_next) / (norm_prev * norm_next)
                angle = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))
                
                # SPIKE DETECTION: If angle is extremely sharp (turning > 165 deg)
                # Protrusions often happen when a single pixel is "out"
                if angle > 165.0:
                    # Cut spikes up to 8px long at high resolution
                    spike_limit = max(3.0, 1.5 * scale_factor)
                    if norm_prev < spike_limit or norm_next < spike_limit:
                        # Skip this point to "cut" the spike
                        continue
                cleaned_cnt.append(contour_arr[i])
            
            if len(cleaned_cnt) < 3:
                return
                
            contour_arr = np.array(cleaned_cnt)
            
            # 3. BEZIER FITTING PHASE
            # Use adjusted_smooth (scale-aware) instead of original smooth_factor
            adaptive_smooth = compute_adaptive_smooth(
                contour_arr, adjusted_smooth, image_class
            )
            
            # Scale-aware epsilon: reduce epsilon for high upscales to preserve detail
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
        
        # FIX GROUP 3.1 & 3.2: Native contour-based path fill (NO DFS fallback)
        c.setFillColorRGB(0, 0, 0)
        path = c.beginPath()
        for contour in contours:
            _append_contour_to_path(path, contour)
            
        try:
            # Use fillMode parameter for proper hole handling in newer ReportLab
            c.drawPath(path, fill=1, stroke=0, fillMode=c.FILL_EVEN_ODD)
            logger.info(f"[VectorExporter] Used even-odd fill for {len(contours)} contours")
        except (AttributeError, TypeError):
            # Fallback for older ReportLab: Non-zero winding rule works naturally
            # with OpenCV RETR_TREE as outer contours and holes have alternating order
            c.drawPath(path, fill=1, stroke=0)
            logger.info(f"[VectorExporter] Used native contour-based path fill for {len(contours)} contours")
        
        # FIX GROUP 6.1: Clean footer with only color name and brand
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)
        # Left: Color name only
        c.drawString(MARGIN_PT, MARGIN_PT - 15, color_name.upper())
        # Right: Brand only
        c.drawRightString(page_w - MARGIN_PT, MARGIN_PT - 15, "Developed by MO2")
    
    c.save()
    logger.info(f"[VectorExporter] Saved: {output_path} ({len(masks)} films)")
    return output_path

def render_vector_halftone(canvas, mask, color_rgb, page_h, lpi: int = 55, angle: float = 45.0, dpi: int = 300):
    """
    FIX GROUP 3.3: Batch-render halftone dots as vector circles.
    Uses HalftoneGenerator.generate_vector_dots() for efficient batch rendering.
    """
    import numpy as np
    from core.halftone_generator import HalftoneGenerator

    # Generate vector dots using the halftone generator
    ht_gen = HalftoneGenerator(dpi=dpi)
    dots = ht_gen.generate_vector_dots(mask, lpi=lpi, angle=angle, dot_shape="circle")

    if not dots:
        logger.warning("[VectorHalftone] No dots generated for mask")
        return

    # Batch render all dots into a single path for efficiency
    canvas.setFillColorRGB(0, 0, 0)  # Black ink for film
    path = canvas.beginPath()

    for dot in dots:
        # Convert to PDF coordinates (flip Y)
        cx = dot.cx
        cy = page_h - dot.cy
        r = dot.radius

        # Add circle to path (approximate with small arc segments)
        # Start at 3 o'clock position
        path.moveTo(cx + r, cy)
        # Draw circle using 4 quadratic bezier curves (good approximation)
        # Control points for circle approximation
        k = 0.552284749831  # 4/3 * (sqrt(2) - 1)
        # Right half (top to bottom)
        path.curveTo(cx + r, cy + k * r, cx + k * r, cy + r, cx, cy + r)
        # Bottom half (right to left)
        path.curveTo(cx - k * r, cy + r, cx - r, cy + k * r, cx - r, cy)
        # Left half (bottom to top)
        path.curveTo(cx - r, cy - k * r, cx - k * r, cy - r, cx, cy - r)
        # Top half (left to right)
        path.curveTo(cx + k * r, cy - r, cx + r, cy - k * r, cx + r, cy)
        path.close()

    # Draw all dots at once
    canvas.drawPath(path, fill=1, stroke=0)
    logger.info(f"[VectorHalftone] Rendered {len(dots)} halftone dots as vector circles")

def render_raster_halftone(canvas, mask: np.ndarray, dpi: int, page_w: float, page_h: float, 
                           margin_pt: float = 65.0, lpi: int = 55, mesh_count: int = 160,
                           scale_mode: str = 'fit_to_page', custom_scale_percent: float = 100.0,
                           custom_page_w: float = 0, custom_page_h: float = 0,
                           fit_to_artwork: bool = False) -> None:
    """Embed halftone mask as a high-resolution raster image inside the PDF.
    
    FIX: Now supports custom pages and fit_to_artwork.
    """
    if mask.dtype != np.uint8:
        mask_u8 = mask.astype(np.uint8)
    else:
        mask_u8 = mask

    if len(mask_u8.shape) == 3:
        mask_u8 = cv2.cvtColor(mask_u8, cv2.COLOR_BGR2GRAY)

    mask_h, mask_w = mask_u8.shape[:2]

    # Use maximum PNG compression quality
    ok, png_bytes = cv2.imencode('.png', mask_u8, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not ok:
        raise RuntimeError("Failed to encode halftone mask as PNG")

    from reportlab.lib.utils import ImageReader
    img_reader = ImageReader(io.BytesIO(png_bytes.tobytes()))

    # Calculate actual page size if custom
    if fit_to_artwork:
        # Match vector_exporter calculation
        target_page_w = (mask_w / dpi * 72.0) + (2 * margin_pt)
        target_page_h = (mask_h / dpi * 72.0) + (2 * margin_pt)
    elif custom_page_w > 0 and custom_page_h > 0:
        target_page_w = custom_page_w * 72.0 / 25.4
        target_page_h = custom_page_h * 72.0 / 25.4
    else:
        target_page_w = page_w
        target_page_h = page_h

    # Reserve space for header/footer
    header_pt = 40.0
    footer_pt = 30.0
    available_w = target_page_w - 2 * margin_pt
    available_h = target_page_h - header_pt - footer_pt - 2 * margin_pt

    # Scale according to mode
    if scale_mode == 'actual_size' or fit_to_artwork:
        scale_factor = 1.0
    elif scale_mode == 'custom_scale':
        scale_factor = custom_scale_percent / 100.0
    else: # fit_to_page
        img_w_pt = (mask_w / dpi) * 72.0
        img_h_pt = (mask_h / dpi) * 72.0
        scale_x = available_w / img_w_pt if img_w_pt > 0 else 1.0
        scale_y = available_h / img_h_pt if img_h_pt > 0 else 1.0
        scale_factor = min(scale_x, scale_y)
        scale_factor = min(scale_factor, 5.0)
        scale_factor = max(scale_factor, 0.1)

    draw_w = (mask_w / dpi * 72.0) * scale_factor
    draw_h = (mask_h / dpi * 72.0) * scale_factor
    draw_x = margin_pt + (available_w - draw_w) / 2
    draw_y = margin_pt + footer_pt + (available_h - draw_h) / 2

    canvas.drawImage(img_reader, draw_x, draw_y, width=draw_w, height=draw_h, 
                     mask='auto')
    
    logger.debug(f"[RasterHalftone] Embedded {mask_w}x{mask_h} mask at {dpi}DPI "
                f"with scale={scale_factor:.2f} (fit_art={fit_to_artwork})")