# Virtual Design — Professional Silk Screen Color Separation Studio

A Flutter desktop application with an embedded Python image processing engine. Automates the full color separation pipeline for silk screen printing studios — from raw design upload to production-ready film files per color layer.

## Overview

Color separation for silk screen printing is traditionally done manually in Photoshop, taking significant time per design. Virtual Design replaces that workflow with an automated pipeline: upload an image, configure layer settings, and get print-ready separated film files — driven by a Python computer vision engine running locally on the machine.

## Architecture

**Flutter (UI layer) → Python Bridge (subprocess) → Python CV Engine (processing)**

The Flutter app communicates with the Python engine via a `PythonProcessor` bridge that spawns a subprocess, streams real-time progress updates (`PROGRESS:xx:message`), and collects structured output. No server needed — everything runs offline on Windows desktop.

```
lib/
├── core/
│   └── python_bridge/
│       ├── python_processor.dart   — Subprocess manager with progress streaming
│       ├── python_config.dart      — Python path discovery and initialization
│       └── process_result.dart     — Typed result model
├── presentation/
│   ├── upload/       — Image input
│   ├── setup/        — Per-layer dot size configuration
│   ├── preview/      — Color layer preview before export
│   ├── batch/        — Batch processing queue
│   └── files/        — Output file management
└── data/
    └── repositories/ — Processing settings persistence (Hive)

python/
├── main.py                     — Pipeline orchestrator (10-step flow)
├── core/
│   ├── decision_engine.py      — Unified Decision Oracle (routing logic)
│   ├── pipeline_router.py      — Selects optimal processing path
│   ├── pipeline_controller.py  — Executes the chosen pipeline
│   ├── ai_vision_bridge.py     — Qwen3-VL local AI model integration
│   ├── color_separator.py      — K-Means color cluster separation
│   ├── image_classifier.py     — Auto-detects image type (text/artwork/photo)
│   ├── halftone_generator.py   — Halftone dot generation (round/square/ellipse)
│   ├── per_layer_halftone.py   — Per-layer halftone with configurable LPI/angle
│   ├── edge_perfection.py      — Edge enhancement per image class
│   ├── stroke_validator.py     — Enforces minimum printable stroke width (mm)
│   ├── print_calibration.py    — DPI/mm calibration + scale validation
│   ├── mask_generator.py       — Binary masks per color layer
│   ├── underbase_generator.py  — White underbase for dark garments
│   ├── registration_marks.py   — Print registration cross marks
│   ├── vector_exporter.py      — SVG/PDF vector output
│   └── exporter.py             — PNG/PDF/ZIP final export
└── config/
    └── settings.py             — All processing parameters (dataclass)
```

## Python Processing Pipeline

The engine runs a 10-step pipeline per image:

1. **Image Loading** — Safe load with alpha channel handling
1. **Decision Oracle** — Classifies image type (text_logo / artwork / photo) and selects parameters
1. **AI Vision Analysis** — Optional Qwen3-VL local model for intelligent parameter tuning
1. **Color Separation** — K-Means clustering to isolate individual ink colors
1. **Per-Layer Processing** — Edge cleaning, stroke validation, halftone generation
1. **Physical Print Modeling** — Enforces real-world printability constraints (min stroke in mm)
1. **Underbase Generation** — White layer for dark substrate printing
1. **Registration Marks** — Cross-hair alignment marks per layer
1. **Edge Perfection** — Class-aware edge enhancement (different treatment for text vs artwork vs photo)
1. **Export** — PNG layers + combined PDF + ZIP bundle

## Key Technical Features

- **AI Decision Engine** — Qwen3-VL VLM runs locally (no API) for image classification and parameter recommendation, with graceful fallback to heuristic rules when model unavailable
- **Physical Print Constraints** — Stroke validator rejects or auto-thickens elements below minimum printable width (configurable in mm), preventing wasted film
- **Halftone Engine** — Round/square/ellipse dot shapes, configurable LPI and angle per layer
- **Calibration System** — DPI-accurate mm grid generation and scale validation templates
- **Batch Processing** — Queue multiple designs and process unattended
- **Offline-First** — Entire pipeline runs locally, no internet required

## Tech Stack

|Component       |Technology                                    |
|----------------|----------------------------------------------|
|UI Framework    |Flutter (Dart) — Desktop (Windows/macOS/Linux)|
|State Management|GetX                                          |
|Python Engine   |Python 3.8+                                   |
|Computer Vision |OpenCV (cv2) + NumPy                          |
|AI Model        |Qwen3-VL 2B (local, via llama.cpp)            |
|Color Clustering|K-Means (scikit-learn)                        |
|Vector Export   |SVG + PDF                                     |
|Local Storage   |Hive + Shared Preferences                     |
|License System  |Flutter Secure Storage                        |
|CI/CD           |GitHub Actions                                |
|Localization    |Arabic + English (RTL support)                |

## Getting Started

### Prerequisites

- Flutter 3.3+ with Desktop support enabled
- Python 3.8+
- OpenCV, NumPy, scikit-learn

### Install Python dependencies

```bash
cd python
pip install -r requirements.txt
# or
python setup.py install
```

### Run the app

```bash
git clone https://github.com/momenmohammed312-dev/virtual_design
cd virtual_design
flutter pub get
flutter run -d windows
```

The Flutter app auto-discovers the Python executable on launch. Set `QWEN_MODEL_PATH` and `QWEN_MMPROJ_PATH` environment variables to enable AI-assisted processing.

## Use Case

Built for real silk screen printing studios as a commercial desktop product. Replaces manual Photoshop color separation workflows with an automated, non-technical interface that printing operators can use directly — with professional RIP-level output quality.

## Screenshots

> Coming soon

## Author

**Moamen Mohamed** — Flutter Developer  
[GitHub](https://github.com/momenmohammed312-dev)
