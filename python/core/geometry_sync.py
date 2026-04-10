"""
geometry_sync.py — Centralized Geometry Synchronization System
Virtual Design Silk Screen Studio

FIX GROUP: Architecture-wide dimension synchronization

This module provides the single source of truth for keeping ALL geometry-dependent
artifacts synchronized throughout the pipeline:
- alpha masks
- artwork masks  
- visibility masks
- transparency maps
- contour maps
- threshold masks

Problem Solved:
- IndexError: boolean index did not match indexed array along dimension 0
- Stale alpha masks after resize/upscale/downscale
- Dimension drift across preprocessing stages
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Union
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class GeometryState:
    """
    Immutable geometry state container.
    Tracks the current authoritative dimensions and all derived masks.
    """
    height: int
    width: int
    alpha_mask: Optional[np.ndarray] = None  # True = visible, False = transparent
    
    # Derived masks (synchronized to main dimensions)
    visibility_mask: Optional[np.ndarray] = None  # Same as alpha but float [0,1]
    contour_mask: Optional[np.ndarray] = None     # Edge/contour regions
    
    def __post_init__(self):
        """Validate and synchronize all masks to current dimensions."""
        if self.alpha_mask is not None:
            self.alpha_mask = self._sync_mask(self.alpha_mask, "alpha_mask")
        if self.visibility_mask is not None:
            self.visibility_mask = self._sync_mask(self.visibility_mask, "visibility_mask")
        if self.contour_mask is not None:
            self.contour_mask = self._sync_mask(self.contour_mask, "contour_mask")
    
    def _sync_mask(self, mask: np.ndarray, name: str) -> np.ndarray:
        """Synchronize a single mask to current dimensions."""
        if mask.shape[:2] != (self.height, self.width):
            logger.warning(
                f"[GeometryState] {name} shape {mask.shape[:2]} != "
                f"target ({self.height}, {self.width}), resizing"
            )
            # Use NEAREST to preserve binary nature of masks
            if mask.dtype == bool:
                resized = cv2.resize(
                    mask.astype(np.uint8),
                    (self.width, self.height),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)
            else:
                resized = cv2.resize(
                    mask,
                    (self.width, self.height),
                    interpolation=cv2.INTER_NEAREST
                )
            return resized
        return mask
    
    @property
    def shape(self) -> Tuple[int, int]:
        return (self.height, self.width)
    
    @property
    def size(self) -> int:
        return self.height * self.width


class GeometrySynchronizer:
    """
    Centralized geometry synchronization manager.
    
    This is the SINGLE POINT OF TRUTH for all dimension-related operations.
    All pipeline stages must use this class when:
    - Loading images (initial geometry establishment)
    - Resizing/upscaling/downscaling images
    - Creating or modifying masks
    - Accessing alpha/visibility masks
    
    Usage:
        sync = GeometrySynchronizer()
        
        # Initialize from loaded image
        sync.initialize_from_image(img, alpha_mask)
        
        # Resize image through synchronizer
        img_resized = sync.resize_image(img, new_w, new_h)
        
        # Get synchronized alpha mask for any operation
        alpha = sync.get_alpha_for_shape(some_mask.shape)
    """
    
    def __init__(self):
        self._state: Optional[GeometryState] = None
        self._operation_log: List[Dict] = []
    
    def initialize_from_image(
        self,
        image: np.ndarray,
        alpha_mask: Optional[np.ndarray] = None,
        source: str = "unknown"
    ) -> GeometryState:
        """
        Initialize geometry state from an image.
        This is the ONLY way to establish initial geometry.
        
        Args:
            image: Input image (H x W x C)
            alpha_mask: Optional alpha channel (True = visible)
            source: Identifier for logging (e.g., "loader", "preprocess")
            
        Returns:
            GeometryState: The synchronized state
        """
        h, w = image.shape[:2]
        
        # Synchronize alpha to image dimensions if provided
        if alpha_mask is not None:
            if alpha_mask.shape != (h, w):
                logger.warning(
                    f"[GeometrySync] Initial alpha mismatch: {alpha_mask.shape} vs image ({h}, {w}), "
                    f"resizing from {source}"
                )
                alpha_mask = cv2.resize(
                    alpha_mask.astype(np.uint8),
                    (w, h),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)
        
        self._state = GeometryState(
            height=h,
            width=w,
            alpha_mask=alpha_mask
        )
        
        self._log_operation("initialize", {
            "source": source,
            "shape": (h, w),
            "has_alpha": alpha_mask is not None
        })
        
        logger.info(f"[GeometrySync] Initialized from {source}: {w}x{h}, alpha={alpha_mask is not None}")
        return self._state
    
    def resize_image(
        self,
        image: np.ndarray,
        new_width: int,
        new_height: int,
        interpolation: int = cv2.INTER_LANCZOS4,
        operation_name: str = "resize"
    ) -> np.ndarray:
        """
        Resize an image AND synchronize all masks to new dimensions.
        
        This is the ONLY sanctioned way to resize images in the pipeline.
        Automatically keeps alpha and all derived masks synchronized.
        
        Args:
            image: Image to resize
            new_width: Target width
            new_height: Target height
            interpolation: OpenCV interpolation constant
            operation_name: Name for logging
            
        Returns:
            Resized image
        """
        if self._state is None:
            raise RuntimeError("GeometrySynchronizer not initialized. Call initialize_from_image first.")
        
        old_shape = self._state.shape
        
        # Resize the image
        resized = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
        
        # Synchronize all masks to new dimensions
        if self._state.alpha_mask is not None:
            self._state.alpha_mask = cv2.resize(
                self._state.alpha_mask.astype(np.uint8),
                (new_width, new_height),
                interpolation=cv2.INTER_NEAREST  # Critical: preserve binary
            ).astype(bool)
        
        # Update state dimensions
        self._state.height = new_height
        self._state.width = new_width
        
        self._log_operation(operation_name, {
            "from": old_shape,
            "to": (new_height, new_width),
            "interpolation": interpolation
        })
        
        logger.info(
            f"[GeometrySync] {operation_name}: {old_shape[1]}x{old_shape[0]} -> "
            f"{new_width}x{new_height}, alpha synced"
        )
        
        return resized
    
    def upscale_with_guard(
        self,
        image: np.ndarray,
        target_min_dim: int = 1000,
        absolute_max_px: int = 2500,
        memory_safe_mp: float = 6.0,
        operation_name: str = "upscale"
    ) -> np.ndarray:
        """
        Upscale small images with memory guards AND alpha synchronization.
        
        Centralized implementation of upscale logic that was previously
        duplicated in image_loader.py and other places.
        
        Args:
            image: Input image
            target_min_dim: Minimum dimension target
            absolute_max_px: Hard cap on dimensions
            memory_safe_mp: Megapixel budget
            operation_name: Name for logging
            
        Returns:
            Potentially upscaled image
        """
        h, w = image.shape[:2]
        min_dim = min(h, w)
        
        if min_dim >= target_min_dim:
            logger.debug(f"[GeometrySync] No upscale needed: {min_dim} >= {target_min_dim}")
            return image
        
        # Calculate scale
        scale = target_min_dim / min_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Apply hard caps
        if max(new_w, new_h) > absolute_max_px:
            scale = absolute_max_px / max(new_w, new_h)
            new_w, new_h = int(w * scale), int(h * scale)
        
        # Check megapixel budget
        if (new_w * new_h) / 1_000_000 > memory_safe_mp:
            scale = (memory_safe_mp * 1_000_000 / (h * w)) ** 0.5
            new_w, new_h = int(w * scale), int(h * scale)
        
        # Perform resize with synchronization
        return self.resize_image(
            image, new_w, new_h,
            interpolation=cv2.INTER_LANCZOS4,
            operation_name=operation_name
        )
    
    def get_alpha_for_shape(
        self,
        target_shape: Tuple[int, ...],
        allow_resize: bool = True
    ) -> Optional[np.ndarray]:
        """
        Get alpha mask synchronized to target shape.
        
        This is the PRIMARY method for accessing alpha masks.
        All pipeline stages should use this instead of directly accessing alpha.
        
        Args:
            target_shape: Desired shape (H, W) or (H, W, C)
            allow_resize: If True, resize to match; if False, return None on mismatch
            
        Returns:
            Alpha mask matching target shape, or None
        """
        if self._state is None or self._state.alpha_mask is None:
            return None
        
        target_hw = target_shape[:2]
        current_hw = self._state.shape
        
        if current_hw == target_hw:
            return self._state.alpha_mask
        
        if not allow_resize:
            logger.warning(
                f"[GeometrySync] Alpha shape mismatch: {current_hw} vs {target_hw}, "
                f"allow_resize=False, returning None"
            )
            return None
        
        # Resize to match target
        resized = cv2.resize(
            self._state.alpha_mask.astype(np.uint8),
            (target_hw[1], target_hw[0]),  # OpenCV: (width, height)
            interpolation=cv2.INTER_NEAREST
        ).astype(bool)
        
        logger.debug(f"[GeometrySync] Alpha resized: {current_hw} -> {target_hw}")
        return resized
    
    def apply_alpha_to_mask(
        self,
        mask: np.ndarray,
        background_value: int = 255,
        operation_name: str = "apply_alpha"
    ) -> np.ndarray:
        """
        Apply alpha mask to a binary/grayscale mask.
        Sets transparent regions to background value.
        
        Centralized implementation of the common "set transparent to background" operation.
        
        Args:
            mask: Input mask
            background_value: Value to set in transparent regions
            operation_name: Name for logging
            
        Returns:
            Mask with alpha applied
        """
        alpha = self.get_alpha_for_shape(mask.shape)
        if alpha is None:
            return mask
        
        # Apply: transparent regions become background
        result = mask.copy()
        result[~alpha] = background_value
        
        transparent_count = np.sum(~alpha)
        logger.debug(
            f"[GeometrySync] {operation_name}: {transparent_count} pixels set to {background_value}"
        )
        
        return result
    
    def get_current_shape(self) -> Optional[Tuple[int, int]]:
        """Get current authoritative dimensions."""
        if self._state is None:
            return None
        return self._state.shape
    
    def _log_operation(self, operation: str, details: Dict):
        """Internal operation logging for debugging."""
        import time
        self._operation_log.append({
            "timestamp": time.time(),
            "operation": operation,
            **details
        })
    
    def get_operation_log(self) -> List[Dict]:
        """Get operation history for debugging."""
        return self._operation_log.copy()


# ═══ GLOBAL SYNCHRONIZER INSTANCE ═══
# Single instance used throughout the pipeline
_global_synchronizer: Optional[GeometrySynchronizer] = None


def get_synchronizer() -> GeometrySynchronizer:
    """Get the global geometry synchronizer instance."""
    global _global_synchronizer
    if _global_synchronizer is None:
        _global_synchronizer = GeometrySynchronizer()
    return _global_synchronizer


def reset_synchronizer():
    """Reset the global synchronizer (useful for testing or new pipeline runs)."""
    global _global_synchronizer
    _global_synchronizer = GeometrySynchronizer()
    logger.info("[GeometrySync] Global synchronizer reset")


# ═══ CONVENIENCE FUNCTIONS ═══
# These make it easy to use the synchronizer without explicit instance management

def sync_initialize(image: np.ndarray, alpha_mask: Optional[np.ndarray] = None, source: str = "unknown"):
    """Initialize geometry from image."""
    return get_synchronizer().initialize_from_image(image, alpha_mask, source)


def sync_resize(image: np.ndarray, new_w: int, new_h: int, **kwargs) -> np.ndarray:
    """Resize image with alpha synchronization."""
    return get_synchronizer().resize_image(image, new_w, new_h, **kwargs)


def sync_upscale(image: np.ndarray, **kwargs) -> np.ndarray:
    """Upscale image with guards and alpha synchronization."""
    return get_synchronizer().upscale_with_guard(image, **kwargs)


def sync_get_alpha(shape: Tuple[int, ...], allow_resize: bool = True) -> Optional[np.ndarray]:
    """Get alpha mask for target shape."""
    return get_synchronizer().get_alpha_for_shape(shape, allow_resize)


def sync_apply_alpha(mask: np.ndarray, background_value: int = 255) -> np.ndarray:
    """Apply alpha to mask, setting transparent regions to background."""
    return get_synchronizer().apply_alpha_to_mask(mask, background_value)
