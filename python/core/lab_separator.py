"""
lab_separator.py — Phase 5: LAB Color Space Separation Upgrade
Industry-grade color separation using perceptual clustering.

Pipeline:
    1. RGB -> LAB conversion (perceptual uniformity)
    2. Adaptive K-means (elbow method for k selection)
    3. ΔE-based pixel assignment (perceptual accuracy)
    4. Per-mask morphological cleanup
    5. Edge smoothing on mask boundaries
"""

from __future__ import annotations
import cv2
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# ─── Data Types ──────────────────────────────────────────────────────────────

@dataclass
class ColorCluster:
    index: int
    lab_center: np.ndarray       # LAB center (float32, 3-values)
    rgb: Tuple[int, int, int]    # Converted RGB for export
    hex_color: str               # '#RRGGBB'
    pixel_count: int
    coverage_pct: float
    mask: np.ndarray             # uint8 binary mask (255=this color, 0=other)


@dataclass
class LABSeparationResult:
    clusters: List[ColorCluster]
    k: int                        # Actual number of clusters used
    compactness: float            # K-means compactness score
    color_space: str = "LAB"

    # Pipeline-compatible aliases
    @property
    def colors(self) -> List[Tuple[int, int, int]]:
        return [c.rgb for c in self.clusters]

    @property
    def color_names(self) -> List[str]:
        return [c.hex_color for c in self.clusters]

    @property
    def color_masks(self) -> List[np.ndarray]:
        return [c.mask for c in self.clusters]

    @property
    def num_colors(self) -> int:
        return self.k


# ─── Separator ───────────────────────────────────────────────────────────────

class LABColorSeparator:
    """
    Perceptual color separator using CIE LAB space + ΔE distance.

    Key improvements over RGB K-means:
    • Perceptually uniform -> equal ΔE means equal perceived difference
    • Elbow-method adaptive K -> no manual color count required
    • Morphological mask cleanup -> clean print-ready edges
    • No hard-threshold segmentation -> no color banding
    """

    def __init__(
        self,
        k_min: int = 2,
        k_max: int = 8,
        kmeans_attempts: int = 3,
        kmeans_max_iter: int = 30,
        morph_cleanup: bool = True,
        morph_kernel_size: int = 3,
        edge_smooth: bool = True,
    ):
        self.k_min = k_min
        self.k_max = k_max
        self.kmeans_attempts = kmeans_attempts
        self.kmeans_max_iter = kmeans_max_iter
        self.morph_cleanup = morph_cleanup
        self.morph_kernel_size = morph_kernel_size
        self.edge_smooth = edge_smooth

    # ─── Public API ────────────────────────────────────────────────────────────

    def separate(
        self,
        image: np.ndarray,          # BGR uint8
        num_colors: Optional[int] = None,   # None = auto elbow
    ) -> LABSeparationResult:
        """
        Separate image into perceptual color clusters.

        Args:
            image:      BGR uint8 input image
            num_colors: Fixed K (or None to use elbow auto-detection)

        Returns:
            LABSeparationResult with clusters, masks, RGB values
        """
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        h, w = image.shape[:2]
        N = h * w

        # 1. Convert to LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        data = lab.reshape(-1, 3).astype(np.float32)

        # 2. Determine K
        if num_colors is not None:
            k = max(self.k_min, min(self.k_max, num_colors))
            centers, labels = self._kmeans(data, k)
            compactness = self._compactness(data, centers, labels)
        else:
            k, centers, labels, compactness = self._elbow_kmeans(data)

        # 3. Build label map (H×W)
        label_map = labels.reshape(h, w)

        # 4. Sort clusters by LAB lightness (L channel) — dark -> light
        L_means = [float(np.mean(lab[:, :, 0][label_map == i])) for i in range(k)]
        order   = np.argsort(L_means)   # darkest first

        # 5. Build ColorCluster objects
        clusters: List[ColorCluster] = []
        for new_idx, old_idx in enumerate(order):
            lab_center = centers[old_idx]

            # Convert LAB center -> BGR -> RGB
            lab_px  = np.array([[lab_center]], dtype=np.float32).astype(np.uint8)
            bgr_px  = cv2.cvtColor(lab_px, cv2.COLOR_LAB2BGR)[0][0]
            rgb_px  = cv2.cvtColor(
                np.array([[bgr_px]], dtype=np.uint8), cv2.COLOR_BGR2RGB
            )[0][0]
            rgb = (int(rgb_px[0]), int(rgb_px[1]), int(rgb_px[2]))
            hex_color = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"

            # Build binary mask
            raw_mask = (label_map == old_idx).astype(np.uint8) * 255

            # 6. Morphological cleanup
            if self.morph_cleanup:
                raw_mask = self._morph_cleanup(raw_mask)

            pixel_count  = int(np.sum(raw_mask > 0))
            coverage_pct = round(pixel_count / N * 100, 2)

            clusters.append(ColorCluster(
                index=new_idx,
                lab_center=lab_center,
                rgb=rgb,
                hex_color=hex_color,
                pixel_count=pixel_count,
                coverage_pct=coverage_pct,
                mask=raw_mask,
            ))

        logger.info(
            f"[LABColorSeparator] k={k} compactness={compactness:.0f} "
            f"colors={[c.hex_color for c in clusters]}"
        )

        return LABSeparationResult(
            clusters=clusters,
            k=k,
            compactness=compactness,
        )

    # ─── Elbow Method ─────────────────────────────────────────────────────────

    def _elbow_kmeans(
        self, data: np.ndarray
    ) -> Tuple[int, np.ndarray, np.ndarray, float]:
        """
        Run K-means for k_min…k_max and find the elbow (largest drop in
        compactness ratio).  Returns (best_k, centers, labels, compactness).
        """
        results: Dict[int, Tuple] = {}
        compactness_list: List[float] = []

        for k in range(self.k_min, self.k_max + 1):
            centers, labels = self._kmeans(data, k)
            comp = self._compactness(data, centers, labels)
            results[k] = (centers, labels, comp)
            compactness_list.append(comp)
            logger.debug(f"  [Elbow] k={k} compactness={comp:.0f}")

        # Find elbow: largest relative drop
        best_k = self.k_min
        if len(compactness_list) > 1:
            drops = []
            for i in range(1, len(compactness_list)):
                prev = compactness_list[i - 1]
                curr = compactness_list[i]
                rel_drop = (prev - curr) / (prev + 1e-9)
                drops.append(rel_drop)
            elbow_i = int(np.argmax(drops)) + 1   # +1 because drops starts at k_min+1
            best_k  = self.k_min + elbow_i
            logger.info(f"[LABColorSeparator] Elbow at k={best_k} (drop={drops[elbow_i-1]:.3f})")

        centers, labels, comp = results[best_k]
        return best_k, centers, labels, comp

    # ─── K-means Helper ───────────────────────────────────────────────────────

    def _kmeans(
        self, data: np.ndarray, k: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Run K-means and return (centers, flat_labels)."""
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            self.kmeans_max_iter,
            1.0,
        )
        np.random.seed(42)
        cv2.setRNGSeed(42)

        best_comp = float("inf")
        best_centers = None
        best_labels  = None

        for _ in range(self.kmeans_attempts):
            try:
                comp, labels, centers = cv2.kmeans(
                    data, k, None, criteria, 1, cv2.KMEANS_PP_CENTERS
                )
                if comp < best_comp:
                    best_comp    = comp
                    best_centers = centers
                    best_labels  = labels.flatten()
            except Exception as e:
                logger.warning(f"[LABColorSeparator] K-means k={k} attempt failed: {e}")

        if best_centers is None:
            raise RuntimeError(f"K-means failed for k={k}")

        return best_centers, best_labels

    @staticmethod
    def _compactness(
        data: np.ndarray, centers: np.ndarray, labels: np.ndarray
    ) -> float:
        """Compute total within-cluster sum of squared distances."""
        assigned = centers[labels.astype(int)]
        return float(np.sum((data - assigned) ** 2))

    # ─── Morphological Cleanup ────────────────────────────────────────────────

    def _morph_cleanup(self, mask: np.ndarray) -> np.ndarray:
        """
        Apply morphological closing + opening to clean mask edges.
        Closing: fills small holes within the mask.
        Opening: removes small isolated noise blobs.
        """
        k = self.morph_kernel_size
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        # Close first (fill internal holes)
        out = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        # Then open (remove pepper noise)
        out = cv2.morphologyEx(out, cv2.MORPH_OPEN,  kernel, iterations=1)
        # Optional edge smoothing via blur+threshold
        if self.edge_smooth:
            out = cv2.GaussianBlur(out, (3, 3), 0.8)
            _, out = cv2.threshold(out, 127, 255, cv2.THRESH_BINARY)
        return out


# ─── Convenience function ────────────────────────────────────────────────────

def separate_colors_lab(
    image: np.ndarray,
    num_colors: Optional[int] = None,
) -> LABSeparationResult:
    """
    Quick LAB color separation with auto K selection.

    Args:
        image:      BGR uint8 image
        num_colors: Fixed number of colors (None = auto)

    Returns:
        LABSeparationResult
    """
    return LABColorSeparator().separate(image, num_colors=num_colors)
