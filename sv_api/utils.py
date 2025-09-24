"""Common API response helpers."""
from __future__ import annotations

from typing import Any, Dict, List


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope with payload."""

    return {"ok": True, "data": data, "warnings": [], "errors": []}


def err(messages: List[str]) -> Dict[str, Any]:
    """Return an error envelope with message list."""

    return {"ok": False, "data": None, "warnings": [], "errors": messages}
