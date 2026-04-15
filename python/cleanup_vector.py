import sys, re

file_path = "python/core/vector_exporter.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove the orphaned else block
# We will just replace everything from `c.setFillColorRGB(0, 0, 0)` down to the start of `c.showPage()`
pattern = r"c\.setFillColorRGB\(0, 0, 0\).*?c\.showPage\(\)"
replacement = """c.setFillColorRGB(0, 0, 0)
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
            
        c.showPage()"""
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Cleaned up orphaned DFS code")
