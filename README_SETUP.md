# Virtual Design — Silk Screen Studio
## Installation & Quick Start Guide

### Prerequisites
- Flutter 3.0+ with Dart 3.8+
- Python 3.8+
- Git
- (Android only) Android SDK 21+

### 1️⃣ Setup Python Environment

#### Windows
```bash
cd virtual_design
install_deps.bat
```

#### Linux / macOS
```bash
cd virtual_design
chmod +x install_deps.sh
./install_deps.sh
```

### 2️⃣ Verify Python Pipeline

```bash
# Activate venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Test main.py
python python/main.py --input python/samples/test.jpg --output python/out --colors 4
```

**Expected Output:**
```
Step 1/9: Loading image
Step 2/9: Separating 4 colors
...
Step 9/9: Exporting
OUTPUT_DIR:/path/to/output
```

Exit code should be `0`.

### 3️⃣ Setup Flutter

```bash
flutter pub get
flutter analyze
```

### 4️⃣ Run Application

#### Windows
```bash
flutter run -d windows
```

#### Android
```bash
flutter run -d android
```

#### Web (Debug)
```bash
flutter run -d chrome
```

---

## Project Structure

```
lib/
├── main.dart                    # App entry point
├── app/
│   ├── bindings/                # GetX dependency injection
│   ├── routes/                  # Navigation
│   └── themes/                  # UI theme
├── core/
│   ├── enums/                   # App enums
│   ├── licensing/               # License service
│   ├── python_bridge/           # Python ↔ Dart communication
│   └── permissions/             # Permission handling
├── data/
│   ├── models/                  # Hive models
│   ├── repositories/            # Repository pattern
│   └── datasources/             # Local storage
├── domain/
│   ├── entities/                # Business entities
│   └── repositories/            # Abstract repositories
└── presentation/
    ├── dashboard/               # Dashboard page
    ├── upload/                  # Upload page
    ├── setup/                   # Setup page
    ├── preview/                 # Preview page
    └── license/                 # License page

python/
├── core/
│   ├── color_separator.py       # K-Means color separation
│   ├── mask_generator.py        # Binary mask generation
│   ├── edge_cleaner.py          # Edge smoothing
│   ├── halftone_generator.py    # Halftone processing
│   ├── binarizer.py             # Binarization
│   ├── stroke_validator.py      # Stroke validation
│   ├── registration_marks.py    # Registration marks
│   ├── exporter.py              # Export to SVG/PNG
│   └── __init__.py
├── main.py                      # CLI entry point
├── requirements.txt             # Dependencies
└── samples/                     # Sample images
```

---

## Troubleshooting

### Python not found
```bash
# Check Python installation
python --version
python3 --version

# Add Python to PATH if needed (Windows)
# setx PATH "%PATH%;C:\Python311"
```

### Missing packages
```bash
pip install -r requirements.txt
# or
pip install opencv-python numpy Pillow scikit-image pytest
```

### Flutter build errors
```bash
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

### Android permissions error
- Go to Settings > Apps > Virtual Design > Permissions
- Enable "Photos" or "All Files"

---

## Common Commands

```bash
# Run tests
flutter test
python -m pytest python/tests/

# Format code
flutter format lib/
black python/

# Analyze
flutter analyze
python -m pylint python/core/

# Generate Hive adapters
flutter pub run build_runner build

# Full app rebuild
flutter clean && flutter pub get && flutter run
```

---

## File Formats Supported

- **Input**: PNG, JPG, JPEG, TIFF, BMP
- **Output**: PNG (default), SVG (vector), PDF (for registration)

---

## Performance Notes

- Images up to 4K recommended (8K may require >500MB RAM)
- Processing time: ~2-10s per image depending on size and colors
- Multiprocessing: Uses all available CPU cores (configurable with `--workers`)

---

## License

© 2026 Virtual Design. Offline licensing system integrated.

For issues or questions, check `SOP_CHECKLIST.md`.
