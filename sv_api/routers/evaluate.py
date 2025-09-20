from fastapi import APIRouter
from pydantic import BaseModel
from sv_eval.metrics import simple_scores
from sv_eval.scorecard import scorecard

router = APIRouter()

class EvalIn(BaseModel):
    text: str

@router.post("/evaluate")
def evaluate(inp: EvalIn):
    scores = simple_scores(inp.text)
    sc = scorecard(scores)
    return sc
