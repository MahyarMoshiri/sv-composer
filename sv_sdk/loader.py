import yaml
from pathlib import Path
from .models import Bible, Schema, Frame, Metaphor

BIBLE_DIR = Path(__file__).resolve().parents[1] / "bible"

def load_yaml(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_bible() -> Bible:
    schemas = load_yaml(BIBLE_DIR / "schemas.yml").get("schemas", [])
    frames = load_yaml(BIBLE_DIR / "frames.yml").get("frames", [])
    metaphors = load_yaml(BIBLE_DIR / "metaphors.yml").get("metaphors", [])
    version = (BIBLE_DIR / "VERSION").read_text(encoding="utf-8").strip()
    return Bible(
        schemas=[Schema(**s) for s in schemas],
        frames=[Frame(**f) for f in frames],
        metaphors=[Metaphor(**m) for m in metaphors],
        version=version,
    )
