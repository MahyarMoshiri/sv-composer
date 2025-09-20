"""SV Composer FastAPI application."""
from __future__ import annotations

import hashlib
from pathlib import Path

import structlog
from fastapi import FastAPI

from sv_sdk.loader import SCHEMA_PATH, load_schema_bank

from .routers import bible, compose, evaluate, health, lexicon

logger = structlog.get_logger(__name__)

app = FastAPI(title="SV Composer API", version="0.1.0")
app.include_router(health.router)
app.include_router(bible.router)
app.include_router(compose.router)
app.include_router(evaluate.router)
app.include_router(lexicon.router)


@app.on_event("startup")
async def log_schema_bank_metadata() -> None:
    bank = load_schema_bank()
    sha256 = hashlib.sha256(Path(SCHEMA_PATH).read_bytes()).hexdigest()
    logger.info(
        "bible.schema_bank.loaded",
        version=bank.version,
        schemas_count=len(bank.schemas),
        sha256=sha256,
    )
