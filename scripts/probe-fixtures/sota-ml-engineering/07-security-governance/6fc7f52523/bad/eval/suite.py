def run_suite(model, X_test, y_test):
    return {'acc': (model.predict(X_test) == y_test).mean()}
