from pydantic import BaseModel
from typing import List, Dict, Any

class Trace(BaseModel):
    steps: List[Dict[str, Any]]
    expectation: List[float]
