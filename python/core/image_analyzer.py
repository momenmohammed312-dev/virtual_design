import os
import mimetypes

class ImageAnalyzer:
    """Analyzes an image file to extract metadata, determine format (Raster vs Vector) and resolution."""

    VECTOR_EXTENSIONS = {'.svg', '.ai', '.eps', '.pdf'}
    RASTER_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp', '.psd'}

    @classmethod
    def analyze(cls, filepath: str) -> dict:
        """
        Analyze the given file and return a dictionary containing its metadata.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        # Get file size
        file_size_bytes = os.path.getsize(filepath)
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Get extension and determine type
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext in cls.VECTOR_EXTENSIONS:
            image_type = "Vector"
            format_name = ext.replace('.', '').upper()
        else:
            image_type = "Raster"
            format_name = ext.replace('.', '').upper() if ext else "UNKNOWN"

        # Safe defaults
        width, height = 0, 0
        dpi = 72
        color_mode = "Unknown"

        # If it's a Raster, attempt to read properties using PIL
        if image_type == "Raster":
            try:
                from PIL import Image
                with Image.open(filepath) as img:
                    width, height = img.size
                    color_mode = img.mode
                    # Try to get DPI
                    info = img.info
                    dpi_tuple = info.get("dpi", (72, 72))
                    if isinstance(dpi_tuple, tuple) and len(dpi_tuple) == 2:
                        dpi = int(dpi_tuple[0])
                    else:
                        dpi = int(dpi_tuple)
            except Exception as e:
                # Fallback to OpenCV if PIL fails
                try:
                    import cv2
                    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        height, width = img.shape[:2]
                        if len(img.shape) == 3:
                            color_mode = "RGBA" if img.shape[2] == 4 else "RGB"
                        else:
                            color_mode = "Grayscale"
                except:
                    pass

        return {
            "filename": os.path.basename(filepath),
            "image_type": image_type,
            "format": format_name,
            "size_mb": round(file_size_mb, 2),
            "width": width,
            "height": height,
            "dpi": dpi,
            "color_mode": color_mode
        }
