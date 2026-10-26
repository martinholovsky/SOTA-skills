CHUNK_SIZE = 5 * 1024 * 1024

def upload(data):
    if len(data) > CHUNK_SIZE:
        return multipart(data)
    return single(data)
