def save_upload(request, data):
    s3.put_object(Bucket=BUCKET, Key=f"{request.form['tenant']}/{request.form['name']}", Body=data)
