lr = cfg.training.lr
epochs = cfg.training.epochs
model.fit(X_train, y_train, learning_rate=lr, n_epochs=epochs)
