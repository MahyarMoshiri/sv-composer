"""Rule-based narrator viewpoint heuristics."""
from __future__ import annotations

from functools import lru_cache
import re
from pathlib import Path
from typing import Any, Dict, Literal

import yaml
from pydantic import BaseModel

ViewPerson = Literal["1st", "2nd", "3rd"]
ViewTense = Literal["past", "present"]
ViewDistance = Literal["close", "medium", "far"]


class ViewHint(BaseModel):
    person: ViewPerson = "3rd"
    tense: ViewTense = "present"
    distance: ViewDistance = "medium"


TOKEN_PATTERN = re.compile(r"[a-zA-Z']+|[\u0600-\u06FF]+")
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "viewpoint_rules.yml"

DEFAULT_RULES: Dict[str, Any] = {
    "person": {
        "en": {
            "first": ["i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"],
            "second": ["you", "your", "yours", "yourself", "yourselves", "thou"],
            "imperatives": [
                "go",
                "walk",
                "run",
                "climb",
                "cross",
                "hold",
                "look",
                "listen",
                "remember",
                "consider",
                "picture",
                "imagine",
                "take",
                "bring",
                "enter",
                "step",
                "descend",
                "follow",
            ],
        },
        "fa": {
            "first": ["\u0645\u0646", "\u0645\u0646\u0645", "\u0645\u0627", "\u0645\u0627\u0646"],
            "second": ["\u062a\u0648", "\u0634\u0645\u0627", "\u062a\u0627", "\u062a\u0648\u0646"],
            "imperatives": ["\u0628\u0631\u0648", "\u0628\u06af\u06cc\u0631", "\u0628\u06cc\u0627", "\u062d\u0631\u06a9\u062a\u200c\u06a9\u0646"],
        },
    },
    "tense": {
        "en": {
            "past_verbs": [
                "was",
                "were",
                "had",
                "did",
                "went",
                "came",
                "crossed",
                "walked",
                "saw",
                "felt",
                "stood",
                "took",
                "left",
                "arrived",
                "gathered",
                "opened",
                "closed",
            ],
            "past_adverbs": ["yesterday", "ago", "earlier", "previously", "once", "before"],
            "time_nouns": ["night", "day", "week", "month", "year", "winter", "summer"],
            "last_tokens": ["last"],
            "past_suffixes": ["ed"],
            "contains": [],
        },
        "fa": {
            "past_verbs": ["\u06a9\u0631\u062f", "\u0628\u0648\u062f", "\u0634\u062f", "\u0631\u0641\u062a", "\u0622\u0645\u062f"],
            "past_adverbs": ["\u062f\u06cc\u0631\u0648\u0632", "\u0642\u0628\u0644\u0627"],
            "time_nouns": [],
            "last_tokens": [],
            "past_suffixes": ["\u062f"],
            "contains": ["\u06af\u0630\u0634\u062a"],
        },
    },
    "distance": {
        "en": {
            "close": [
                "inside",
                "within",
                "room",
                "chamber",
                "corridor",
                "tunnel",
                "threshold",
                "door",
                "bridge",
                "hands",
                "hand",
                "skin",
                "breath",
                "pocket",
                "embrace",
                "near",
            ],
            "far": [
                "horizon",
                "mountain",
                "mountains",
                "landscape",
                "distant",
                "distance",
                "sky",
                "clouds",
                "valley",
                "field",
                "fields",
                "plain",
                "plains",
                "desert",
                "sea",
                "ocean",
                "vista",
                "expanse",
            ],
        },
        "fa": {
            "close": ["\u062f\u0631\u0648\u0646", "\u0627\u062a\u0627\u0642", "\u062f\u0633\u062a", "\u062f\u0633\u062a\u0645", "\u067e\u0648\u0633\u062a", "\u0646\u0641\u0633", "\u0622\u063a\u0648\u0634"],
            "far": ["\u0627\u0641\u0642", "\u06a9\u0648\u0647", "\u062f\u0634\u062a", "\u062f\u0631\u06cc\u0627", "\u0622\u0633\u0645\u0627\u0646", "\u0641\u0627\u0635\u0644\u0647"],
        },
    },
    "fallback": {
        "defaults": {"person": "3rd", "tense": "present", "distance": "medium"},
        "frames": {
            "journey": {"person": "3rd", "tense": "present", "distance": "far"}
        },
    },
}


def infer_viewpoint(prompt: str, frame_id: str | None = None, lang: str = "en") -> ViewHint:
    lang_code = _normalise_lang(lang)
    tokens = _tokenize(prompt)
    text_lower = prompt.lower()

    detected_person = _infer_person(tokens, lang_code)
    detected_tense = _infer_tense(tokens, text_lower, lang_code)
    detected_distance = _infer_distance(tokens, lang_code)

    config_frame_defaults = _config_frame_defaults().get(frame_id or "", {})
    frame_defaults = _frame_defaults().get(frame_id or "", {})
    config_defaults = _config_defaults()

    person = (
        detected_person
        or config_frame_defaults.get("person")
        or frame_defaults.get("person")
        or config_defaults.get("person", "3rd")
    )
    tense = (
        detected_tense
        or config_frame_defaults.get("tense")
        or frame_defaults.get("tense")
        or config_defaults.get("tense", "present")
    )
    distance = (
        detected_distance
        or config_frame_defaults.get("distance")
        or frame_defaults.get("distance")
        or config_defaults.get("distance", "medium")
    )

    return ViewHint(person=person, tense=tense, distance=distance)


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _normalise_lang(lang: str | None) -> str:
    return (lang or "en").lower()


def _infer_person(tokens: list[str], lang: str) -> ViewPerson | None:
    rules = _lang_rules("person", lang)
    first = set(rules.get("first", []))
    second = set(rules.get("second", []))
    imperatives = set(rules.get("imperatives", []))

    token_set = set(tokens)
    if token_set & first:
        return "1st"
    if token_set & second:
        return "2nd"
    if tokens and tokens[0] in imperatives:
        return "2nd"
    return None


def _infer_tense(tokens: list[str], text_lower: str, lang: str) -> ViewTense | None:
    rules = _lang_rules("tense", lang)
    token_set = set(tokens)

    past_verbs = set(rules.get("past_verbs", []))
    if token_set & past_verbs:
        return "past"

    past_adverbs = set(rules.get("past_adverbs", []))
    if token_set & past_adverbs:
        return "past"

    for suffix in rules.get("past_suffixes", []):
        if suffix and any(len(token) > len(suffix) and token.endswith(suffix) for token in tokens):
            return "past"

    time_nouns = set(rules.get("time_nouns", []))
    last_tokens = set(rules.get("last_tokens", []))
    if time_nouns and last_tokens:
        for idx, token in enumerate(tokens[:-1]):
            if token in last_tokens and tokens[idx + 1] in time_nouns:
                return "past"

    for marker in rules.get("contains", []):
        if marker and marker in text_lower:
            return "past"

    return None


def _infer_distance(tokens: list[str], lang: str) -> ViewDistance | None:
    rules = _lang_rules("distance", lang)
    close_cues = set(rules.get("close", []))
    far_cues = set(rules.get("far", []))

    close_hits = sum(1 for token in tokens if token in close_cues)
    far_hits = sum(1 for token in tokens if token in far_cues)

    if close_hits and close_hits >= far_hits:
        return "close"
    if far_hits:
        return "far"
    return None


@lru_cache(maxsize=1)
def _frame_defaults() -> Dict[str, Dict[str, str]]:
    path = Path(__file__).resolve().parents[1] / "bible" / "frames.yml"
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}

    frames = data.get("frames")
    if not isinstance(frames, list):
        return {}

    defaults: Dict[str, Dict[str, str]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        frame_id = frame.get("id")
        vp_defaults = frame.get("viewpoint_defaults")
        if not frame_id or not isinstance(vp_defaults, dict):
            continue

        clean_defaults = {}
        for key in ("person", "tense", "distance"):
            value = vp_defaults.get(key)
            if isinstance(value, str):
                clean_defaults[key] = value
        if clean_defaults:
            defaults[str(frame_id)] = clean_defaults

    return defaults


@lru_cache(maxsize=1)
def _viewpoint_rules() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict):
                return raw
        except yaml.YAMLError:
            pass
    return DEFAULT_RULES


def _lang_rules(section: str, lang: str) -> Dict[str, list[str]]:
    rules = _viewpoint_rules().get(section, {})
    if not isinstance(rules, dict):
        return {}
    lang_rules = rules.get(lang, {})
    if not isinstance(lang_rules, dict):
        return {}

    cleaned: Dict[str, list[str]] = {}
    for key, values in lang_rules.items():
        if isinstance(values, list):
            cleaned[key] = [str(item).lower() for item in values if isinstance(item, str)]
        else:
            cleaned[key] = []
    return cleaned


def _config_defaults() -> Dict[str, str]:
    fallback = _viewpoint_rules().get("fallback", {})
    if not isinstance(fallback, dict):
        return {}
    defaults = fallback.get("defaults", {})
    if not isinstance(defaults, dict):
        return {}
    return {str(key): str(value) for key, value in defaults.items() if isinstance(value, str)}


def _config_frame_defaults() -> Dict[str, Dict[str, str]]:
    fallback = _viewpoint_rules().get("fallback", {})
    if not isinstance(fallback, dict):
        return {}
    frames = fallback.get("frames", {})
    if not isinstance(frames, dict):
        return {}

    cleaned: Dict[str, Dict[str, str]] = {}
    for frame_id, values in frames.items():
        if not isinstance(values, dict):
            continue
        cleaned[str(frame_id)] = {
            str(key): str(value)
            for key, value in values.items()
            if isinstance(value, str) and key in {"person", "tense", "distance"}
        }
    return cleaned
