def test_loads_config():
    cfg = load_config("/etc/myapp/config.yaml")
    assert cfg.port == 8080
