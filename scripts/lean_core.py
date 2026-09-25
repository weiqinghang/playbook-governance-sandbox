#!/usr/bin/env python3
"""Root wrapper for the canonical v0.13 Lean Core helper."""

import os
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[1] / ".playbook" / "scripts" / "lean_core.py"
os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
