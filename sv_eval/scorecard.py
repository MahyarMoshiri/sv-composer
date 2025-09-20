from typing import Dict

def scorecard(scores: Dict[str, float]) -> Dict[str, object]:
    passed = scores["frame_fit"] >= 0.6
    return {"scores": scores, "pass": passed}
