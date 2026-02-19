#!/bin/bash
# install_deps.sh - Install Python dependencies for Virtual Design
# Linux/macOS script

set -e

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8+ before running this script."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "Found Python: $PYTHON_VERSION"

echo ""
echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

echo ""
echo "Upgrading pip..."
python -m pip install --upgrade pip

echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "============================================================"
echo "Installation complete!"
echo ""
echo "To activate the environment in future sessions, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the pipeline:"
echo "  python python/main.py --input_dir samples --output_dir out --colors 4"
echo "============================================================"
