from fastapi import APIRouter
from pydantic import BaseModel
from sv_gen.composer import compose

router = APIRouter()

class ComposeIn(BaseModel):
    prompt: str
    length: str = "short"

@router.post("/compose")
def compose_endpoint(inp: ComposeIn):
    text, trace = compose(inp.prompt, inp.length)
    return {"text": text, "trace": trace.model_dump()}
