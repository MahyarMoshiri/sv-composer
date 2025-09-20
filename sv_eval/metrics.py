from typing import Dict

def simple_scores(text: str) -> Dict[str, float]:
    # toy metrics: presence of keywords
    frame_fit = 1.0 if "bridge" in text.lower() else 0.6
    schema_cov = 0.7
    explosion_timing = 0.8
    return {"frame_fit": frame_fit, "schema_cov": schema_cov, "explosion_timing": explosion_timing}
