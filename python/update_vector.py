import sys

file_path = "python/core/vector_exporter.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add binary constraint before finding contours
if "bw_for_contours = cv2.bitwise_not(bw)" in content:
    strict_binary_fix = """
        # FINAL FIX: enforce strict binary integrity directly before contour trace
        bw = (bw > 127).astype(np.uint8) * 255

        # Ensure ink=BLACK(0) for contour tracing
        # preprocess_mask_for_vector uses THRESH_BINARY which preserves input polarity
        # But findContours traces WHITE(255) regions — so we need design=WHITE, background=BLACK
        # This is INVERTED from silk screen convention, only for the purpose of contour detection
        bw_for_contours = cv2.bitwise_not(bw)
"""
    # Replace that block
    old_block = """
        # Ensure ink=BLACK(0) for contour tracing
        # preprocess_mask_for_vector uses THRESH_BINARY which preserves input polarity
        # But findContours traces WHITE(255) regions — so we need design=WHITE, background=BLACK
        # This is INVERTED from silk screen convention, only for the purpose of contour detection
        bw_for_contours = cv2.bitwise_not(bw)
"""
    content = content.replace(old_block.strip() + "\n", strict_binary_fix.strip() + "\n")

import re

# Remove DFS
pattern = r"# FIX GROUP 3\.1 & 3\.2: Fixed even-odd fill and recursive hierarchy traversal\n\s*# Define recursive DFS for proper hole handling(.*?)def _append_contour_to_path"
content = re.sub(pattern, "def _append_contour_to_path", content, flags=re.DOTALL)

# Replace the drawing portion
drawing_pattern = r"# FIX GROUP 3\.1 & 3\.2: Use even-odd fill with recursive hierarchy traversal\n\s*c\.setFillColorRGB\(0, 0, 0\)\n\s*try:\n\s*# Try ReportLab 4\.x\+ even-odd fill mode first(.*?)c\.drawPath\(p, fill=1, stroke=0\)"
new_drawing = """# FIX GROUP 3.1 & 3.2: Native contour-based path fill (NO DFS fallback)
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
            logger.info(f"[VectorExporter] Used native contour-based path fill for {len(contours)} contours")"""

content = re.sub(drawing_pattern, new_drawing, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated vector_exporter.py")
