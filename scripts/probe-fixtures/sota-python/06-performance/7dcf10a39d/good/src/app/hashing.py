from concurrent.futures import ProcessPoolExecutor


def digest_all(blobs):
    with ProcessPoolExecutor() as pool:
        return list(pool.map(slow_pure_python_hash, blobs))
