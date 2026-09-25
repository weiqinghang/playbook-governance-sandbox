#!/usr/bin/env python3
import os
import sys
from pathlib import Path


target = Path(__file__).resolve().parents[1] / ".playbook" / "scripts" / Path(__file__).name
if not target.is_file():
    raise SystemExit(f"Missing canonical playbook script: {target}")

os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
