from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier

X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=0.2)
clf = HistGradientBoostingClassifier().fit(X_train, y_train)
