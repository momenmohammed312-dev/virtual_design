"""
Logger utility for consistent output formatting
"""

from datetime import datetime
from typing import Optional
import sys

class Logger:
    """Custom logger with colors and formatting"""
    
    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
    }
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.start_time = None
    
    def _colorize(self, text: str, color: str) -> str:
        """Add color to text"""
        if sys.platform == 'win32':
            # Windows might not support ANSI colors
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
    
    def info(self, message: str):
        """Info message"""
        if self.verbose:
            print(f"ℹ️  {message}")
    
    def success(self, message: str):
        """Success message"""
        if self.verbose:
            print(self._colorize(f"✅ {message}", 'green'))
    
    def warning(self, message: str):
        """Warning message"""
        if self.verbose:
            print(self._colorize(f"⚠️  {message}", 'yellow'))
    
    def error(self, message: str):
        """Error message"""
        print(self._colorize(f"❌ {message}", 'red'), file=sys.stderr)
    
    def step(self, step_num: int, total_steps: int, message: str):
        """Step progress"""
        if self.verbose:
            print(f"\n{'='*60}")
            print(self._colorize(
                f"Step {step_num}/{total_steps}: {message}",
                'bold'
            ))
            print('='*60)
    
    def progress(self, current: int, total: int, item: str = "item"):
        """Progress indicator"""
        if self.verbose:
            percentage = (current / total) * 100
            print(f"   Progress: {current}/{total} ({percentage:.0f}%) - {item}")
    
    def start_timer(self):
        """Start timing"""
        self.start_time = datetime.now()
    
    def end_timer(self):
        """End timing and print elapsed"""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            self.info(f"⏱️  Time elapsed: {elapsed.total_seconds():.2f}s")
            self.start_time = None
    
    def header(self, title: str):
        """Print header"""
        border = "=" * 60
        print(f"\n{border}")
        print(self._colorize(title.center(60), 'bold'))
        print(f"{border}\n")
    
    def separator(self):
        """Print separator line"""
        if self.verbose:
            print("-" * 60)
