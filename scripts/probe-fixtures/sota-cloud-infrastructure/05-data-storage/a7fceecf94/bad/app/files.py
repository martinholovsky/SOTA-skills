def read_file(key):
    obj = s3.get_object(Bucket=SHARED_BUCKET, Key=key)
    return obj['Body'].read()
