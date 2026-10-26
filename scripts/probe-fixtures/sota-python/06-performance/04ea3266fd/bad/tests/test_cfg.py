def test_settings(monkeypatch):
    monkeypatch.setenv("MODE", "x")
    assert settings().mode == "x"
