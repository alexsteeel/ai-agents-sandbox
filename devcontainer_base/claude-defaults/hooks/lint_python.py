#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path.cwd()
LOG_DIR = ROOT / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "linters_python.json"


def run(cmd: list[str], env: dict | None = None) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env={**os.environ, **(env or {})},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)


def run_ruff() -> dict:
    rc, out, err = run(["uvx", "ruff", "check", "."])  # auto-install via uvx
    return {
        "tool": "ruff",
        "rc": rc,
        "stdout": out,
        "stderr": err,
    }


def run_black() -> dict:
    rc, out, err = run(["uvx", "black", "--check", "."])  # check only, no writes
    return {
        "tool": "black",
        "rc": rc,
        "stdout": out,
        "stderr": err,
    }


def summarize(results: list[dict]) -> dict:
    summary = {
        "total": len(results),
        "failed": sum(1 for r in results if r.get("rc", 0) != 0),
        "tools": {r["tool"]: r.get("rc", 1) for r in results},
    }
    return summary


def main() -> int:
    try:
        _payload = sys.stdin.read()
    except Exception:
        _payload = ""

    results: list[dict] = []
    for fn in (run_ruff, run_black):
        results.append(fn())

    summary = summarize(results)
    LOG_FILE.write_text(json.dumps({"summary": summary, "results": results}, indent=2))

    print("Python linters summary:")
    print(json.dumps(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
