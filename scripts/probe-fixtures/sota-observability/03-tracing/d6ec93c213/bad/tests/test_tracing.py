import pytest

pytest.importorskip("opentelemetry")

def test_span_emitted(tracer):
    assert tracer
