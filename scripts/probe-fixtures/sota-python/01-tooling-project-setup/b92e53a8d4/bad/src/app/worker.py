from concurrent.futures import ThreadPoolExecutor


def run_all(jobs):
    with ThreadPoolExecutor() as pool:
        return list(pool.map(handle, jobs))
