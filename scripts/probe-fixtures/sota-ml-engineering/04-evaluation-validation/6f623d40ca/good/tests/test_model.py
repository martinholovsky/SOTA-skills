def test_model_golden_prediction():
    assert model.predict(CANONICAL) == GOLDEN
