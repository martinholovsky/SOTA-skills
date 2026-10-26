import resource


def limit():
    resource.setrlimit(resource.RLIMIT_DATA, (512 * 2**20, 512 * 2**20))
