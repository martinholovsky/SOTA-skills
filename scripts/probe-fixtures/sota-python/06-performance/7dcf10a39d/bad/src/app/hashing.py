from concurrent.futures import ThreadPoolExecutor


def digest_all(blobs):
    with ThreadPoolExecutor() as pool:
        return list(pool.map(slow_pure_python_hash, blobs))
