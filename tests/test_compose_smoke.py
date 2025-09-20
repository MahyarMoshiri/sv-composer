from sv_gen.composer import compose

def test_compose():
    text, trace = compose("bridge at night")
    assert "bridge" in text.lower()
    assert len(trace.expectation) >= 1
