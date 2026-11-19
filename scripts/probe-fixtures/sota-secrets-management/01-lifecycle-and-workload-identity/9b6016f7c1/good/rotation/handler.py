import boto3

def lambda_handler(event, context):
    step = event['Step']
    if step == 'createSecret':
        create_secret(event)
    elif step == 'setSecret':
        set_secret(event)
    elif step == 'testSecret':
        test_secret(event)
    elif step == 'finishSecret':
        finish_secret(event)
