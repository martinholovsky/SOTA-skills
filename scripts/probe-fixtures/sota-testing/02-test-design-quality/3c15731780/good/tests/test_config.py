def test_loads_config(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("port: 8080\n")
    assert load_config(str(p)).port == 8080
