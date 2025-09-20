from sv_sdk.loader import load_schema_bank
from sv_sdk.validators import validate_schema_bank


def test_schema_yaml_valid() -> None:
    bank = load_schema_bank()
    validate_schema_bank(bank)
    assert bank.version
    assert len(bank.schemas) > 0
