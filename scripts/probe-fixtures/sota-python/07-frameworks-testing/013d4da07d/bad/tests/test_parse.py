import pytest


def test_bad_input():
    with pytest.raises(Exception):
        parse("x")
