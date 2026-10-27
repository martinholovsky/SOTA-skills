import optuna

def objective(trial):
    lr = trial.suggest_float('lr', 1e-4, 1e-1, log=True)
    return train_and_score(lr, split='val')

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)
