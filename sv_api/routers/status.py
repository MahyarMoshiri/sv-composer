"""Status endpoint exposing runtime metadata."""
from __future__ import annotations

import platform
import sys
import time

from fastapi import APIRouter

from sv_llm import default_llm_name
from sv_sdk import __version__ as sdk_version
from sv_sdk.versioning import bible_versions

_started = time.time()
router = APIRouter()


@router.get("/status")
def status() -> dict[str, object]:
    """Return process health and build metadata."""

    uptime = round(time.time() - _started, 2)
    return {
        "ok": True,
        "data": {
            "sdk_version": sdk_version,
            "bible_versions": bible_versions(),
            "embedder": "hash",
            "llm_default": default_llm_name(),
            "uptime_sec": uptime,
            "build": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "fastapi": "installed",
            },
        },
        "warnings": [],
        "errors": [],
    }
