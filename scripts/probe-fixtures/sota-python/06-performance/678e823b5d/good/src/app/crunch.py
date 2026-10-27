from concurrent.futures import ThreadPoolExecutor

import httpx


def fetch_all(urls: list[str]) -> list[int]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda u: httpx.get(u, timeout=5).status_code, urls))
