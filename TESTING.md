# Testing Guide — Virtual Design

## Python Pipeline Tests

### 1️⃣ Test Imports (Dependencies)

Quick validation that all Python dependencies are installed:

```bash
cd virtual_design
python python/test_imports.py
```

**Expected Output:**
```
Testing Python imports...
  ✓ NumPy (numpy)
  ✓ OpenCV (cv2)
  ✓ Pillow (PIL)
  ✓ scikit-image (skimage)
  ✓ SciPy (scipy)

Testing local modules...
  ✓ core.color_separator
  ✓ core.mask_generator
  ✓ core.edge_cleaner
  ✓ core.image_loader

✅ All imports successful!
```

### 2️⃣ Test Pipeline (End-to-End)

Full pipeline test with test image generation:

```bash
python python/test_pipeline.py
```

**What it does:**
1. Creates a test image with 4 colored quadrants
2. Runs main.py to process it
3. Validates output films were created
4. Cleans up

**Expected Output:**
```
[1/4] Creating test image...
✓ Test image created: python/samples/test_simple.png

[2/4] Running pipeline...
Command: python ... main.py --input ... --colors 3 --dpi 300
STDOUT:
Step 1/9: Loading image
Step 2/9: Separating 3 colors
...
Step 9/9: Exporting
OUTPUT_DIR:/path/to/output_test/

✓ Pipeline completed

[3/4] Verifying output...
Found 3 film files:
  - film_0_k.png
  - film_1_cyan.png
  - film_2_magenta.png
✓ Output files generated

[4/4] Cleanup...
✓ Cleaned up

==================================================
✅ ALL TESTS PASSED!
==================================================
```

### 3️⃣ Test Flutter

Run Flutter tests:

```bash
flutter test
```

Or specific test:

```bash
flutter test test/python_processor_test.dart
```

### 4️⃣ Integration Test (Manual)

Full app integration test:

```bash
# On Windows
flutter run -d windows

# On Android
flutter run -d android
```

Then in the app:
1. Go to Upload tab
2. Select a test image (4-colored recommended)
3. Set colors to 3-4
4. Click Process
5. Observe real-time progress ("Step 1/9", "Step 2/9", etc.)
6. Verify output films displayed

---

## Testing Checkpoints

### ✓ Checkpoint 1: Python Environment
- [ ] `python --version` returns 3.8+
- [ ] `pip list | grep opencv-python` shows version
- [ ] `python test_imports.py` shows all ✓

### ✓ Checkpoint 2: Database Setup  
- [ ] `chmod +x install_deps.sh` (Linux/macOS)
- [ ] `install_deps.bat` (Windows) or `install_deps.sh` runs without errors
- [ ] `.venv` directory created
- [ ] All packages in requirements.txt installed

### ✓ Checkpoint 3: Pipeline Test
- [ ] `python test_pipeline.py` returns exit code 0
- [ ] `python/output_test/` contains ≥3 film_*.png files
- [ ] Each film is valid PNG (can open in viewer)

### ✓ Checkpoint 4: Flutter Build
- [ ] `flutter analyze` returns no errors
- [ ] `flutter test` passes
- [ ] `flutter run` starts without crashes

### ✓ Checkpoint 5: Full Integration
- [ ] Upload image → Process → See "Step 1/9" in real-time
- [ ] Process completes successfully
- [ ] Output directory created with films
- [ ] No permission errors
- [ ] No Python process hanging

---

## Troubleshooting

### Python tests fail with "No module named 'numpy'"

```bash
# Reinstall dependencies
pip install -r python/requirements.txt

# Or if using venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate  # Windows
pip install -r python/requirements.txt
```

### Flutter tests fail with "Can't find python"

Make sure Python is in PATH:

```bash
echo $PATH  # Check if /usr/bin/python3 or C:\Python311 is there
which python3  # Linux/macOS
where python  # Windows
```

### Integration test fails at "OUTPUT_DIR:"

- Check that main.py has `print(f"OUTPUT_DIR:{path}", flush=True)` at end
- Verify PythonProcessor reads this line with `line.startsWith('OUTPUT_DIR:')`
- Run `python test_pipeline.py` to debug Python side

### Slow performance in tests

- Normal: ~2-10s for 500px image
- If >30s: Check CPU usage, may need fewer cores (`--workers 2`)
- If hanging: Python process likely stuck, check logs

---

## Performance Benchmarks

Target metrics:

| Image Size | Colors | Expected Time | Notes |
|-----------|--------|---|---|
| 200×200 | 3-4 | 0.5-1.0s | Test image |
| 800×600 | 3-4 | 2-3s | Phone screenshot |
| 2K | 4-6 | 5-10s | High-res design |
| 4K | 6-8 | 15-30s | Professional artwork |

---

## CI/CD Integration

For GitHub Actions / GitLab CI, verify:

1. Python 3.8+ available
2. Flutter 3.0+ available
3. Run `install_deps.sh` in test setup
4. Run `python test_imports.py` && `python test_pipeline.py`
5. Run `flutter test` && `flutter analyze`

Example GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: |
          chmod +x install_deps.sh
          ./install_deps.sh
          python python/test_imports.py
          python python/test_pipeline.py
      - uses: subosito/flutter-action@v2
      - run: flutter test && flutter analyze
```

---

## Debugging Tips

### Enable verbose logging

```bash
# Python
python python/main.py --input ... --output ... --verbose

# Flutter
flutter run -v
```

### Profile performance

```bash
time python python/main.py --input test.jpg --output out --colors 4
# Shows total time
```

### Check stdout in real-time

```bash
# Windows
python python/main.py --input test.jpg --output out 2>&1 | findstr "Step"

# Linux
python python/main.py --input test.jpg --output out 2>&1 | grep "Step"
```

---

**Last Updated:** Phase 6 of SOP
**Next:** Phase 7 — License Enforcement & Error Handling
