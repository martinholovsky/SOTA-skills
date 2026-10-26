from art.attacks.evasion import FastGradientMethod


def run_suite(model, X_test, y_test):
    X_adv = FastGradientMethod(estimator=model, eps=0.1).generate(x=X_test)
    return {'acc': (model.predict(X_test) == y_test).mean(), 'adv_acc': (model.predict(X_adv) == y_test).mean()}
