"""SV Composer FastAPI application."""
from __future__ import annotations

import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sv_llm import default_llm_name
from sv_sdk import bible_versions
from sv_sdk.loader import (
    BLEND_RULES_PATH,
    FRAMES_PATH,
    METAPHORS_PATH,
    SCHEMA_PATH,
    file_sha256,
    load_bible_version,
    load_blend_rules,
    load_frame_bank,
    load_metaphor_bank,
    load_schema_bank,
)

from .rag import get_embedder_name, get_rag_index
from .routers import (
    bible,
    bible_blend,
    bible_frames,
    bible_metaphors,
    blend,
    compose,
    control,
    evaluate,
    expectation,
    framecheck,
    generate,
    gold,
    health,
    lexicon,
    retrieval,
    status,
)

structlog.configure(processors=[structlog.processors.JSONRenderer()])
logger = structlog.get_logger(__name__)
BIBLE_VERSION = load_bible_version()


def _log_schema_bank() -> None:
    bank = load_schema_bank()
    sha256 = hashlib.sha256(Path(SCHEMA_PATH).read_bytes()).hexdigest()
    logger.info(
        "bible.schema_bank.loaded",
        version=bank.version,
        schemas_count=len(bank.schemas),
        sha256=sha256,
        bible_version=BIBLE_VERSION,
    )


def _log_frame_bank() -> None:
    bank = load_frame_bank()
    sha256 = file_sha256(FRAMES_PATH)
    logger.info(
        "bible.frame_bank.loaded",
        version=bank.version,
        frames_count=len(bank.frames),
        sha256=sha256,
        bible_version=BIBLE_VERSION,
    )


def _log_blend_rules() -> None:
    rules = load_blend_rules()
    sha256 = file_sha256(BLEND_RULES_PATH)
    frame_sha = file_sha256(FRAMES_PATH)
    logger.info(
        "bible.blend_rules.loaded",
        version=rules.version,
        vital_relations=len(rules.vital_relations),
        operators=len(rules.operators),
        sha256=sha256,
        frames_sha=frame_sha,
        bible_version=BIBLE_VERSION,
    )


def _log_metaphor_bank() -> None:
    bank = load_metaphor_bank()
    sha256 = file_sha256(METAPHORS_PATH)
    logger.info(
        "bible.metaphor_bank.loaded",
        version=bank.version,
        metaphors_count=len(bank.metaphors),
        sha256=sha256,
        bible_version=BIBLE_VERSION,
    )


def _log_bible_versions() -> None:
    logger.info("bible.versions.snapshot", versions=bible_versions())


def _log_rag_index() -> None:
    index = get_rag_index()
    stats = index.stats()
    logger.info(
        "rag.index.initialized",
        embedder=get_embedder_name(),
        documents=len(index),
        per_kind=stats,
    )


def _log_llm_default() -> None:
    configured = os.getenv("SV_LLM_DEFAULT", "openai").strip() or "openai"
    offline = os.getenv("SV_OFFLINE", "").strip() == "1"
    provider = os.getenv("SV_LLM_IMPL", "").strip() or "builtin"
    has_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
    logger.info(
        "llm.default.configured",
        default=default_llm_name(),
        configured=configured,
        offline=offline,
        provider=provider,
        openai_key=has_key,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - framework glue
    _log_bible_versions()
    _log_schema_bank()
    _log_frame_bank()
    _log_blend_rules()
    _log_metaphor_bank()
    _log_rag_index()
    _log_llm_default()
    yield


app = FastAPI(title="SV Composer API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(bible.router)
app.include_router(bible_blend.router)
app.include_router(bible_frames.router)
app.include_router(bible_metaphors.router)
app.include_router(blend.router)
app.include_router(compose.router)
app.include_router(control.router)
app.include_router(expectation.router)
app.include_router(evaluate.router)
app.include_router(framecheck.router)
app.include_router(generate.router)
app.include_router(gold.router)
app.include_router(lexicon.router)
app.include_router(retrieval.router)
app.include_router(status.router)


def _cors_enabled() -> bool:
    toggle = os.getenv("SV_API_ENABLE_CORS", "").strip().lower()
    return toggle in {"1", "true", "yes", "on"}


if _cors_enabled():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
