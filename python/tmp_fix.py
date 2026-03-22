def step7_5_strict_binarization(masks: list, args: argparse.Namespace) -> list:
    """
    Apply strict binarization and noise removal to ensure clean solid films.
    """
    is_halftone = args.halftone and not getattr(args, 'skip_halftone', False)
    _step(7.5, f"Strict binarization ({'halftone' if is_halftone else 'solid'} mode)")
    
    result = []
    total = max(1, len(masks))
    
    # Use global-threshold if provided, fallback to 200 for solid, 45 for halftone
    threshold_val = getattr(args, 'global_threshold', 200 if not is_halftone else 45)
    noise_min_area = getattr(args, 'noise_removal', 10)
    
    for i, mask in enumerate(masks):
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)

        # ── BINARY MASK GUARD: Ensure clean edges and preserved dots ──────
        
        # 1. Apply smoothing to SOLID masks if requested (Phase 22)
        is_solid = not is_halftone
        if is_solid:
            smooth = getattr(args, 'smoothing_factor', 0.0)
            if smooth > 0.1:
                blur_size = 5 if smooth > 0.5 else 3
                mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
        
        # 2. Select safe threshold (45 for halftone to keep tiny dots, 127/threshold_val for solid)
        safe_thresh = 45 if is_halftone else threshold_val
        _, binary_mask = cv2.threshold(mask, safe_thresh, 255, cv2.THRESH_BINARY)
        
        # Noise removal (Area opening)
        if noise_min_area > 0:
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                binary_mask, 8, cv2.CV_32S
            )
            clean = np.zeros_like(binary_mask)
            for lbl in range(1, num_labels):
                if stats[lbl, cv2.CC_STAT_AREA] >= noise_min_area:
                    clean[labels == lbl] = 255
            binary_mask = clean
        
        result.append(binary_mask)
        _progress(((7.5 - 1) + (i + 1) / total) / TOTAL_STEPS, f"Processed {i+1}/{total} [BINARY-GUARD]")
        
    return result
