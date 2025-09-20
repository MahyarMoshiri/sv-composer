from .models import Bible

def validate_bible(b: Bible) -> None:
    schema_ids = {s.id for s in b.schemas}
    metaphor_ids = {m.id for m in b.metaphors}
    for fr in b.frames:
        missing_s = [s for s in fr.allowed_schemas if s not in schema_ids]
        missing_m = [m for m in fr.allowed_metaphors if m not in metaphor_ids]
        if missing_s or missing_m:
            raise ValueError(f"Frame '{fr.id}' invalid. missing_schemas={missing_s} missing_metaphors={missing_m}")
