#!/bin/bash
# Virtual Design — Silk Screen Studio
# Python Dependency Installer for Mac/Linux

echo "============================================"
echo " Virtual Design — Silk Screen Studio"
echo " Python Dependency Installer"
echo "============================================"
echo ""

# البحث عن Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python not found!"
    echo "Install Python 3.8+ with your package manager:"
    echo "  Mac:   brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[OK] Python found: $($PYTHON --version)"
echo ""

# ترقية pip
echo "Upgrading pip..."
$PYTHON -m pip install --upgrade pip --quiet

# تثبيت المكتبات
echo "Installing dependencies..."
$PYTHON -m pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo " [SUCCESS] All dependencies installed!"
    echo " You can now use Virtual Design Silk Screen Studio."
    echo "============================================"
else
    echo ""
    echo "[ERROR] Some packages failed to install."
    echo "Try: sudo $PYTHON -m pip install -r requirements.txt"
    exit 1
fi
