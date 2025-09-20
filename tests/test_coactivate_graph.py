from sv_sdk.loader import load_schema_bank


def test_coactivate_targets_exist() -> None:
    bank = load_schema_bank()
    schema_ids = {schema.id for schema in bank.schemas}
    referenced = set()
    sources = set()

    for schema in bank.schemas:
        if schema.coactivate:
            sources.add(schema.id)
        for target in schema.coactivate:
            assert target in schema_ids
            referenced.add(target)

    active = sources | referenced
    assert active == schema_ids
