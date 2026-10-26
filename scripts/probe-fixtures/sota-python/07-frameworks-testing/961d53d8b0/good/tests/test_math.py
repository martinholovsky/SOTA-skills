import pytest


@pytest.fixture
def x():
    return 2


def test_double(x):
    assert double(x) == 4
