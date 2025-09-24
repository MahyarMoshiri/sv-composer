"""Minimal template renderer supporting subset of Handlebars syntax."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable


EACH_PATTERN = re.compile(r"{{#each\s+([^\s{}]+)\s*}}")
END_EACH = "{{/each}}"
VAR_PATTERN = re.compile(r"{{\s*([^{#/][^{}]*)\s*}}")


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _resolve_path(context: Dict[str, Any], path: str) -> Any:
    if path.endswith(".*"):
        path = path[:-2]
    parts = path.split(".") if path else []
    value: Any = context
    for index, part in enumerate(parts):
        if part == "this":
            value = context.get("this")
            continue
        if isinstance(value, dict):
            if part in value:
                value = value[part]
                continue
        if isinstance(value, (list, tuple)) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(value):
                value = value[idx]
                continue
            return None
        if hasattr(value, part):
            value = getattr(value, part)
            continue
        return None
    return value


def _render_variables(segment: str, context: Dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        resolved = _resolve_path(context, path)
        return _format_value(resolved)

    return VAR_PATTERN.sub(replace, segment)


def _find_matching_each(template: str, start: int) -> tuple[int, int]:
    depth = 1
    cursor = start
    while cursor < len(template):
        next_open = EACH_PATTERN.search(template, cursor)
        next_close = template.find(END_EACH, cursor)
        if next_close == -1:
            break
        if next_open and next_open.start() < next_close:
            depth += 1
            cursor = next_open.end()
            continue
        depth -= 1
        close_pos = next_close
        cursor = close_pos + len(END_EACH)
        if depth == 0:
            return close_pos, cursor
    raise ValueError("Unmatched {{#each}} block in template")


def _render(template: str, context: Dict[str, Any]) -> str:
    output: list[str] = []
    cursor = 0
    while cursor < len(template):
        match = EACH_PATTERN.search(template, cursor)
        if not match:
            output.append(_render_variables(template[cursor:], context))
            break
        start, end_tag = match.span()
        output.append(_render_variables(template[cursor:start], context))
        path = match.group(1).strip()
        block_start = match.end()
        block_end, block_close = _find_matching_each(template, match.end())
        block_content = template[block_start:block_end]
        iterable = _resolve_path(context, path)
        rendered_block = []
        if isinstance(iterable, Iterable) and not isinstance(iterable, (str, bytes)):
            for item in iterable:
                scoped = dict(context)
                scoped["this"] = item
                rendered_block.append(_render(block_content, scoped))
        output.append("".join(rendered_block))
        cursor = block_close
    return "".join(output)


def render_template(path: str | Path, context: Dict[str, Any]) -> str:
    template_path = Path(path)
    if not template_path.exists():
        raise FileNotFoundError(template_path)
    template = template_path.read_text(encoding="utf-8")
    # Shallow copy to avoid mutating caller context when we inject `this`.
    safe_context = dict(context)
    rendered = _render(template, safe_context)
    lines = []
    for line in rendered.splitlines():
        if line.strip().startswith("### Output Contract"):
            continue
        lines.append(line)
    return "\n".join(lines)
