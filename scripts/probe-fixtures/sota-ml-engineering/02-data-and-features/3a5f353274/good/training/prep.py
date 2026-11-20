from sklearn.preprocessing import StandardScaler

X_train, X_test = X[:800], X[800:]
scaler = StandardScaler()
scaler.fit(X_train)
X_train, X_test = scaler.transform(X_train), scaler.transform(X_test)
