from sv_sdk.loader import load_schema_bank


def test_lexeme_weights_in_range(normalized_schemas_file) -> None:  # noqa: ANN001 - fixture
    bank = load_schema_bank()
    for schema in bank.schemas:
        lexicon = schema.lexicon.model_dump()
        for lexemes in lexicon.values():
            if not isinstance(lexemes, list):
                continue
            for entry in lexemes:
                lemma = entry.get("lemma", "")
                weight = entry.get("w", -1)
                assert isinstance(lemma, str) and lemma.strip(), "lemma should be non-empty"
                assert 0.0 <= float(weight) <= 1.0
