import os


def test_reads_env():
    os.environ["APP_MODE"] = "prod"
    assert load().mode == "prod"
