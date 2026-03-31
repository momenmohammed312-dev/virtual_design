# Refactoring Silk Screen Pipeline — Detailed Implementation Plan

## 🎯 GOAL
Achieve the system state described in the **SILK SCREEN PIPELINE REFACTOR — COMPLETION REPORT**, transitioning the current monolithic linear pipeline to an **Orchestrator-Router architecture** with specialized processing for different image classes (Text/Logo, Artwork, Photo).

---

## 🏗 SECTION 1 — CORE INFRASTRUCTURE & CLI

### TASK 1 — Define Print Job Constraints
*   **File**: `python/core/print_job_config.py` (New)
    *   Create `PrintJobConfig` dataclass.
    *   Define `MESH_LPI_TABLE` (86:33, 110:42, 160:55, 200:65, 305:85, etc.).
    *   Implement `validate_lpi(lpi)` to clamp input LPI to mesh limits.
    *   Implement `calculate_dot_radius_max()`.

### TASK 2/3 — CLI Mesh Awareness
*   **File**: `python/main.py`
    *   Add `--mesh-count` (int, default 160) to `parse_args()`.
    *   Instantiate `PrintJobConfig` in `main()`.
    *   Clamp `args.lpi` immediately using `job_config.validate_lpi()`.

### TASK 4 — Dart Integration
*   **File**: `lib/core/python_bridge/python_processor.dart`
    *   Update `_buildArgs()` to include `--mesh-count` from `settings.meshCount`.

---

## 🧩 SECTION 2 — PIPELINE COMPONENT HARDENING

### TASK 11 — Binarizer Cache Isolation
*   **File**: `python/core/binarizer.py`
    *   Clear `self._method_cache` at the start of `auto_threshold()` unless it is a recursive retry call.

### TASK 12 — EdgeCleaner Determinism
*   **File**: `python/core/edge_cleaner.py`
    *   Remove `GaussianBlur` and secondary thresholding from `clean()`.
    *   Keep signature for compatibility but make `smooth` parameters no-op.

### TASK 13/14 — Mask Coverage Safeguards
*   **File**: `python/core/pipeline_controller.py` & `python/core/pipeline_router.py`
    *   Add `validate_mask_coverage(mask, min, max)` to `PipelineController`.
    *   Wire validation after every binarization and halftone step.

### TASK 15 — Silhouette Validation (K-Means Guard)
*   **File**: `python/core/color_separator.py`
    *   Implement quality score based on inter/intra-cluster distances.
    *   Auto-retry with $K-1$ if separation is poor.

### TASK 16 — Halftone Shadow Relief
*   **File**: `python/core/halftone_generator.py`
    *   Cap dot radius multiplier at `0.85` (down from `0.95`) to prevent shadow flooding.

---

## 🚀 SECTION 3 — ORCHESTRATION & ROUTING (MAJOR)

### TASK 8/9 — Per-Class Preprocessing
*   **File**: `python/main.py`
    *   `preprocess_text_logo()`: Bilateral (d=7) only.
    *   `preprocess_artwork()`: Bilateral (d=9) + Contrast boost.
    *   `preprocess_photo()`: Bilateral (d=15) + Grayscale + Unsharp Mask.

### TASK 5/10 — LOGO Optimization
*   **File**: `python/main.py`
    *   `_make_single_color_separation()`: Bypass K-means for logos.
    *   Fix trapping bug: `overlap = (mask == 0) & (other_mask == 0)` and `trapped[dilated > 0] = 0`.

### TASK 17 — The Pipeline Router
*   **File**: `python/core/pipeline_router.py` (New)
    *   Dispatch logic for `_run_text_logo()`, `_run_artwork()`, `_run_photo()`.
    *   Enforce per-class rules (e.g., photo MUST halftone, logo NO halftone).

### TASK 18 — Main Orchestrator Update
*   **File**: `python/main.py`
    *   Replace linear steps with `router.route()`.
    *   Gate post-router steps (trapping, underbase) by `image_class`.
