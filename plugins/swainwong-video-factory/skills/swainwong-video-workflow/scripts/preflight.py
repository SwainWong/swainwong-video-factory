#!/usr/bin/env python3
"""Fail-closed runtime dependency check for the video workflow hard gates."""
from __future__ import annotations

import importlib.util
import json
import shutil


def inspect_runtime() -> dict:
    checks = {
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "python_module_cv2": importlib.util.find_spec("cv2") is not None,
        "python_module_numpy": importlib.util.find_spec("numpy") is not None,
    }
    missing = [name for name, value in checks.items() if not value]
    return {
        "schema": "swainwong.video-workflow-preflight.v1",
        "status": "PASS" if not missing else "FAIL",
        "checks": checks,
        "missing": missing,
    }


def main() -> None:
    result = inspect_runtime()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
