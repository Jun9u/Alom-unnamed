"""Check the Git index for accidental data uploads and a few common secrets.

This is a limited guard, not a complete security scanner. File contents are never printed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import PurePosixPath

MAX_BYTES = 5 * 1024 * 1024
BLOCKED_SUFFIXES = {
    ".aac",
    ".ckpt",
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".ogg",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".wav",
    ".webm",
}
TOKEN_PATTERNS = (
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
)


def inspect_file(path: str, content: bytes) -> list[str]:
    """Return reasons to reject a staged file without exposing its contents."""
    name = PurePosixPath(path)
    issues: list[str] = []
    if name.name == ".env" or (
        name.name.startswith(".env.") and name.name not in {".env.example", ".env.template"}
    ):
        issues.append("environment file")
    if name.suffix.lower() in BLOCKED_SUFFIXES:
        issues.append("recording or model file")
    if path.startswith("data/") and path != "data/README.md":
        issues.append("local data directory")
    if len(content) > MAX_BYTES:
        issues.append("file larger than 5 MiB")
    if any(pattern.search(content) for pattern in TOKEN_PATTERNS):
        issues.append("possible credential or private key")
    return issues


def git_output(*args: str) -> bytes:
    result = subprocess.run(["git", *args], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("Git index could not be read. Run inside an initialized repository.")
    return result.stdout


def main() -> int:
    try:
        paths = git_output("ls-files", "-z").split(b"\0")
        failures: list[tuple[str, list[str]]] = []
        for raw_path in paths:
            if not raw_path:
                continue
            path = raw_path.decode("utf-8", errors="surrogateescape")
            size = int(git_output("cat-file", "-s", f":{path}"))
            if size > MAX_BYTES:
                failures.append((path, ["file larger than 5 MiB"]))
                continue
            # Read staged bytes, not a possibly different working-tree copy.
            issues = inspect_file(path, git_output("show", f":{path}"))
            if issues:
                failures.append((path, issues))
        for path, issues in failures:
            print(f"BLOCKED {path}: {', '.join(issues)}", file=sys.stderr)
        if failures:
            print(
                "Remove sensitive files from the index; do not bypass this check.", file=sys.stderr
            )
            return 1
        print("Repository hygiene checks passed (limited checks only).")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Repository hygiene check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
