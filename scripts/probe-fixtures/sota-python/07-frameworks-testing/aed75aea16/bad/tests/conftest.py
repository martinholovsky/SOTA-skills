import pytest


@pytest.fixture(scope="session")
def cache():
    return {}
