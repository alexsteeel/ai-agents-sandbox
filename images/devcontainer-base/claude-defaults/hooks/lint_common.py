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
LOG_FILE = LOG_DIR / "linters_common.json"


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


def run_shellcheck() -> dict:
    # Find shell files and run shellcheck
    find_cmd = [
        "bash",
        "-lc",
        "set -o pipefail; find . -type f \\n          -name '*.sh' -print0 | xargs -0 -r shellcheck -S style",
    ]
    rc, out, err = run(find_cmd)
    return {
        "tool": "shellcheck",
        "rc": rc,
        "stdout": out,
        "stderr": err,
    }


def run_shfmt() -> dict:
    # Show diffs for formatting issues
    rc, out, err = run(["shfmt", "-d", "."])
    # Treat non-empty diff as failure for summary purposes
    failed = 1 if out.strip() or err.strip() else 0
    return {
        "tool": "shfmt",
        "rc": failed if rc == 0 else rc,
        "stdout": out,
        "stderr": err,
    }


def run_hadolint() -> dict:
    cmd = [
        "bash",
        "-lc",
        "set -o pipefail; find . -type f -iname 'Dockerfile*' -print0 | xargs -0 -r hadolint",
    ]
    rc, out, err = run(cmd)
    return {
        "tool": "hadolint",
        "rc": rc,
        "stdout": out,
        "stderr": err,
    }


def run_yamllint() -> dict:
    rc, out, err = run(["yamllint", "-s", "."])  # -s: stricter, prints only errors
    return {
        "tool": "yamllint",
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
    for fn in (run_shellcheck, run_shfmt, run_hadolint, run_yamllint):
        results.append(fn())

    summary = summarize(results)
    LOG_FILE.write_text(json.dumps({"summary": summary, "results": results}, indent=2))

    print("Common linters summary:")
    print(json.dumps(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
