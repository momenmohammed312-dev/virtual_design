import datetime
from pathlib import Path
try:
    from core.halftone_generator import HalftoneDot
except Exception:
    # Fallback: define a minimal HalftoneDot to satisfy type hints if import fails
    from dataclasses import dataclass
    @dataclass
    class HalftoneDot:
        cx: float
        cy: float
        radius: float
        shape: str
from typing import List, Optional, Tuple

import cv2
import numpy as np

# ── reportlab imports ─────────────────────────────────────────────────────────
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


def _rgb_to_cmyk(r: int, g: int, b: int) -> Tuple[int, int, int, int]:
    """Convert 0-255 RGB to 0-100 CMYK percentages."""
    if r == g == b == 0:
        return (0, 0, 0, 100)
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    k = 1 - max(rf, gf, bf)
    if k == 1.0:
        return (0, 0, 0, 100)
    c = (1 - rf - k) / (1 - k)
    m = (1 - gf - k) / (1 - k)
    y = (1 - bf - k) / (1 - k)
    return (round(c * 100), round(m * 100), round(y * 100), round(k * 100))


class PDFDocumentBuilder:
    """
    Build a multi-page, 100% vector PDF for silk-screen film output.
    Each page = one color film.
    """

    def __init__(self, output_path: str, dpi: int = 300, page_size=None):
        if not REPORTLAB_OK:
            raise ImportError("reportlab is required: pip install reportlab")

        self.output_path = Path(output_path)
        self.dpi = dpi
        self.page_size = page_size or A4          # default A4, can pass custom
        self._page_w, self._page_h = self.page_size

        # Border around image area (in points, 1pt = 1/72 inch)
        self.margin_pt = 40.0                     # 40pt ≈ 14mm

        # Registration mark size in points
        self.reg_size_pt = 18.0                   # crosshair arm length
        self.reg_circle_r = 9.0                   # outer circle radius

        # Open canvas
        self._canvas = rl_canvas.Canvas(
            str(self.output_path),
            pagesize=self.page_size,
        )
        self._page_count = 0

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def add_film_page(
        self,
        mask: np.ndarray,
        color_rgb: Tuple[int, int, int],
        color_name: str,
        film_index: int,
        total_films: int,
        halftone_dots=None,       # List[HalftoneDot] | None
        project_name: str = "Silk Screen Job",
        job_id: str = "",
        angle: float = 0.0,
    ) -> None:
        """
        Add one page for a color film.

        If halftone_dots is provided → draw vector circles (halftone mode).
        If halftone_dots is None     → draw filled contour paths (solid mode).
        """
        c = self._canvas
        pw, ph = self._page_w, self._page_h

        if self._page_count > 0:
            c.showPage()
        self._page_count += 1

        # ── image area (inside margins) ───────────────────────────────────────
        img_h, img_w = mask.shape[:2]
        avail_w = pw - 2 * self.margin_pt - 2 * self.reg_size_pt * 2
        avail_h = ph - 2 * self.margin_pt - 60       # 60pt for metadata block

        scale = min(avail_w / img_w, avail_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale

        # Center the image area
        img_x = (pw - draw_w) / 2
        img_y = 55 + (avail_h - draw_h) / 2          # 55pt metadata block at bottom

        # ── draw image content ───────────────────────────────────────────────
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)

        if halftone_dots:
            self._draw_halftone_dots(c, halftone_dots, img_x, img_y, img_w, img_h, scale)
        else:
            self._draw_mask_paths(c, mask, img_x, img_y, img_h, scale)

        # ── registration marks (vector) ───────────────────────────────────────
        self._draw_registration_marks(c, img_x, img_y, draw_w, draw_h)

        # ── crop marks (corner L-marks) ───────────────────────────────────────
        self._draw_crop_marks(c, img_x, img_y, draw_w, draw_h)

        # ── color metadata block (bottom strip) ───────────────────────────────
        self._draw_metadata_block(
            c, color_rgb, color_name, film_index, total_films,
            project_name, job_id, angle, img_w, img_h,
        )

    def save(self) -> Path:
        """Save and close the PDF file."""
        self._canvas.save()
        print(f"   📄 PDF saved ({self._page_count} pages): {self.output_path}")
        return self.output_path

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE — IMAGE CONTENT RENDERERS
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_mask_paths(
        self, c, mask: np.ndarray,
        img_x: float, img_y: float, img_h: int, scale: float,
    ) -> None:
        """Draw mask as filled vector paths (contours → PDF path commands)."""
        _, bw = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(
            bw, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS
        )
        if not contours:
            return

        c.setFillColorRGB(0, 0, 0)

        for cnt in contours:
            if len(cnt) < 3:
                continue
            arc_len = cv2.arcLength(cnt, True)
            epsilon = 0.0005 * arc_len           # tighter simplification
            approx = cv2.approxPolyDP(cnt, epsilon, True).reshape(-1, 2)
            if len(approx) < 3:
                continue

            p = c.beginPath()
            x0, y0 = approx[0]
            # Flip Y: PDF origin is bottom-left, image origin is top-left
            p.moveTo(img_x + x0 * scale, img_y + (img_h - y0) * scale)
            for (x, y) in approx[1:]:
                p.lineTo(img_x + x * scale, img_y + (img_h - y) * scale)
            p.close()
            c.drawPath(p, fill=1, stroke=0)

    def _draw_halftone_dots(self, c, dots, img_x: float, img_y: float, img_w: int, img_h: int, scale: float) -> None:
        """Draw halftone dots as vector circles — true vector halftone."""
        c.setFillColorRGB(0, 0, 0)
        for dot in dots:
            px = img_x + dot.cx * scale
            py = img_y + (img_h - dot.cy) * scale  # flip Y
            r = dot.radius * scale
            if r < 0.1:
                continue
            if dot.shape == "square":
                c.rect(px - r, py - r, r * 2, r * 2, fill=1, stroke=0)
            else:
                c.circle(px, py, r, fill=1, stroke=0)

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE — MARKS AND METADATA
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_registration_marks(
        self, c, ix: float, iy: float, dw: float, dh: float,
    ) -> None:
        """Draw 4 crosshair+circle registration marks at image corners (vector)."""
        s = self.reg_size_pt
        r = self.reg_circle_r
        offset = s * 1.8         # distance from image edge to mark center

        positions = [
            (ix - offset,      iy + dh + offset),  # top-left
            (ix + dw + offset, iy + dh + offset),  # top-right
            (ix - offset,      iy - offset),        # bottom-left
            (ix + dw + offset, iy - offset),        # bottom-right
        ]

        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(1, 1, 1)   # white fill inside circle
        c.setLineWidth(0.75)

        for (mx, my) in positions:
            # Outer circle (unfilled)
            c.circle(mx, my, r, fill=0, stroke=1)
            # Horizontal line
            c.line(mx - s, my, mx + s, my)
            # Vertical line
            c.line(mx, my - s, mx, my + s)

    def _draw_crop_marks(
        self, c, ix: float, iy: float, dw: float, dh: float,
    ) -> None:
        """Draw L-shaped crop marks at all 4 corners (vector)."""
        arm = 14.0      # pt
        gap = 6.0       # pt gap between image edge and mark start

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)

        corners = [
            # (corner_x, corner_y, h_dir, v_dir)
            (ix,      iy + dh, -1,  1),   # top-left
            (ix + dw, iy + dh,  1,  1),   # top-right
            (ix,      iy,      -1, -1),   # bottom-left
            (ix + dw, iy,       1, -1),   # bottom-right
        ]

        for (cx_, cy_, hd, vd) in corners:
            # Horizontal arm
            c.line(cx_ + hd * gap, cy_, cx_ + hd * (gap + arm), cy_)
            # Vertical arm
            c.line(cx_, cy_ + vd * gap, cx_, cy_ + vd * (gap + arm))

    def _draw_metadata_block(
        self, c,
        color_rgb: Tuple[int, int, int],
        color_name: str,
        film_index: int,
        total_films: int,
        project_name: str,
        job_id: str,
        angle: float,
        img_w: int,
        img_h: int,
    ) -> None:
        """Draw metadata text strip at the bottom of the page (vector text)."""
        r, g, b = color_rgb
        ci, cm, cy, ck = _rgb_to_cmyk(r, g, b)
        today = datetime.date.today().strftime("%Y-%m-%d")

        pw = self._page_w

        c.setFillColorRGB(0, 0, 0)

        # ── top line: project + job ───────────────────────────────────────────
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10, 44, f"PROJECT: {project_name}")
        c.setFont("Helvetica", 8)
        if job_id:
            c.drawString(pw / 2, 44, f"JOB ID: {job_id}")
        c.drawRightString(pw - 10, 44, f"DATE: {today}")

        # ── mid line: film info ───────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 9)
        c.drawString(10, 32, f"FILM {film_index} / {total_films}")
        c.setFont("Helvetica", 8)
        c.drawString(70, 32, f"COLOR: {color_name}")
        c.drawString(200, 32, f"RGB ({r}, {g}, {b})")
        c.drawString(310, 32, f"CMYK {ci}% {cm}% {cy}% {ck}%")
        c.drawRightString(pw - 10, 32, f"ANGLE: {angle}°")

        # ── bottom line: resolution ───────────────────────────────────────────
        c.setFont("Helvetica", 7)
        c.drawString(10, 20, f"SIZE: {img_w}×{img_h}px  |  DPI: {self.dpi}")
        c.drawString(200, 20, "PRINT METHOD: Silk Screen / Sérigraphie")

        # ── color swatch (small filled rect, vector) ─────────────────────────~
        c.setFillColorRGB(r / 255.0, g / 255.0, b / 255.0)
        c.rect(pw - 55, 18, 40, 18, fill=1, stroke=0)
        c.setStrokeColorRGB(0, 0, 0)
        c.rect(pw - 55, 18, 40, 18, fill=0, stroke=1)

        # ── separator line ───────────────────────────────────────────────────
        c.setStrokeColorRGB(0.3, 0.3, 0.3)
        c.setLineWidth(0.3)
        c.line(10, 50, pw - 10, 50)


def build_multipage_pdf(
    output_path: str,
    masks: List[np.ndarray],
    colors: List[Tuple[int, int, int]],
    color_names: List[str],
    dpi: int = 300,
    halftone_dots_list=None,     # List[List[HalftoneDot]] | None
    angles: Optional[List[float]] = None,
    project_name: str = "Silk Screen Job",
    job_id: str = "",
) -> Path:
    """
    Build a complete multi-page vector PDF in one call.

    Args:
        output_path:       Path to output .pdf file
        masks:             List of binary masks (one per color)
        colors:            List of (R, G, B) tuples
        color_names:       List of color name strings
        dpi:               Resolution
        halftone_dots_list: Optional list of HalftoneDot lists (one per mask).
                            If provided, pages use vector halftone dots.
                            If None, pages use solid contour fills.
        angles:            Screen angles per color (for metadata display)
        project_name:      Project/job name shown in metadata
        job_id:            Optional job ID string
    
    Returns:
        Path to the saved PDF
    """
    builder = PDFDocumentBuilder(output_path=output_path, dpi=dpi)
    total = len(masks)
    _angles = angles or [0.0] * total

    for i, (mask, color, name) in enumerate(zip(masks, colors, color_names)):
        dots = halftone_dots_list[i] if halftone_dots_list else None
        builder.add_film_page(
            mask=mask,
            color_rgb=tuple(color),
            color_name=name,
            film_index=i + 1,
            total_films=total,
            halftone_dots=dots,
            project_name=project_name,
            job_id=job_id,
            angle=_angles[i],
        )
        print(f"   ✅ Page {i+1}/{total}: {name}")

    return builder.save()
