"""Routes exposing the schema bible."""
from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query

from sv_sdk.loader import load_schema_bank
from sv_sdk.models import SchemaBank, SchemaItem

router = APIRouter()


def _schema_summary(bank: SchemaBank) -> Dict[str, int | str]:
    schemas = bank.schemas
    return {
        "version": bank.version,
        "schemas_count": len(schemas),
        "en_lexemes": sum(len(schema.lexicon.en) for schema in schemas),
        "fa_lexemes": sum(len(schema.lexicon.fa) for schema in schemas),
    }


@router.get("/bible/schemas")
def get_schemas(id: str | None = Query(default=None)) -> Dict[str, object]:
    bank = load_schema_bank()
    schemas: List[SchemaItem] = list(bank.schemas)
    if id is not None:
        filtered = [schema for schema in schemas if schema.id == id]
        if not filtered:
            raise HTTPException(status_code=404, detail="schema not found")
        schemas = filtered
    return {
        "summary": _schema_summary(bank),
        "schemas": [schema.model_dump(by_alias=True) for schema in schemas],
    }


@router.get("/bible/schemas/compat")
def get_schema_compatibility() -> Dict[str, Dict[str, List[str]]]:
    bank = load_schema_bank()
    compat = {schema.id: list(schema.coactivate) for schema in bank.schemas}
    return {"compat": compat}
