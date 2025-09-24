"""Utilities for reporting curated bible component versions."""
from __future__ import annotations

from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "schemas": "bible/schemas.yml",
    "metaphors": "bible/metaphors.yml",
    "frames": "bible/frames.yml",
    "blends": "bible/blend_rules.yml",
    "beats": "config/beats.yml",
    "thresholds": "config/thresholds.yml",
    "gold": "data/gold/labels.jsonl",
}


def _sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _version_from_yaml(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version:"):
                return line.split(":", 1)[1].strip().strip('\"\'')
    except Exception:  # noqa: BLE001 - defensive guard against partial files
        return None
    return None


def bible_versions() -> dict[str, dict[str, object]]:
    """Return metadata for curated bible artifacts."""

    out: dict[str, dict[str, object]] = {}
    for key, relative_path in FILES.items():
        path = (ROOT / relative_path).resolve()
        if path.exists():
            out[key] = {
                "version": _version_from_yaml(path),
                "sha256": _sha(path)[:12],
                "path": str(path),
            }
        else:
            out[key] = {"missing": True, "path": str(path)}
    return out
