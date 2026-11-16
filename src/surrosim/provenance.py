"""Shared provenance helpers: git revision, content hashes, tool versions."""

from pathlib import Path
import hashlib
import platform
import subprocess
from importlib import metadata


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_info() -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True,
                check=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def tool_versions() -> dict:
    versions = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        versions["surrosim"] = metadata.version("surrosim")
    except metadata.PackageNotFoundError:
        versions["surrosim"] = "unknown"
    return versions
