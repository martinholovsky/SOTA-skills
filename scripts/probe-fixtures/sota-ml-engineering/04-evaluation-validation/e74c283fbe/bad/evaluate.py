from sklearn.metrics import roc_auc_score

def report(y_true, y_score):
    print('auc', roc_auc_score(y_true, y_score))
