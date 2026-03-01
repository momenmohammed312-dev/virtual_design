import sys
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image


def _write_test_image(path: Path, size=(50, 50)) -> None:
    w, h = size
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Small colored patch to exercise color processing
    img[0:h//2, 0:w//2] = [255, 0, 0]     # Red quadrant
    img[0:h//2, w//2:w] = [0, 255, 0]     # Green quadrant
    img[h//2:h, 0:w//2] = [0, 0, 255]     # Blue quadrant
    Image.fromarray(img).save(path, format="PNG")


def test_integration_pipeline_runs(tmp_path: Path):
    # Prepare a tiny test image
    input_path = tmp_path / "input.png"
    _write_test_image(input_path, size=(60, 60))

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Path to the CLI entry point
    main_path = Path(__file__).resolve().parents[1] / "main.py"  # python/main.py

    cmd = [sys.executable, str(main_path), "--input", str(input_path), "--output", str(output_dir), "--colors", "3", "--dpi", "300"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Debug prints (optional)
    if result.stdout:
        print("STDOUT:\n" + result.stdout)
    if result.stderr:
        print("STDERR:\n" + result.stderr)

    assert result.returncode == 0, f"Pipeline failed with exit code {result.returncode}"

    # Verify that at least one PNG was produced in the output directory
    produced = list(output_dir.glob("*.png"))
    assert len(produced) >= 1, f"Expected at least 1 PNG file produced, got: {produced}"
