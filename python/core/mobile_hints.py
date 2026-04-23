import os
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MobileHints:
    def __init__(self, image_class_hint, ai_confidence, pre_mask_path, force_no_ai=False):
         self.image_class_hint = image_class_hint
         self.ai_confidence = ai_confidence
         self.pre_mask_path = pre_mask_path
         self.force_no_ai = force_no_ai

def parse_mobile_hints(args):
    # args parsed in main.py
    image_class_hint = getattr(args, 'image_class_hint', 'auto')
    ai_confidence = getattr(args, 'ai_confidence', 0.0)
    pre_mask = getattr(args, 'pre_mask', None)
    no_ai = getattr(args, 'no_ai', False)

    if image_class_hint == 'auto' and not pre_mask:
        return None
        
    return MobileHints(image_class_hint, ai_confidence, pre_mask, no_ai)

def _load_mobile_mask(mask_path, target_shape):
    """
    Loads edge-case pre-segmented mask from mobile app safely
    """
    if not mask_path or not os.path.exists(mask_path):
        return None
        
    try:
        # read grey
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            return None
            
        if mask.shape != target_shape:
            mask = cv2.resize(mask, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LANCZOS4)
            
        # Optional basic thresholding if it got messy
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        
        # Micro morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        return mask
    except Exception as e:
        logger.warning(f"Failed to load mobile mask {mask_path}: {e}")
        return None

def apply_mobile_hints(args, decision, image):
    """
    Apply any pre-computed AI hints from the mobile app (flutter) to skip expensive py processing
    """
    hints = parse_mobile_hints(args)
    if not hints:
         return decision, None
         
    # FIX: Disable automatic class injection; delegate to Fast Classifier for consistency
    # if hints.image_class_hint != 'auto' and hints.ai_confidence > 0.8:
    #      if getattr(decision, 'is_locked', False):
    #           logger.info(f"[Mobile AI] Ignoring class hint '{hints.image_class_hint}' because decision is already LOCKED.")
    #      else:
    #           logger.info(f"[Mobile AI] Injecting highly confident class: {hints.image_class_hint}")
    #           decision.image_class = hints.image_class_hint
         
    alpha_mask = None
    if hints.pre_mask_path:
         logger.info(f"[Mobile AI] Injecting pre-segmentation mask from {hints.pre_mask_path}")
         alpha_mask = _load_mobile_mask(hints.pre_mask_path, image.shape[:2])
         
    return decision, alpha_mask

def cleanup_mobile_mask(mask_path):
    try:
        if mask_path and os.path.exists(mask_path):
            os.remove(mask_path)
            logger.info(f"Cleaned up mobile temp mask {mask_path}")
    except Exception as e:
        logger.warning(f"Could not delete temp mobile mask: {e}")
