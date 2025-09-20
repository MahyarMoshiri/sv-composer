from sv_sdk.loader import load_bible
from sv_sdk.validators import validate_bible

def test_bible_valid():
    b = load_bible()
    validate_bible(b)
    assert b.version
