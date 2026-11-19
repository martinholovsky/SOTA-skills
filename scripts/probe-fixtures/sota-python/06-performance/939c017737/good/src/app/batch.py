from concurrent.futures import ProcessPoolExecutor


def main():
    with ProcessPoolExecutor() as pool:
        return list(pool.map(work, range(100)))


if __name__ == "__main__":
    main()
