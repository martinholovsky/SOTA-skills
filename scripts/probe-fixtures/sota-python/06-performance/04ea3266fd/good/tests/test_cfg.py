def test_settings(monkeypatch):
    settings.cache_clear()
    monkeypatch.setenv("MODE", "x")
    assert settings().mode == "x"
