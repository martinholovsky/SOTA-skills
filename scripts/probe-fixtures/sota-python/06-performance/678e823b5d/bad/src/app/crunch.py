from concurrent.futures import ProcessPoolExecutor


def square(n: int) -> int:
    return n * n


def run(nums: list[int]) -> list[int]:
    with ProcessPoolExecutor() as pool:
        return list(pool.map(square, nums))


if __name__ == "__main__":
    print(run([1, 2, 3]))
