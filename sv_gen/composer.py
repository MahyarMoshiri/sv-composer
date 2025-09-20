from typing import Tuple
from sv_control.viewpoint import infer_viewpoint
from sv_control.expectation import expectation_curve, should_explode
from .llm_provider import generate_text
from .trace import Trace

def compose(prompt: str, length: str = "short") -> Tuple[str, Trace]:
    vp = infer_viewpoint(prompt)
    steps, curve = [], []
    text = ""
    for i in range(1, 6):
        curve.append(expectation_curve(i))
        steps.append({"i": i, "vp": vp.model_dump()})
        if should_explode(i):
            break
    text = generate_text(prompt, provider="local")
    return text, Trace(steps=steps, expectation=curve)
