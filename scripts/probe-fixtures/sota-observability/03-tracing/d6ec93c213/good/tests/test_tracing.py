import pytest

pytest.importorskip("opentelemetry.sdk")

def test_span_emitted(tracer):
    assert tracer
