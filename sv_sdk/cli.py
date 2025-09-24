"""Command line helpers for schema bank maintenance."""
from __future__ import annotations

import json
from collections import Counter
from statistics import mean
from pathlib import Path
from typing import Dict

import typer

import structlog

from .gold_loader import DEFAULT_GOLD_PATH, load_gold_jsonl
from .gold_stats import compute_gold_stats
from .loader import (
    file_sha256,
    load_beats_config,
    load_bible_version,
    load_frame_bank,
    load_metaphor_bank,
    load_schema_bank,
)
from .validators import validate_gold, validate_schema_bank
from sv_compose.controller import get_thresholds_config
from sv_eval.evaluator import evaluate as run_evaluator

app = typer.Typer(help="SV SDK utilities")
schemas_app = typer.Typer(help="Schema bank commands")
gold_app = typer.Typer(help="Gold corpus commands")
app.add_typer(schemas_app, name="schemas")
app.add_typer(gold_app, name="gold")

logger = structlog.get_logger(__name__)


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


@gold_app.command("validate")
def gold_validate(
    path: Path = typer.Option(DEFAULT_GOLD_PATH, "--path", help="Path to labels.jsonl"),
) -> None:
    """Validate the gold-labelled corpus and report findings."""

    try:
        gold = load_gold_jsonl(path)
        schemas = load_schema_bank()
        metaphors = load_metaphor_bank()
        frames = load_frame_bank()
        beats = load_beats_config()
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI
        typer.echo("Failed to load gold corpus dependencies:")
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    bible_version = load_bible_version()
    sha256 = file_sha256(path)

    logger.info(
        "gold.validation.start",
        **{"bible.version": bible_version},
        path=str(path),
        sha256=sha256,
        total=len(gold),
    )

    try:
        errors, warnings = validate_gold(
            gold,
            schemas,
            metaphors,
            frames,
            beats,
            errors_as="list",
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI
        typer.echo("Gold corpus validation raised an error:")
        typer.echo(str(exc))
        logger.info(
            "gold.validation.error",
            **{"bible.version": bible_version},
            path=str(path),
            sha256=sha256,
        )
        raise typer.Exit(code=1) from exc

    typer.echo(f"items: {len(gold)}")
    typer.echo(f"warnings: {len(warnings)}")
    typer.echo(f"errors: {len(errors)}")

    if warnings:
        typer.echo("-- warnings --")
        for warning in warnings:
            typer.echo(f"- {warning}")

    if errors:
        typer.echo("-- errors --")
        for error in errors:
            typer.echo(f"- {error}")
        logger.info(
            "gold.validation.failed",
            **{"bible.version": bible_version},
            path=str(path),
            sha256=sha256,
            errors=len(errors),
            warnings=len(warnings),
        )
        raise typer.Exit(code=1)

    logger.info(
        "gold.validation.ok",
        **{"bible.version": bible_version},
        path=str(path),
        sha256=sha256,
        warnings=len(warnings),
    )
    typer.echo("Gold corpus OK")


@gold_app.command("stats")
def gold_stats(
    path: Path = typer.Option(DEFAULT_GOLD_PATH, "--path", help="Path to labels.jsonl"),
) -> None:
    """Print descriptive statistics for the gold corpus."""

    try:
        gold = load_gold_jsonl(path)
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI
        typer.echo("Failed to load gold corpus:")
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    stats = compute_gold_stats(gold)

    typer.echo(f"items: {stats['count']}")

    typer.echo("lang totals:")
    for lang, count in stats["by_lang"].items():
        typer.echo(f"  {lang}: {count}")

    typer.echo("frame totals:")
    for frame, count in stats["by_frame"].items():
        typer.echo(f"  {frame}: {count}")

    typer.echo("schema totals:")
    for schema, count in stats["by_schema"].items():
        typer.echo(f"  {schema}: {count}")

    typer.echo("metaphor totals:")
    for metaphor, count in stats["by_metaphor"].items():
        typer.echo(f"  {metaphor}: {count}")

    typer.echo("explosion beats:")
    for beat, count in stats["explosion_beats"].items():
        typer.echo(f"  {beat}: {count}")

    attention = stats["attention"]
    typer.echo(
        f"avg attention weight: {attention['avg_weight']:.3f} over {attention['count']} spans"
    )

    pole_info = stats["metaphor_poles"]
    typer.echo(
        "percent with explicit pole: "
        f"{pole_info['percent_with_pole']:.1f}% ({pole_info['with_pole']}/{pole_info['total']})"
    )


@app.command("evaluate")
def evaluate_piece(
    piece: Path = typer.Argument(..., help="Path to the composed piece text"),
    trace: Path = typer.Option(..., "--trace", "-t", help="Path to compose trace JSON"),
) -> None:
    """Run the deterministic evaluator on a composed piece."""

    try:
        piece_text = piece.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI
        typer.echo(f"Failed to read piece: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        trace_payload = json.loads(trace.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI
        typer.echo(f"Failed to read trace: {exc}")
        raise typer.Exit(code=1) from exc

    thresholds = get_thresholds_config()
    banks = {
        "schemas": load_schema_bank(),
        "metaphors": load_metaphor_bank(),
        "frames": load_frame_bank(),
    }

    try:
        result = run_evaluator(piece_text, trace_payload, thresholds, banks)
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI
        typer.echo(f"Evaluation failed: {exc}")
        raise typer.Exit(code=1) from exc

    status = "PASS" if result.get("pass") else "FAIL"
    typer.echo(
        f"{status} score_final={result.get('score_final', 0.0):.3f} "
        f"(pre={result.get('score_pre_penalty', 0.0):.3f} "
        f"penalty={result.get('total_penalty', 0.0):.3f})"
    )

    metrics = result.get("metrics", {})
    ordered_keys = ["frame_fit", "schema_cov", "metaphor_diversity", "attention_discipline", "explosion_timing"]
    summary = ", ".join(
        f"{key}={metrics.get(key, 0.0):.2f}" for key in ordered_keys if key in metrics
    )
    if summary:
        typer.echo(f"metrics: {summary}")

    penalties = result.get("penalties_applied", [])
    if penalties:
        penalty_summary = ", ".join(
            f"{entry['code']}(-{entry['value']:.2f})" for entry in penalties if "code" in entry
        )
        if penalty_summary:
            typer.echo(f"penalties: {penalty_summary}")

    criticals = result.get("critical_violations", [])
    if criticals:
        typer.echo(f"critical: {', '.join(criticals)}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()
