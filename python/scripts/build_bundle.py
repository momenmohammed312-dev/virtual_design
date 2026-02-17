"""
Build Python bundle for distribution
Creates a standalone Python environment with all dependencies
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def create_bundle():
    """Create Python bundle for desktop app"""
    
    print("=" * 60)
    print("Building Python Bundle for Desktop Distribution")
    print("=" * 60)
    
    # Paths
    project_root = Path(__file__).parent.parent
    bundle_dir = project_root / 'bundle'
    
    # Clean previous bundle
    if bundle_dir.exists():
        print(f"\n🗑️  Removing old bundle...")
        shutil.rmtree(bundle_dir)
    
    bundle_dir.mkdir()
    
    # Step 1: Create virtual environment
    print(f"\n📦 Creating virtual environment...")
    venv_dir = bundle_dir / 'venv'
    subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
    
    # Determine python executable in venv
    if sys.platform == 'win32':
        python_exe = venv_dir / 'Scripts' / 'python.exe'
        pip_exe = venv_dir / 'Scripts' / 'pip.exe'
    else:
        python_exe = venv_dir / 'bin' / 'python'
        pip_exe = venv_dir / 'bin' / 'pip'
    
    # Step 2: Install dependencies
    print(f"\n📥 Installing dependencies...")
    requirements = project_root / 'requirements.txt'
    subprocess.run([str(pip_exe), 'install', '-r', str(requirements)], check=True)
    
    # Step 3: Copy source code
    print(f"\n📋 Copying source code...")
    src_files = ['core', 'utils', 'config', 'main.py']
    
    for item in src_files:
        src = project_root / item
        dst = bundle_dir / item
        
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    
    # Step 4: Create launcher script
    print(f"\n🚀 Creating launcher...")
    
    if sys.platform == 'win32':
        launcher = bundle_dir / 'run.bat'
        launcher_content = f"""@echo off
"{python_exe}" main.py %*
"""
    else:
        launcher = bundle_dir / 'run.sh'
        launcher_content = f"""#!/bin/bash
"{python_exe}" main.py "$@"
"""
    
    launcher.write_text(launcher_content)
    
    if sys.platform != 'win32':
        os.chmod(launcher, 0o755)
    
    # Step 5: Create README
    print(f"\n📝 Creating README...")
    readme = bundle_dir / 'README.txt'
    readme_content = """
Silk Screen Python Engine - Standalone Bundle
=============================================

This is a standalone Python environment with all dependencies included.

Usage:
------
Windows:
    run.bat --input image.jpg --colors 4

Mac/Linux:
    ./run.sh --input image.jpg --colors 4

For full options:
    run.bat --help

Dependencies are pre-installed in the venv/ directory.
No additional setup required!

"""
    readme.write_text(readme_content)
    
    # Step 6: Create zip archive
    print(f"\n📦 Creating archive...")
    archive_name = f'silk_screen_python_bundle_{sys.platform}'
    shutil.make_archive(
        str(project_root / archive_name),
        'zip',
        bundle_dir
    )
    
    print(f"\n✅ Bundle created successfully!")
    print(f"📁 Location: {project_root / archive_name}.zip")
    print(f"📏 Size: {(project_root / archive_name).with_suffix('.zip').stat().st_size / 1024 / 1024:.1f} MB")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    create_bundle()
