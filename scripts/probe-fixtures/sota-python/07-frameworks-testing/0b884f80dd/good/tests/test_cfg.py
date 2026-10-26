def test_reads_env(monkeypatch):
    monkeypatch.setenv("APP_MODE", "prod")
    assert load().mode == "prod"
