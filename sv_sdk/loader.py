"""Helpers for loading the schema bank from YAML."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .models import BeatsConfig, BlendRules, FrameBank, MetaphorBank, SchemaBank

BIBLE_DIR = Path(__file__).resolve().parents[1] / "bible"
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
SCHEMA_PATH = BIBLE_DIR / "schemas.yml"
METAPHORS_PATH = BIBLE_DIR / "metaphors.yml"
FRAMES_PATH = BIBLE_DIR / "frames.yml"
BLEND_RULES_PATH = BIBLE_DIR / "blend_rules.yml"
NORMALIZED_NAME = "schemas.normalized.yml"
BIBLE_VERSION_PATH = BIBLE_DIR / "VERSION"
BEATS_CONFIG_PATH = CONFIG_DIR / "beats.yml"


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


def load_metaphor_bank() -> MetaphorBank:
    """Load the metaphor bank from the canonical YAML file."""

    raw = load_yaml(METAPHORS_PATH)
    return MetaphorBank(**raw)


def load_frame_bank() -> FrameBank:
    """Load the frame bank from the canonical YAML file."""

    raw = load_yaml(FRAMES_PATH)
    return FrameBank(**raw)


def load_blend_rules() -> BlendRules:
    """Load the blending rulebook from the canonical YAML file."""

    raw = load_yaml(BLEND_RULES_PATH)
    return BlendRules(**raw)


def load_beats_config() -> BeatsConfig:
    """Load the beats configuration from config/beats.yml."""

    raw = load_yaml(BEATS_CONFIG_PATH)
    return BeatsConfig(**raw)


def normalized_path() -> Path:
    """Return the expected path for the normalized schema file."""

    return BIBLE_DIR / NORMALIZED_NAME


def file_sha256(path: Path) -> str:
    """Compute a SHA-256 digest for the supplied file path."""

    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_schema_bank_normalized_if_exists() -> Optional[SchemaBank]:
    """Load the normalized schema bank when available."""

    path = normalized_path()
    if not path.exists():
        return None
    raw = load_yaml(path)
    return SchemaBank(**raw)


def load_bible_version() -> str:
    """Return the curated bible version string."""

    if not BIBLE_VERSION_PATH.exists():
        return "unknown"
    return BIBLE_VERSION_PATH.read_text(encoding="utf-8").strip()


def normalize_in_memory(bank: SchemaBank) -> SchemaBank:
    """Return a sanitized copy of the provided schema bank."""

    raw = bank.model_dump(mode="python", by_alias=True)

    for schema in raw.get("schemas", []):
        roles = schema.get("roles") or []
        if isinstance(roles, list):
            unique_roles = list(dict.fromkeys(roles))
            schema["roles"] = sorted(unique_roles)

        params = schema.get("params") or {}
        if isinstance(params, dict):
            schema["params"] = {key: params[key] for key in sorted(params.keys())}

        lexicon = schema.get("lexicon") or {}
        if isinstance(lexicon, dict):
            for lang in ("en", "fa"):
                entries = lexicon.get(lang)
                if isinstance(entries, list):
                    cleaned = []
                    for entry in entries:
                        item = dict(entry)
                        weight = float(item.get("w", 0.0))
                        item["w"] = max(0.0, min(1.0, weight))
                        cleaned.append(item)
                    lexicon[lang] = sorted(cleaned, key=lambda item: item["w"], reverse=True)

    return SchemaBank(**raw)
