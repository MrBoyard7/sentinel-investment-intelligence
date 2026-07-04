#!/usr/bin/env python3
"""
Convenience script: run one full pipeline pass.
Equivalent to `python -m sentinel.cli run`.

Usage:
    python scripts/run_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["run"]))
