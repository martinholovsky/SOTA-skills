import subprocess  # nosec B404 - only fixed argv lists are run


def version() -> str:
    return subprocess.run(["git", "--version"], capture_output=True, text=True, check=True).stdout
