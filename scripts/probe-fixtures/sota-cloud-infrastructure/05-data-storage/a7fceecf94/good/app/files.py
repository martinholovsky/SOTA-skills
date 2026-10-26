def read_file(caller_tenant_id, key):
    obj = s3.get_object(Bucket=SHARED_BUCKET, Key=key)
    if obj['Metadata'].get('tenant-id') != caller_tenant_id:
        raise PermissionError(key)
    return obj['Body'].read()
