def upload(data, chunk_size):
    if len(data) > chunk_size:
        return multipart(data)
    return single(data)
