from pydantic import BaseModel
from typing import Literal

class ViewHint(BaseModel):
    person: Literal["1st", "2nd", "3rd"] = "3rd"
    tense: Literal["past", "present"] = "present"
    distance: Literal["close", "far"] = "close"
    attention_center: str | None = None

def infer_viewpoint(prompt: str) -> ViewHint:
    # trivial heuristic (stub): night/close; day/far
    return ViewHint(
        person="3rd",
        tense="present",
        distance="close" if "night" in prompt.lower() else "far",
        attention_center=None,
    )
