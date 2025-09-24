"""Routes exposing the schema bible."""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from sv_api.utils import err, ok
from sv_sdk.loader import (
    load_schema_bank,
    load_schema_bank_normalized_if_exists,
    normalized_path,
)
from sv_sdk.models import SchemaBank, SchemaItem
from sv_sdk.validators import validate_schema_bank

router = APIRouter()


def _schema_summary(bank: SchemaBank) -> Dict[str, int | str]:
    schemas = bank.schemas
    return {
        "version": bank.version,
        "schemas_count": len(schemas),
        "en_lexemes": sum(len(schema.lexicon.en) for schema in schemas),
        "fa_lexemes": sum(len(schema.lexicon.fa) for schema in schemas),
    }


def _load_schema_bank(source: str) -> Optional[SchemaBank]:
    if source == "normalized":
        return load_schema_bank_normalized_if_exists()
    return load_schema_bank()


def _validate_bank(bank: SchemaBank) -> Optional[JSONResponse]:
    try:
        validate_schema_bank(bank)
    except Exception as exc:  # noqa: BLE001 - surfacing validation errors
        return JSONResponse(status_code=422, content=err([str(exc)]))
    return None


@router.get("/bible/schemas")
def get_schemas(
    id: Optional[str] = Query(default=None),
    validate: bool = Query(default=False),
    source: str = Query(default="current", pattern="^(current|normalized)$"),
):
    bank = _load_schema_bank(source)

    if bank is None:
        message = f"normalized schema file not found at {normalized_path()}"
        return JSONResponse(status_code=422, content=err([message]))

    if validate:
        error_response = _validate_bank(bank)
        if error_response is not None:
            return error_response

    schemas: list[SchemaItem] = list(bank.schemas)
    if id is not None:
        schemas = [schema for schema in schemas if schema.id == id]

    payload = {
        "summary": _schema_summary(bank),
        "schemas": [schema.model_dump(by_alias=True) for schema in schemas],
    }
    return ok(payload)


@router.get("/bible/schemas/compat")
def get_schema_compatibility(
    validate: bool = Query(default=False),
    source: str = Query(default="current", pattern="^(current|normalized)$"),
):
    bank = _load_schema_bank(source)

    if bank is None:
        message = f"normalized schema file not found at {normalized_path()}"
        return JSONResponse(status_code=422, content=err([message]))

    if validate:
        error_response = _validate_bank(bank)
        if error_response is not None:
            return error_response

    compat = {schema.id: list(schema.coactivate) for schema in bank.schemas}
    payload = {"summary": _schema_summary(bank), "compat": compat}
    return ok(payload)
