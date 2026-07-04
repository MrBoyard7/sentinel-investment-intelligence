#!/usr/bin/env python3
"""
Convenience script: run the pipeline once against the local demo fixtures
and print a summary. Equivalent to `python -m sentinel.cli seed-demo`.

Usage:
    python scripts/seed_demo_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["seed-demo"]))
