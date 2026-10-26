def safe(method):
    return method in ["GET", "HEAD", "OPTIONS"]
