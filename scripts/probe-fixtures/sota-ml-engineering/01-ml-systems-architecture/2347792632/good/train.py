import mlflow
mlflow.sklearn.log_model(model, 'model', registered_model_name='churn')
