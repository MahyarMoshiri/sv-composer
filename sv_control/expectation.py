def expectation_curve(step: int) -> float:
    # simple rising curve [0..1]
    return min(1.0, step / 5.0)

def should_explode(step: int, threshold: float = 0.8) -> bool:
    return expectation_curve(step) >= threshold
