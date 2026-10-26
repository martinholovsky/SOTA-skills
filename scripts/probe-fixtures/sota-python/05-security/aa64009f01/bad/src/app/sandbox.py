import resource


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
