"""Helpers for loading the schema bank from YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .models import SchemaBank

BIBLE_DIR = Path(__file__).resolve().parents[1] / "bible"
SCHEMA_PATH = BIBLE_DIR / "schemas.yml"


def load_yaml(path: Path | str) -> Dict[str, Any]:
    """Load a YAML file as a dictionary."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {p}, got {type(data)!r}")
    return data


def load_schema_bank() -> SchemaBank:
    """Load the schema bank from the canonical YAML file."""
    raw = load_yaml(SCHEMA_PATH)
    return SchemaBank(**raw)
