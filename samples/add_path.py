"""
Helper module to add remotable_function to path for samples.
Import this at the beginning of sample files.
"""

import sys
from pathlib import Path

# Add the parent directory (repository root) to Python path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))