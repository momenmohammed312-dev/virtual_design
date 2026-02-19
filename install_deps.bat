@echo off
REM install_deps.bat - Install Python dependencies for Virtual Design
REM Windows batch script

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+ before running this script.
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo.
echo ============================================================
echo Installation complete!
echo.
echo To activate the environment in future sessions, run:
echo   .venv\Scripts\activate.bat
echo.
echo To run the pipeline:
echo   python python/main.py --input_dir samples --output_dir out --colors 4
echo ============================================================

pause
