from fastapi import APIRouter
from pathlib import Path

router = APIRouter()

@router.get("/health")
def health():
    version = (Path("bible") / "VERSION").read_text(encoding="utf-8").strip()
    return {"status": "ok", "version": version}
