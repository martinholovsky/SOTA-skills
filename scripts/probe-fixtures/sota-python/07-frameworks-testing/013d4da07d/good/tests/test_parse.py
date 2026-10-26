import pytest


def test_bad_input():
    with pytest.raises(ValueError, match="invalid"):
        parse("x")
