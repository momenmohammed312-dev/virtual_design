# 🎨 Silk Screen Image Processor

Professional color separation tool for screen printing. Converts digital images into print-ready color films.

## ✨ Features

- **Automatic Color Separation** using K-Means clustering
- **Stroke Width Validation** for print reliability
- **Edge Cleaning** and noise removal
- **Halftone Generation** for gradients and photos
- **Multiple Export Formats** (PNG, PDF, SVG)
- **Professional Output** with documentation

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/yourusername/silk-screen-processor.git
cd silk-screen-processor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Quick Start

```bash
# Basic usage
python main.py --input design.jpg

# With all features
python main.py --input design.jpg --colors 4 --dpi 300 --clean --validate-strokes --halftone
```

## 📖 Usage Examples

### Simple 4-Color Separation
```bash
python main.py --input logo.png --colors 4
```

### High-Quality with Validation
```bash
python main.py --input design.jpg --colors 3 --dpi 600 --clean --validate-strokes --min-stroke 0.5
```

### Photo with Halftone
```bash
python main.py --input photo.jpg --colors 4 --halftone --lpi 65 --dot-shape round
```

### Full Processing Pipeline
```bash
python main.py \
  --input artwork.png \
  --output my_films \
  --colors 4 \
  --dpi 300 \
  --clean \
  --validate-strokes \
  --min-stroke 0.5 \
  --thicken \
  --halftone \
  --lpi 55 \
  --pdf \
  --zip
```

## ⚙️ Command Line Options

### Required
- `--input, -i` : Input image path

### Color Separation
- `--colors, -c` : Number of colors (1-16, default: 4)
- `--attempts` : K-means attempts (default: 10)

### Quality
- `--dpi` : Target DPI (default: 300)
- `--detail-level` : Processing detail (high/medium/low)

### Edge Cleaning
- `--clean` : Enable edge cleaning
- `--kernel-size` : Morphology kernel size (default: 3)
- `--min-area` : Minimum object area in pixels (default: 50)

### Stroke Validation
- `--validate-strokes` : Enable stroke width validation
- `--min-stroke` : Minimum width in mm (default: 0.5)
- `--thicken` : Auto-thicken thin strokes

### Halftone
- `--halftone` : Generate halftone patterns
- `--lpi` : Lines per inch (20-100, default: 55)
- `--angle` : Screen angle in degrees (default: 45)
- `--dot-shape` : Dot shape (round/square/ellipse)

### Export
- `--no-png` : Skip PNG export
- `--pdf` : Export combined PDF
- `--svg` : Export SVG (experimental)
- `--zip` : Create ZIP archive

### Other
- `--output, -o` : Output directory (default: output)
- `--quiet, -q` : Suppress verbose output

## 📁 Output Structure

```
output/
├── film_01_Black.png           # Individual color films
├── film_02_Cyan.png
├── film_03_Magenta.png
├── film_04_Yellow.png
├── films_combined.pdf          # Combined PDF (if --pdf)
├── metadata.json               # Processing metadata
├── README.txt                  # Print instructions
└── films.zip                   # Archive (if --zip)
```

## 🎯 Recommended Settings

### T-Shirts (Simple Designs)
```bash
--colors 3 --dpi 300 --clean --validate-strokes
```

### Posters (Detailed)
```bash
--colors 4 --dpi 600 --clean --validate-strokes --min-stroke 0.3
```

### Photographs
```bash
--colors 4 --halftone --lpi 65 --dot-shape round --dpi 300
```

## 🔧 Troubleshooting

### "Image too small" error
Increase DPI or use a higher resolution image.

### Thin strokes warning
Use `--thicken` to automatically thicken strokes, or increase `--min-stroke`.

### Colors not separating well
Try increasing `--attempts` or adjusting `--colors` count.

### PDF export not working
Install reportlab: `pip install reportlab`

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Support

For issues and questions, please open a GitHub issue.
