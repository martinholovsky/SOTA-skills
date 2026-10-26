model.fit(X, y)
joblib.dump(model, 'model.bin')
