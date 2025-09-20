"""Command line helpers for schema bank maintenance."""
from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Dict

import typer

from .loader import load_schema_bank
from .validators import validate_schema_bank

app = typer.Typer(help="SV SDK utilities")
schemas_app = typer.Typer(help="Schema bank commands")
app.add_typer(schemas_app, name="schemas")


@schemas_app.command("validate")
def schemas_validate() -> None:
    """Validate the schema bank and report the result."""

    try:
        bank = load_schema_bank()
        validate_schema_bank(bank)
    except Exception as exc:  # noqa: BLE001 - broad to surface validation issues
        typer.echo("Schema bank validation failed:")
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    typer.echo("Schema bank OK")


@schemas_app.command("stats")
def schemas_stats() -> None:
    """Print descriptive statistics about the schema bank."""

    bank = load_schema_bank()
    lexeme_counts: Counter[str] = Counter()
    valences = []
    arousals = []
    edges = 0

    for schema in bank.schemas:
        lexicon_data: Dict[str, list] = schema.lexicon.model_dump()
        for lang, lexemes in lexicon_data.items():
            if isinstance(lexemes, list):
                lexeme_counts[lang] += len(lexemes)
        valences.append(schema.affect.valence)
        arousals.append(schema.affect.arousal)
        edges += len(schema.coactivate)

    typer.echo(f"schemas: {len(bank.schemas)}")
    for lang, count in sorted(lexeme_counts.items()):
        typer.echo(f"lexemes[{lang}]: {count}")
    typer.echo(f"avg valence: {mean(valences) if valences else 0:.3f}")
    typer.echo(f"avg arousal: {mean(arousals) if arousals else 0:.3f}")
    typer.echo(f"coactivation edges: {edges}")
