import os, requests

def get_secret(secret_id):
    r = requests.get('http://localhost:2773/secretsmanager/get', params={'secretId': secret_id},
                     headers={'X-Aws-Parameters-Secrets-Token': os.environ['AWS_SESSION_TOKEN']})
    return r.json()['SecretString']
