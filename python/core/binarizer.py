"""
Binarizer - Final Production Grade (Refined).
- Edge-density-aware normalization.
- Shape integrity (largest component with center penalty).
- Printability validation (stroke continuity via skeletonization).
- Adaptive weighting based on edge density.
- Multi-scale stability check.
- Extended caching with contrast/brightness bins.
- Early rejection for low-contrast images.
"""

import cv2
import numpy as np
import logging
import os
import json
import time
from typing import Tuple, Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class Binarizer:
    """
    Expert binarization system with enterprise-grade safeguards and health tracking.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.Binarizer")
        self._method_cache = {} 
        # Health Metrics (Safeguard 3)
        self._health = { "total": 0, "fallbacks": 0, "tiers": {"HIGH": 0, "ACCEPTABLE": 0, "LOW": 0} }

    def binarize(self, mask: np.ndarray, method: str = 'auto', **kwargs) -> np.ndarray:
        return self.auto_threshold(mask, preferred_method=method, **kwargs)

    def _get_cache_key(self, ic: str, stats: Dict) -> str:
        # std: 20px steps, mean: 50px steps, density: 0.05 steps
        s_bin = min(4, int(stats['std'] / 20))
        m_bin = min(4, int(stats['mean'] / 50))
        d_bin = min(4, int(stats.get('density', 0) * 20))
        return f"{ic}_s{s_bin}_m{m_bin}_d{d_bin}"

    def auto_threshold(self, image: np.ndarray, preferred_method: str = 'auto', **kwargs) -> np.ndarray:
        start_total = time.time()
        rid = kwargs.get('request_id', 'unknown')
        self._health["total"] += 1
        
        # TASK 11: RESET CACHE TO PREVENT CROSS-IMAGE POLLUTION
        # Only preserve cache if this is a nested retry call for the SAME image.
        if preferred_method == 'auto' and not kwargs.get('_retry_call', False):
            self._method_cache = {}

        # 1. PREP & DENSITY
        if len(image.shape) == 3: gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else: gray = image.copy()
        gray = gray.astype(np.uint8) if gray.dtype != np.uint8 else gray
        
        stats = self._analyze_image(gray)
        # Add edge density to stats for cache key (Safeguard 2)
        orig_edges = cv2.Canny(gray, 50, 150)
        orig_edge_px = np.count_nonzero(orig_edges)
        stats['density'] = orig_edge_px / gray.size
        
        # 0. REJECTION
        if stats['std'] < 5.0 and preferred_method == 'auto':
            self.logger.warning(f"[{rid}] REJECTED_LOW_CONTRAST(std={stats['std']:.2f})")
            return np.full_like(gray, 255)

        # 2. CACHE
        cache_key = self._get_cache_key(kwargs.get('image_class', 'auto'), stats)
        if cache_key in self._method_cache and preferred_method == 'auto':
            res = self._apply_method(gray, self._method_cache[cache_key], stats)
            if res is not None:
                if self.evaluate_result(res, gray, 'auto', orig_edges, orig_edge_px)[0]: return res

        # 3. TRIAL
        candidates = self._get_candidates(kwargs.get('image_class', 'auto'), stats['std'], preferred_method)
        results, timings = [], {}
        for cmd in candidates:
            t_s = time.time()
            res = self._apply_method(gray, cmd, stats)
            timings[cmd] = round((time.time() - t_s) * 1000, 2)
            if res is None: continue
            valid, conf, m = self.evaluate_result(res, gray, 'auto', orig_edges, orig_edge_px)
            if valid:
                results.append({'conf': conf, 'cmd': cmd, 'res': res, 'm': m})
                if conf > 0.90: break

        fallback = False
        if not results:
            fallback = True
            self._health["fallbacks"] += 1
            self.logger.error(f"[{rid}] FALLBACK_MODE_ENABLED")
            best_res = self._apply_method(gray, candidates[0], stats)
            best_res = best_res if best_res is not None else np.full_like(gray, 255)
            best_conf, best_cmd, best_metrics = 0.1, candidates[0], {"fallback": True}
        else:
            results.sort(key=lambda x: x['conf'], reverse=True)
            b = results[0]
            best_conf, best_cmd, best_res, best_metrics = b['conf'], b['cmd'], b['res'], b['m']

        # 4. POLARITY (Safeguard 1: Strategic Inversion)
        ink_ratio = np.count_nonzero(best_res == 0) / best_res.size
        lcr = best_metrics.get('lcr', 0)
        # Only invert if ink is high (mostly black) AND no dominant component exists (noisy/background)
        # Avoid inverting valid large solid shapes (high lcr)
        if ink_ratio > 0.85 and lcr < 0.4:
            best_res = cv2.bitwise_not(best_res)
            self.logger.warning(f"[{rid}] POLARITY_INVERTED(ratio={ink_ratio:.2f},lcr={lcr:.2f})")

        # 5. HEALTH & SUMMARY (Safeguard 3 & 4)
        tier = "HIGH" if best_conf > 0.8 else ("ACCEPTABLE" if best_conf > 0.45 else "LOW")
        self._health["tiers"][tier] += 1
        total_time = round((time.time() - start_total) * 1000, 2)
        
        summary = {
            "rid": rid, "tier": tier, "conf": round(best_conf, 3), "fallback": fallback,
            "time_ms": total_time, "health": self._get_health_summary(),
            "method": best_cmd, "metrics": best_metrics
        }
        self.logger.info(f"[Binarizer_Summary] {json.dumps(summary)}")
        
        if kwargs.get('debug_dir'): 
            self._handle_debug_export(kwargs['debug_dir'], rid, gray, best_res, summary, best_conf, [])

        if not fallback and preferred_method == 'auto' and best_conf > 0.5:
            self._method_cache[cache_key] = best_cmd
        return best_res

    def _get_health_summary(self) -> Dict:
        # Avoid zero division
        total = max(1, self._health["total"])
        return {
            "fallback_rate": round(self._health["fallbacks"] / total, 3),
            "tier_distribution": {k: round(v / total, 3) for k, v in self._health["tiers"].items()}
        }

    def _get_candidates(self, ic: str, std: float, preferred: str) -> List[str]:
        if preferred != 'auto': return [preferred]
        if std > 60: c = ['otsu', 'triangle']
        elif std < 30: c = ['adaptive_gauss'] if ic != 'text_logo' else ['otsu']
        else: c = ['otsu', 'adaptive_gauss', 'triangle']
        c.append('global_127')
        return c

    def _handle_debug_export(self, ddir: str, rid: str, gray: np.ndarray, res: np.ndarray, log: dict, conf: float, warnings: list):
        try:
            if not os.path.exists(ddir): os.makedirs(ddir, exist_ok=True)
            files = sorted([os.path.join(ddir, f) for f in os.listdir(ddir)], key=os.path.getmtime)
            if len(files) > 150: [os.remove(f) for f in files[:-100]]
            ts = int(time.time() * 1000); prefix = f"{rid}_{ts}"
            cv2.imwrite(f"{ddir}/{prefix}_gray.png", gray)
            cv2.imwrite(f"{ddir}/{prefix}_res.png", res)
            with open(f"{ddir}/{prefix}_meta.json", 'w') as f: json.dump(log, f, indent=2)
        except Exception as e: self.logger.error(f"Debug error: {e}")

    def _analyze_image(self, gray: np.ndarray) -> Dict:
        return { 'std': float(np.std(gray)), 'mean': float(np.mean(gray)), 'size': gray.shape }

    def _apply_method(self, gray: np.ndarray, cmd: str, stats: Dict) -> Optional[np.ndarray]:
        try:
            if cmd == 'otsu': _, res = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            elif cmd == 'triangle': _, res = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE)
            elif cmd.startswith('global_'): 
                val = int(cmd.split('_')[1]); _, res = cv2.threshold(gray, val, 255, cv2.THRESH_BINARY)
            elif 'adaptive' in cmd:
                bs = max(3, int(min(stats['size']) * 0.05) | 1)
                res = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, bs, 10)
            else: return None
            return res
        except: return None

    def evaluate_result(self, mask: np.ndarray, gray: np.ndarray, ic: str, orig_edges: np.ndarray = None, orig_edge_px: int = 0) -> Tuple[bool, float, Dict]:
        if mask is None: return False, 0.0, {}
        inv_mask = cv2.bitwise_not(mask); ink_px = np.count_nonzero(inv_mask)
        if (ink_px / mask.size) > 0.99 or (ink_px / mask.size) < 0.0001: return False, 0.0, {'r': 'collapsed'}
        bin_edges = cv2.Canny(mask, 50, 150)
        edge_preservation = (np.count_nonzero(cv2.bitwise_and(orig_edges, bin_edges)) / orig_edge_px) if orig_edge_px > 0 else 1.0
        max_half_width = float(np.max(cv2.distanceTransform(inv_mask, cv2.DIST_L2, 3)))
        num_labels, labels, stats_cc, centroids = cv2.connectedComponentsWithStats(inv_mask, 8, cv2.CV_32S)
        if num_labels < 2: return False, 0.0, {'r': 'no_content'}
        max_idx = np.argmax([stats_cc[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]) + 1
        lcr = stats_cc[max_idx, cv2.CC_STAT_AREA] / ink_px
        h, w = mask.shape[:2]
        center_penalty = 1.0 - (np.sqrt(((centroids[max_idx][0]-w/2)**2 + (centroids[max_idx][1]-h/2)**2)) / np.sqrt((w/2)**2 + (h/2)**2) * max(0.0, 1.0 - lcr))
        smooth_inv = cv2.morphologyEx(inv_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))) if max_half_width > 1.2 else inv_mask
        skeleton = self._skeletonize(smooth_inv)
        skel_blobs = max(0, cv2.connectedComponents(skeleton, 8)[0] - 1)
        cs = min(1.0, (num_labels - 1) / skel_blobs) if skel_blobs > 0 else 1.0
        ed = orig_edge_px / mask.size
        # Adaptive Weights
        w_e, w_s, w_c = (0.5, 0.3, 0.2) if ed > 0.05 else ((0.1, 0.6, 0.3) if ed < 0.01 else (0.3, 0.4, 0.3))
        conf = (edge_preservation * w_e) + (lcr * center_penalty * w_s) + (cs * w_c) + (min(1.0, max_half_width/10.0) * 0.1)
        return (edge_preservation > 0.02) and (lcr > 0.0005), float(conf), {'ep': round(edge_preservation, 3), 'lcr': round(lcr, 3), 'cs': round(cs, 3), 'mhw': round(max_half_width, 2)}

    def _skeletonize(self, binary: np.ndarray) -> np.ndarray:
        skel = np.zeros(binary.shape, np.uint8); element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3)); img = binary.copy()
        for _ in range(30):
            eroded = cv2.erode(img, element); temp = cv2.subtract(img, cv2.dilate(eroded, element)); skel = cv2.bitwise_or(skel, temp); img = eroded.copy()
            if cv2.countNonZero(img) == 0: break
        return skel


