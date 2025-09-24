from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Iterator

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def normalized_schemas_file() -> Iterator[Path]:
    """Provide a normalized schema file for tests and clean up afterwards."""

    normalized_path = REPO_ROOT / "bible" / "schemas.normalized.yml"
    fixture_path = REPO_ROOT / "tests" / "fixtures" / "schemas_min.yml"

    backup: bytes | None = None
    if normalized_path.exists():
        backup = normalized_path.read_bytes()
    shutil.copy(fixture_path, normalized_path)

    try:
        yield normalized_path
    finally:
        if backup is not None:
            normalized_path.write_bytes(backup)
        elif normalized_path.exists():
            normalized_path.unlink()


@pytest.fixture
def remove_normalized_schemas() -> Iterator[None]:
    """Ensure the normalized schemas file is absent during a test."""

    normalized_path = REPO_ROOT / "bible" / "schemas.normalized.yml"

    backup: bytes | None = None
    if normalized_path.exists():
        backup = normalized_path.read_bytes()
        normalized_path.unlink()

    try:
        yield
    finally:
        if backup is not None:
            normalized_path.write_bytes(backup)
