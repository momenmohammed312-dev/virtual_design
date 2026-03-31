
import numpy as np
import cv2
from pathlib import Path
import sys
import os

# Create dummy mask
mask = np.zeros((200, 200), dtype=np.uint8)
cv2.rectangle(mask, (50, 50), (150, 150), 255, -1)

# Add python to path
sys.path.append(r"G:\Designs\design app\virtual_design\python")
from core.vector_exporter import export_vector_pdf

output_path = Path(r"G:\Designs\design app\virtual_design\test_output_color.pdf")
try:
    from reportlab.lib.colors import Color, black, white
    from reportlab.lib.units import mm, inch
    print("ReportLab sub-modules imported successfully.")
    
    print("Starting export_vector_pdf with colors...")
    export_vector_pdf(
        masks=[mask],
        colors=[(255, 0, 0)], # Red
        color_names=["Red"],
        output_path=output_path,
        dpi=300
    )
    print(f"Export finished. File exists: {output_path.exists()}")
    if output_path.exists():
        print(f"File size: {os.path.getsize(output_path)} bytes")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
