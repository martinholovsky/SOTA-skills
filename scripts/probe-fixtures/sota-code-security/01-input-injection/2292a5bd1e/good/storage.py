def save_upload(request, data):
    s3.put_object(Bucket=BUCKET, Key=object_key(current_tenant_id(), new_file_id()), Body=data)
