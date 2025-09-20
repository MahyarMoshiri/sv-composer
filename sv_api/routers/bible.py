from fastapi import APIRouter, HTTPException
from sv_sdk.loader import load_bible

router = APIRouter()

@router.get("/bible/{section}")
def get_bible_section(section: str):
    b = load_bible()
    if section == "schemas":
        return {"schemas": [s.model_dump() for s in b.schemas], "version": b.version}
    if section == "frames":
        return {"frames": [f.model_dump() for f in b.frames], "version": b.version}
    if section == "metaphors":
        return {"metaphors": [m.model_dump() for m in b.metaphors], "version": b.version}
    raise HTTPException(status_code=404, detail="section not found")
