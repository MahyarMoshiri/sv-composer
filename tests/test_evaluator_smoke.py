from sv_eval.metrics import simple_scores
from sv_eval.scorecard import scorecard

def test_eval():
    sc = scorecard(simple_scores("bridge at night"))
    assert "scores" in sc and "pass" in sc
