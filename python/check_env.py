import importlib
import sys

packages = [
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("reportlab", "reportlab"),
    ("llama_cpp", "llama-cpp-python"),
    ("PIL", "pillow"),
    ("skimage", "scikit-image"),
    ("base64", "built-in"),
    ("json", "built-in"),
]

print(f"--- Environment Diagnosis ---")
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print("-" * 30)

missing = []
for module_name, pip_name in packages:
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name:15} | INSTALLED")
    except ImportError:
        print(f"❌ {module_name:15} | MISSING (pip install {pip_name})")
        missing.append(pip_name)

print("-" * 30)
if not missing:
    print("✨ ALL SYSTEMS GO! Your Python environment is ready for the Silk Screen Pipeline.")
else:
    print(f"⚠️  WAIT! You still need to install: {' '.join(missing)}")
    print(f"Run: pip install {' '.join(missing)}")
