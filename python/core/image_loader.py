"""Image loading utilities (placeholder).
"""
try:
    from PIL import Image
except Exception:
    Image = None

def load_image(path):
    """Load an image and return a PIL Image object (placeholder)."""
    if Image is None:
        raise RuntimeError("Pillow is not available")
    return Image.open(path)
